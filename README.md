# Library System

一個端到端的圖書館管理平台，整合 Django REST API、Vue 3 SPA、PostgreSQL 以及 Ollama／AI 聊天助理。專案以模組化方式切分功能，支援使用者自助借閱、管理員審核、通知提醒與客服對話。

## 系統架構

- **後端**：`backend/` 為 Django 5 專案，使用 Django REST Framework、SimpleJWT，依功能拆分成 `auth_app`、`users`、`books`、`loans`、`favorites`、`notifications`、`chat` 等應用，並以服務層（`services.py`）封裝商業邏輯。
- **前端**：`frontend/` 為 Vue 3 + TypeScript + Vite 專案，採 domain-oriented 結構（`features/*`），使用 Pinia 管理登入狀態與 Element Plus UI 元件。
- **資料庫**：PostgreSQL 16，透過 `dj-database-url` 與環境變數連線。
- **AI / RAG**：`chat` 模組連接 Ollama 模型，提供同步回覆與 SSE 串流。
- **協作與自動化**：`docker-compose.yml` 建立 db/backend/frontend/ollama 四個服務；`Makefile` 提供一鍵啟動、測試與維運指令。

```
[Vue 3 SPA] -- REST / SSE --> [Django API] -- ORM --> [PostgreSQL]
                                   |
                                   +--> [Ollama 推理服務]
```

## 功能總覽

### 使用者與身份
- 電子郵件註冊／登入／刷新 Token，支援多端登出。
- 角色與權限：一般讀者、管理員；共用 `/auth/me/` 取得個人資訊。
- 個人檔案編輯與管理員後台使用者管理。

### 館藏與借閱
- 書籍／分類 CRUD、搜尋、分頁、排序與庫存狀態顯示。
- 借閱流程包含借書、續借、歸還，並自動判斷庫存不足時改為預約。
- 收藏清單、個人借閱與預約紀錄查詢。
- 事件通知：借閱到期提醒、系統訊息等（支援批次設為已讀）。

### 客服與 AI 聊天
- 客服工單與訊息串管理，支援管理員指派處理。
- 以 JWT 鑑權的 SSE 串流，在 `ChatCenterView` 中串接 Ollama 模型，提供即時 AI 回覆。

### 前端體驗
- 使用 `features/*/api.ts` 匯整各模組 API，`lib/http.ts` 統一攔截器與錯誤處理。
- `useAIStream` 可重複使用於任意 SSE 場景，並具中止控制與錯誤回傳。
- 路由守衛 `app/guards/auth-guard.ts` 確保私人頁面需登入。

## 專案目錄重點

```
. (monorepo)
├── backend/           # Django REST 後端
│   ├── config/        # settings、URL、WSGI/ASGI
│   ├── auth_app/      # JWT 登入與 refresh token 黑名單
│   ├── books/         # 書籍與分類管理
│   ├── loans/         # 借閱、預約、續借、還書服務
│   ├── favorites/     # 收藏清單
│   ├── notifications/ # 使用者通知
│   ├── chat/          # 客服工單、AI 串流回覆
│   └── users/         # 個人資料與管理員 API
├── frontend/          # Vue 3 + Vite 前端
│   ├── app/router.ts  # 路由與守衛
│   ├── features/*     # Domain 功能模組 (auth/books/chat/...)
│   ├── stores/auth.ts # Pinia 登入狀態
│   └── composables/   # 共用 hook，如 AI SSE 串流
├── docker-compose.yml # PostgreSQL、Ollama、後端、前端整合
└── Makefile           # 日常開發與維運指令
```

## 快速開始

1. **取得專案原始碼**
   ```bash
   git clone https://github.com/raylei50653/library_system.git
   cd library_system
   ```
2. **安裝前置**：
   - Docker 24+ 與 Docker Compose v2（若要使用 `docker compose build` 建議一併安裝 Buildx）。
   - （如需 GPU／Ollama 推理）NVIDIA 驅動、NVIDIA Container Toolkit，完成 `sudo nvidia-ctk runtime configure --runtime=docker --set-as-default` 後重新啟動 Docker。
   - Node 18+、Python 3.12（僅在跳過 Docker、於本機執行時需要）。
   - 若於本機環境執行（非 Docker），建議先透過套件管理器安裝基礎相依：
     - **Debian / Ubuntu (apt)**：
       ```bash
       sudo apt update
       sudo apt install -y build-essential python3 python3-venv python3-dev libpq-dev \
         libffi-dev libssl-dev pkg-config nodejs npm git
       ```
     - **Arch / Manjaro (pacman)**：
       ```bash
       sudo pacman -Syu
       sudo pacman -S --needed base-devel python python-pip python-virtualenv libpq \
         libffi openssl nodejs npm git
       ```
3. **建立環境**：根據 `backend/.env`、`frontend/.env` 覆寫需要的設定（預設已可本機使用）。
4. **啟動所有服務**
   ```bash
   make up          # 或 docker compose up -d
   make logs-backend
   ```
   - 後端管理站台：`http://127.0.0.1:8000/admin/`
   - 前端開發伺服器：`http://127.0.0.1:5173`
5. **建立管理員帳號**
   ```bash
   make superuser
   ```
   完成指令後，以該帳號登入 `http://127.0.0.1:8000/admin/`，在 `Users` 選單中點選 `Add user`，輸入新成員的 `Username` 與 `Password`，再勾選需要的 `Staff status` 或 `Superuser status` 後儲存。
6. **建立測試資料**：透過 API 或 Django Admin 匯入 `backend/books_seed.csv` 等資料。

### 本機開發（不透過 Docker）

```bash
# 後端
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver

# 前端
cd frontend
npm install
npm run dev
```

## 測試與維運

- 後端測試：`make test` 或 `uv run python -m pytest`
- 前端建置：`npm run build` 或使用 `make fe-build`
- 健康檢查：`make health` 會確認 `/admin/` 是否存活
- 常見維運：`make ollama-pull MODEL=<name>` 拉取模型、`make psql` 進入資料庫

## 更多資訊

- 詳細後端 API 與模型說明：`backend/README.md`
- Makefile 指令與自動化流程：`project.md`
- 若需客製 AI 模型或串接其他提供者，可調整 `backend/.env` 中 `CHAT_AI_PROVIDER` 與 `CHAT_AI_MODEL`

歡迎依照需求擴充 reports、recommendations 等預留模組，一同打造完整的智慧圖書館體驗。
