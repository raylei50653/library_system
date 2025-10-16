# Library System Backend

模組化的圖書館管理系統後端，建立在 Django REST Framework 上，提供帳號登入、書籍與借閱流程、收藏與通知，以及含 AI 助理的客服票單服務。此文件著重介紹專案結構與核心邏輯，如需完整端點列表可對照 `modules.md`。

## 技術與特性
- Django 5、Django REST Framework、PostgreSQL (藉 `dj-database-url` 配置)
- Simple JWT 驗證配合 token blacklisting，支援登出與 refresh rotation
- Argon2 密碼雜湊、自訂 `users.User` 模型（以 email 為登入主體）
- 功能依網域拆為獨立 app：`auth_app`、`users`、`books`、`loans`、`favorites`、`notifications`、`chat`
- 服務層封裝業務邏輯（如借閱、續借、AI 助理），方便測試與重用
- `entrypoint.sh` 具備資料庫／Ollama 健康檢查與模型預拉取，正式環境使用 Gunicorn

## 快速啟動

### 使用 uv (建議)
```bash
cd backend
uv sync                 # 安裝依賴
cp .env.example .env    # 若已有樣板，或自行建立
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
```

### Docker Compose
專案根目錄提供 `docker-compose.yml`，後端容器啟動時會：
- 等待 PostgreSQL 與 Ollama (若設定 `OLLAMA_URL`)
- `python manage.py migrate` / `collectstatic`
- 以 `gunicorn config.wsgi:application` 監聽 8000

## 環境變數 (.env)
```env
DJANGO_SECRET_KEY=xxx
DEBUG=true
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/library_db
CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173

JWT_ACCESS_MIN=90
JWT_REFRESH_DAYS=14

LOAN_DAYS_DEFAULT=14
LOAN_MAX_RENEWALS=1
LOAN_RENEW_DAYS=14

# AI / RAG
CHAT_AI_ENABLED=true
CHAT_AI_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:8b
```

## 主要目錄結構
```
backend/
├── config/              # Django 設定、urls、WSGI/ASGI 入口
├── auth_app/            # 註冊、登入、refresh、logout
├── users/               # 自訂 User 模型與個資／後台管理 API
├── books/               # 書籍與分類 CRUD、filters、services
├── loans/               # 借閱與預約流程、服務層邏輯
├── favorites/           # 收藏清單 API
├── notifications/       # 通知模型與讀取/標記服務
├── chat/                # 客服票單、訊息、AI 助理與 SSE 串流
├── manage.py            # Django 管理指令入口
├── entrypoint.sh        # 容器啟動流程（等待 DB/Ollama、migrate、gunicorn）
└── backend_tree.txt     # 產生的結構快照（開發參考用）
```

## 模組職責摘要
- **auth_app**：基於 `rest_framework_simplejwt` 的登入／登出。`LoginView` 以 email 查詢並生成 access/refresh；`LogoutView`、`LogoutAllView` 操作黑名單表。
- **users**：自訂 `User` 模型 (無 username)。`MeProfileView` 提供個資查詢與更新；`AdminUser*` API 受 `IsAdminRole` 控制，可檢索／調整角色與啟用狀態。
- **books**：`BookViewSet` 支援 `query`、`category`、`status`、排序與分頁；`CategoryViewSet` 擴充 `book_count` 並禁止刪除仍有關聯書籍。`services.py` 處理冊數調整與庫存重算。
- **loans**：`Loan` 模型以 `type` 區分借閱與預約，並以複合 `UniqueConstraint` 限制重複借／重複預約。`services.py` 負責借閱 (`loan_book`)、預約 (`reserve_book`)、歸還 (`return_loan`) 與續借 (`renew_loan`) 等交易流程並觸發通知。
- **favorites**：維護 `Favorite` 關聯，列表固定回傳完整集合，新增／刪除皆為冪等操作。
- **notifications**：提供 `create_notification`、`mark_as_read`、`mark_all_as_read` 服務，並由借閱邏輯與排程任務呼叫。
- **chat**：`Ticket`/`Message` 模型配合 `TicketCollectionView`、`MessageCollectionView` 提供客服票單 CRUD。`AIReplyView`、`sse_ai_reply`、`AssistView` 整合 Ollama，`services.agent` 進一步加上 RAG 與工具調用。詳情參考 `modules.md` 對應段落。

## 核心流程與商業邏輯

### 驗證與帳號
- 新增帳號走 `RegisterSerializer`，註冊後僅回基本資訊，登入需另行呼叫。
- `LoginView` 直接使用 email/password 驗證，透過 Simple JWT 發放 access/refresh，前端在 refresh 時會自動旋轉 token。
- `auth/me` 端點由前端重新整理時呼叫，以恢復 `useAuthStore` 狀態。
- `LogoutView` 接收 refresh 字串並加入黑名單；`LogoutAllView` 會拉黑該使用者所有 outstanding token。

### 館藏與借閱
- `Book` 模型跟蹤 `total_copies`、`available_copies` 與 `status`。任何借閱或歸還都透過 `Book.objects.update(..., F())` 原子調整，並同步更新 `status`。
- 借閱流程 (`loan_book`) 會鎖定書籍、檢查庫存並建立 `Loan`，缺貨時轉交預約流程 (`reserve_book`)。
- 歸還流程 (`return_loan`) 釋放庫存後會撈取最早的 `pending` 預約並自動轉成真正借閱，成功轉換時發送 `reservation_available` 通知。
- 續借流程 (`renew_loan`) 會遵守 `LOAN_MAX_RENEWALS` 與 `LOAN_RENEW_DAYS` 設定，並在成功後推播 `loan_due_soon` 通知提醒新的到期日。

### 收藏與通知
- 收藏 API 始終作用在登入者身上，列表使用 `select_related` 直接帶回書籍與分類資訊。
- 通知服務由借閱模組呼叫，也可由排程任務透過 `notify_due_soon()` 建立逾期提醒。前端輪詢 `GET /api/me/notifications/?is_read=false` 時可直接利用回傳的 `count`。
- 任何標記已讀操作都回傳統一 JSON（單筆回對應通知、全部已讀回 `{updated: count}`），方便前端同步徽章數。

### 客服票單與 AI 助理
- 一般使用者預設只能查詢自己的票單；管理員可透過 `?mine=true|false` 取得篩選後的結果並以 `PATCH /chat/admin/tickets/{id}/` 指派或關閉票單。
- 每則訊息在建立時寫入 `Message`，AI 回覆會在 `response_meta` 儲存模型資訊、延遲或工具狀態。
- `chat/services/agent.py` 使用 `build_messages` 組合歷史對話與票單 `config`，再以 `chat_once` 或 `chat_stream` 與 Ollama 互動。啟用工具時會解析 `[TOOL]{...}` 指令，執行對應函式後將輸出再次餵回模型。
- `sse_ai_reply` 回傳 `StreamingHttpResponse`，串流期間會先寫入啟動訊息、逐段推送 `data: ...`，最後以 `data: [DONE]` 結束；若模型失敗則推送錯誤內容並收尾。

### 管理與工具
- `books.management.commands.import_books` 可從 CSV 匯入書籍，開發者可用 `uv run python manage.py import_books --path books_seed.csv` 補齊資料。
- `config/settings_test.py` 覆寫部分設定，搭配 `pytest.ini` 可使用 `uv run python -m pytest` 快速執行測試。

## 資料模型摘要
```
User (AUTH_USER_MODEL)
 ├─< Loan (type=loan|reservation, status=active|pending|...)
 │     └─> Book
 ├─< Favorite ──> Book
 ├─< Notification [optional loan FK]
 └─< Ticket ──< Message (is_ai flag, response_meta JSON)
```

## 測試與開發工具
- `uv run python -m pytest`：使用 pytest + pytest-django，預設載入 `config.settings`
- `uv run python manage.py test`：亦可使用 Django 原生測試指令
- `uv run python manage.py shell_plus`：若安裝 `django-extensions`，可快速進入互動殼層
- `backend/error.log`：預設 log 輸出位置，方便本地或容器排錯

## 部署重點
- 靜態檔案由 Whitenoise 服務，建議在啟動腳本中保留 `collectstatic`
- 解除 `DEBUG` 後，`settings.py` 會自動套用 SSL、HSTS 等安全設定
- 若啟用 AI 助理，確保環境變數 `OLLAMA_URL`、`OLLAMA_MODEL` 正確，並於防火牆允許後端容器與 Ollama 通訊
- 若需排程通知，可透過 `cron` 或 Celery 呼叫 `loans.services.notify_due_soon`
