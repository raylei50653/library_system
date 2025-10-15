# 📚 模組總覽與接口設計（同步後端現況）

`config/urls.py` 掛載策略：**REST 資源歸在 `/api/`**；**認證 `/auth/`**；**使用者 `/users/`**；**聊天 `/chat/`**。  
本專案預設 **尾斜線啟用**（請使用 `/path/` 形式）。

---

## 1) Auth（使用者登入註冊與驗證）

- `POST /auth/register/`：註冊（email、password、display_name）
- `POST /auth/login/`：登入（回傳 access/refresh）
- `POST /auth/refresh/`：刷新 access token
- `GET /auth/me/`：讀取當前登入者基本資料
- `POST /auth/logout/`：單次登出；body 需提供欲作廢的 refresh token
- `POST /auth/logout-all/`：清空目前使用者所有 refresh token（需帶 access token）

> JWT 存活時間由環境變數 `JWT_ACCESS_MIN`／`JWT_REFRESH_DAYS` 控制；啟用 blacklist 以支援登出。

---

## 2) Users（使用者管理）

- `GET /users/me/profile`：查詢個人資料
- `PATCH /users/me/profile`：更新顯示名稱
- `GET /users/admin/users`：管理員查詢全部使用者，可用 `?email=`、`?role=`、`?active=true|false` 篩選
- `GET /users/admin/users/{id}`：管理員檢視特定使用者
- `PATCH /users/admin/users/{id}/update`：管理員更新角色或啟用狀態

關聯：所有外鍵以 `ForeignKey(settings.AUTH_USER_MODEL)` 指向 `User`；`USERNAME_FIELD="email"`；密碼採 **Argon2**。

---

## 3) Books（書籍管理）— `/api/`

- `GET /api/books/`：查詢書籍列表（`?query=&category=&status=`；預設分頁 `count/results`）
- `POST /api/books/`：管理員新增書籍
- `GET /api/books/{id}/`：取得書籍詳細
- `PUT/PATCH/DELETE /api/books/{id}/`：管理員維護
- `GET /api/categories/`：列出分類（含 `book_count`）
- `POST/PUT/PATCH/DELETE /api/categories/{id}/`：管理員維護（分類仍有書籍則禁止刪除）

模型重點：`Book.available_copies` 於借還流程即時遞增／遞減；`status` 會依庫存自動更新。

---

## 4) Loans（借閱與預約）— `/api/`

- `GET /api/loans/`：列出借閱紀錄（一般使用者僅看到自己的；管理員可 `?status=` 篩選）
- `POST /api/loans/`：建立借閱（body 提供 `book_id`；無庫存回 `NotEnoughCopies`）
- `POST /api/loans/{id}/return_/`：歸還（持有人或管理員）
- `POST /api/loans/{id}/renew/`：續借（檢查 `LOAN_MAX_RENEWALS` 與續借天數）
- `GET /api/reservations/`：列出預約（`Loan.type = reservation`）
- `POST /api/reservations/`：建立預約（初始狀態 `pending`）
- `GET /api/admin/loans/`：管理員檢視所有借閱／預約
- `PATCH /api/admin/loans/{id}/`：管理員人工修改狀態或備註

流程重點：
1. 借書成功會鎖定庫存並計算 `due_at`
2. 還書釋出庫存；若有相同書籍的 `pending` 預約會轉為 `active` 借閱並寄送通知
3. 續借成功推播 `loan_due_soon` 通知並更新到期日

資料模型：單表 `Loan` 以 `type` 區分借閱／預約；以 `UniqueConstraint` 限制同人同書不可重複借。

---

## 5) Favorites（收藏）— `/api/`

- `GET /api/me/favorites/`：查詢自己的收藏（無分頁，依建立時間新到舊）
- `POST /api/me/favorites/{book_id}/`：新增收藏（已存在回 200）
- `DELETE /api/me/favorites/{book_id}/`：移除收藏（冪等；不存在回 204）

---

## 6) Notifications（通知）— `/api/`

- `GET /api/me/notifications/`：取得個人通知（`?is_read=true|false`）
- `POST /api/me/notifications/{id}/read/`：標記單筆為已讀
- `POST /api/me/notifications/read-all/`：一次標記所有未讀

關聯：通知由 `notifications.services.create_notification` 產生；`Notification.loan` 為可選外鍵。

---

## 7) Chat（客服票單與 AI 助理）— `/chat/`

### 功能端點
- `GET /chat/tickets/`：列出票單（一般使用者預設僅看自己的；管理員可用 `?mine=true` 或 `?status=` 篩選）
- `POST /chat/tickets/`：建立票單（欄位：`subject`、可選 `content`、`config` JSON）
- `PATCH /chat/admin/tickets/{ticket_id}/`：管理員指派或變更狀態（`status`、`assignee_id`）
- `GET /chat/messages/?ticket_id=`：讀取指定票單訊息（支援分頁）
- `POST /chat/messages/`：新增訊息，body `{ticket_id, content}`
- `POST /chat/ai/reply/`：呼叫本地 Ollama，同步取得 AI 回覆並儲存人類/AI 訊息
- `GET /chat/ai/stream/?ticket_id=&content=`：透過 SSE 串流 AI 回覆（需登入）

### 權限與資料
- `Ticket`：`user`（建立者）與可選 `assignee`（管理員）；狀態 `open`/`closed`
- `Message`：連結 `Ticket` 與來源；AI 訊息標 `is_ai=True` 並記錄 `response_meta`
- `PromptTemplate`、`KnowledgeDoc`、`KnowledgeChunk`：提供 AI 助理的系統提示與 RAG 資料

> 通知整合暫未啟用；票單狀態變更尚不自動推播。

---

## 8) 系統關聯（ASCII 摘要）

```
User (1) ──< (∞) Ticket (1) ──< (∞) Message
User (1) ──< (∞) Favorite >── (1) Book
User (1) ──< (∞) Loan    >── (1) Book
Loan (1) ──< (∞) Notification
```

---

## 9) 前端導覽對應

| 項目 | 路由 | 功能說明 |
|------|------|----------|
| 首頁 | `/` | 最新公告、熱門書籍 |
| 館藏 | `/books` | 書籍列表與搜尋 |
| 借閱紀錄 | `/loans` | 查看借閱與預約 |
| 收藏 | `/favorites` | 個人收藏清單 |
| 通知 | `/notifications` | 系統推播、借閱提醒 |
| 客服中心 | `/chat` | 與管理員或 AI 助理對話 |
| 個人資料 | `/profile` | 修改名稱、密碼 |
| 登入／註冊 | `/login`、`/register` | 帳號操作 |

