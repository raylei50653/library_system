# 📘 Library System Backend

一個模組化的圖書管理系統後端，採用 **Django REST Framework + PostgreSQL**，支援 **JWT 登入、權限控管、RAG/AI 聊天** 與 **測試環境**。

---

## 🚀 快速啟動

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```
預設服務位址：http://127.0.0.1:8000

---

## ⚙️ 環境設定 `.env`

```env
DJANGO_SECRET_KEY=******
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DATABASE_URL=postgresql://ray:ray123456@127.0.0.1:5432/library_db

CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173

JWT_ACCESS_MIN=90
JWT_REFRESH_DAYS=14

# Chat / AI Assistant
CHAT_AI_ENABLED=true
CHAT_AI_PROVIDER=ollama
CHAT_AI_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

---

## 📦 路由總覽（Base Prefix）

> 原則：REST 資源統一放在 `/api/` 前綴；認證在 `/auth/`；使用者在 `/users/`；聊天在 `/chat/`。  
> 本專案預設 **啟用尾斜線**（e.g. `/path/`），請前端保持一致。

| 模組             | Base Prefix | 說明                              |
|------------------|-------------|-----------------------------------|
| Auth             | `/auth/`    | 登入、註冊、刷新、登出、`/auth/me/` |
| Users            | `/users/`   | 個人資料與管理員使用者管理        |
| API（資源）      | `/api/`     | Books / Categories / Loans / Reservations / Favorites / Notifications |
| Chat             | `/chat/`    | 客服票單、訊息、AI 回覆            |

---

## 🔗 URL 掛載（節錄）

```python
# config/urls.py
urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("auth_app.urls")),
    path("users/", include("users.urls")),
    path("api/", include("books.urls")),
    path("api/", include("loans.urls")),
    path("api/", include("favorites.urls")),
    path("api/", include("notifications.urls")),
    path("chat/", include("chat.urls")),
]
```
> 小提醒：同一個 `"/api/"` 前綴下包含多個 router 時，`/api/` 會出現多次 APIRootView，是正常現象；若想整潔，可集中在一個頂層 `DefaultRouter`。

---

## 🧭 主要 API 索引（依實作為準）

### Auth
- `POST /auth/register/` 註冊
- `POST /auth/login/` 登入（回傳 access/refresh）
- `POST /auth/refresh/` 刷新 Access Token
- `GET /auth/me/` 取得個人基本資料
- `POST /auth/logout/` 單一 Refresh 登出
- `POST /auth/logout-all/` 全部 Refresh 登出

### Users
- `GET /users/me/profile` 讀取個人資料
- `PATCH /users/me/profile` 更新顯示名稱
- `GET /users/admin/users`（可 `?email=`、`?role=`、`?active=`）
- `GET /users/admin/users/{id}`
- `PATCH /users/admin/users/{id}/update`

### Books / Categories（位於 `/api/`）
- `GET /api/books/`（`?query=&category=&status=`，預設分頁）
- `POST /api/books/`（管理員）
- `GET /api/books/{id}/`，`PUT/PATCH/DELETE /api/books/{id}/`（管理員）
- `GET /api/categories/`（含 `book_count`）
- `POST/PUT/PATCH/DELETE /api/categories/{id}/`（管理員；若仍有書籍則禁止刪除）

### Loans / Reservations（位於 `/api/`）
- `GET /api/loans/`（一般用戶只看自己的；管理員可篩選 `?status=`）
- `POST /api/loans/`（建立借閱）
- `POST /api/loans/{id}/return_/`（歸還）
- `POST /api/loans/{id}/renew/`（續借）
- `GET /api/reservations/`，`POST /api/reservations/`

### Favorites（位於 `/api/`）
- `GET /api/me/favorites/`
- `POST /api/me/favorites/{book_id}/`
- `DELETE /api/me/favorites/{book_id}/`

### Notifications（位於 `/api/`）
- `GET /api/me/notifications/`（`?is_read=true|false`）
- `POST /api/me/notifications/{id}/read/`
- `POST /api/me/notifications/read-all/`

### Chat（位於 `/chat/`）
- `GET /chat/tickets/`，`POST /chat/tickets/`
- `PATCH /chat/admin/tickets/{ticket_id}/`
- `GET /chat/messages/?ticket_id=`，`POST /chat/messages/`
- `POST /chat/ai/reply/`（同步回覆）
- `GET /chat/ai/stream/?ticket_id=&content=`（SSE 串流回覆）

---

## 🗃️ 資料模型關聯（ASCII 版）

```
User (1) ──< (∞) Ticket (1) ──< (∞) Message
   │
   ├──< (∞) Favorite >── (1) Book
   │                     │
   └──< (∞) Loan    >────┘
             │
             └──< (∞) Notification

Message：若為 AI 回覆，標記 is_ai=True 並保存 response_meta
Ticket：可選 assignee（管理員），狀態 open/closed
```

---

## 🧪 測試與除錯

- 測試：`uv run python -m pytest`（或 `manage.py test`）  
- 錯誤日誌：`backend/error.log`  
- 清除測試資料庫：`uv run python manage.py test --keepdb`

---

## 🧭 延伸模組（預留）

- `reports/`：統計報表（借閱量、熱門書籍、客服回覆率）  
- `recommendations/`：AI 推薦書籍  
- `analytics/`：後台使用行為追蹤  
