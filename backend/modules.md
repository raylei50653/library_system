# 📚 模組總覽與接口設計（同步後端現況）

`config/urls.py` 掛載策略：**REST 資源歸在 `/api/`**；**認證 `/auth/`**；**使用者 `/users/`**；**聊天 `/chat/`**。  
部分路由因為沿用 Django `APPEND_SLASH=True` 可接受無尾斜線，文件仍以實際定義為準。

---

## 1) Auth（使用者登入註冊與驗證）

- `POST /auth/register/`：註冊（`email`、`password`、可選 `display_name`）。成功回傳建立的使用者基本欄位，**不會**自動登入。
- `POST /auth/login/`：登入並回傳 `access_token` / `refresh_token` / `token_type=bearer`。未啟用帳號回 `403`。
- `POST /auth/refresh/`：沿用 Simple JWT `TokenRefreshView`，輸入 `refresh` 取得新的 access。
- `GET /auth/me/`：登入狀態回傳 `MeSerializer`（`id`、`email`、`display_name`、`role` 等）。
- `POST /auth/logout/`：單次登出；body 需帶 `{ "refresh": "<token>" }`，會黑名單化該 refresh。
- `POST /auth/logout-all/`：清空目前使用者所有 outstanding refresh token，需要帶 `Authorization: Bearer <access>`。

邏輯補充：
- JWT 存活時間由 `JWT_ACCESS_MIN`／`JWT_REFRESH_DAYS` 決定，啟用 `token_blacklist` 才能使用 logout。
- `LoginView` 直接以 email 查詢並 `check_password`，登入成功後立即回傳新的 refresh 與 access（已開啟 `ROTATE_REFRESH_TOKENS`）。

---

## 2) Users（使用者管理）

- `GET /users/me/profile`：查詢個人資料，資料結構同 `UserDetailSerializer`。
- `PATCH /users/me/profile`：更新 `display_name` 等欄位（Partial 更新）。
- `GET /users/admin/users`：管理員查詢全部使用者，可用 `?email=`、`?role=`、`?active=true|false`，預設依 `id` 遞增。
- `GET /users/admin/users/{id}`：管理員檢視特定使用者。
- `PATCH /users/admin/users/{id}/update`：管理員更新 `role`／`is_active`。僅開放 `PATCH`，不允許 PUT。

關聯：所有外鍵以 `ForeignKey(settings.AUTH_USER_MODEL)` 指向 `User`；`USERNAME_FIELD="email"`；密碼採 **Argon2**。

---

## 3) Books（書籍管理）— `/api/`

- `GET /api/books/`：查詢書籍列表。支援：
  - `?query=`（模糊比對 title/author/category，透過 `BookFilter`）
  - `?category=`、`?status=`
  - 標準 `?ordering=`、`?page=`、`?page_size=`（預設 10、上限 100）
- `POST /api/books/`：管理員新增書籍。成功後回傳 `BookSerializer`。
- `GET /api/books/{id}/`、`PUT/PATCH/DELETE /api/books/{id}/`：讀取與維護單筆書籍（管理員才可寫入）。
- `GET /api/categories/`：列出分類並附帶 `book_count`（使用 `annotate`）。
- `POST/PUT/PATCH/DELETE /api/categories/{id}/`：管理員維護。若分類仍有書籍，`DELETE` 回 `409`。

模型重點：`Book.total_copies` 與 `available_copies` 會在借還流程內以 `select_for_update` 鎖定更新；`status` 為 0 時自動設為 `unavailable`。

---

## 4) Loans（借閱與預約）— `/api/`

- `GET /api/loans/`：列出借閱紀錄。非管理員僅看到自己的；管理員可看到全部並可用 `?status=`。
- `POST /api/loans/`：建立借閱，body `{ "book_id": number }`。無庫存會觸發 `NotEnoughCopies`（HTTP 400）。
- `POST /api/loans/{id}/return_/`：自訂 action，持有人或管理員可歸還，回傳更新後的 `status`、`returned_at` 等欄位。
- `POST /api/loans/{id}/renew/`：續借，檢查 `LOAN_MAX_RENEWALS` 與 `LOAN_RENEW_DAYS`，超過上限會回 400。
- `GET /api/reservations/`：列出預約（`Loan.type=reservation`），同樣依權限篩選，可用 `?status=`。
- `POST /api/reservations/`：建立預約，body `{ "book_id": number }`。
- `GET /api/admin/loans/`：管理員檢視所有借閱與預約（含 user/book 關聯）。
- `PATCH /api/admin/loans/{id}/`：管理員人工修正 `status` 或 `note`（使用 `AdminLoanPatchSerializer`）。

流程重點：
1. 借書成功會鎖定庫存並計算 `due_at`
2. 還書釋出庫存；若有相同書籍的 `pending` 預約會轉為 `active` 借閱並寄送通知
3. 續借成功推播 `loan_due_soon` 通知並更新到期日

資料模型：單表 `Loan` 以 `type` 區分借閱／預約；`UniqueConstraint` 保證同一位使用者在借閱 (`active`/`pending`) 與預約 (`pending`) 不會重覆建立。

---

## 5) Favorites（收藏）— `/api/`

- `GET /api/me/favorites/`：查詢自己的收藏（關閉分頁，依建立時間新到舊），每項包含完整 `BookSerializer`。
- `POST /api/me/favorites/{book_id}/`：新增收藏，已有紀錄仍回 200 並附帶快照。
- `DELETE /api/me/favorites/{book_id}/`：移除收藏，冪等操作，不存在也回 204。

---

## 6) Notifications（通知）— `/api/`

- `GET /api/me/notifications/`：取得個人通知，可用 `?is_read=true|false` 篩選；預設不分頁（全部載回）。
- `POST /api/me/notifications/{id}/read/`：標記單筆為已讀，找不到回 404。
- `POST /api/me/notifications/read-all/`：一次標記所有未讀，回 `{ "updated": <count> }`。

關聯：通知由 `notifications.services.create_notification` 產生；`Notification.loan` 為可選外鍵。

---

## 7) Chat（客服票單與 AI 助理）— `/chat/`

### 功能端點
- `GET /chat/tickets/`：列出票單。非管理員僅能看到自己的；管理員可用 `?mine=true` 篩出自己，`?status=open|closed` 篩選狀態，預設依 `updated_at` 由新到舊。
- `POST /chat/tickets/`：建立票單，欄位：`subject`（必填）、`content`（可選初始訊息）、`config`（JSON 設定，存於 `ticket.config`）。
- `PATCH /chat/admin/tickets/{ticket_id}/`：管理員將票單關閉或指派他人（`status`、`assignee_id`）。
- `GET /chat/messages/?ticket_id=`：讀取指定票單訊息，支援 `?page=`、`?page_size=`（預設 20）。
- `POST /chat/messages/`：新增訊息，body `{ "ticket_id": number, "content": string }`，會先檢查 ticket 所屬權限與狀態。
- `POST /chat/ai/reply/`：同步呼叫 Ollama，成功後會寫入一筆人類訊息與一筆 AI 訊息（`response_meta` 包含 latency）。
- `GET /chat/ai/stream/?ticket_id=&content=`：以 `text/event-stream` 串流 AI 回覆；成功結尾會送出 `data: [DONE]`。
- `POST /chat/ai/assist`：進階助理（可附 `use_rag`、`enable_tools` 旗標），回傳 AI 訊息與 `meta`。

### 權限與資料
- `Ticket`：`user`（建立者）與可選 `assignee`（管理員）；狀態 `open`/`closed`
- `Message`：連結 `Ticket` 與來源；AI 訊息標 `is_ai=True` 並記錄 `response_meta`
- `PromptTemplate`、`KnowledgeDoc`、`KnowledgeChunk`：提供 AI 助理的系統提示與 RAG 資料

> 尚未整合通知推播；票單狀態改變不會自動寄送通知。

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
