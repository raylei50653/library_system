# Library System 前端

這個前端專案以 Vue 3、TypeScript、Vite 為基礎，搭配 Element Plus UI 套件打造圖書館管理系統的操作介面。主要支援會員登入、館藏查詢與借閱、收藏清單、通知中心，以及客服票單與 AI 回覆等功能。

## 技術棧
- Vue 3 + `<script setup>` + TypeScript
- Vite 開發/建置流程，`@` 路徑別名指向 `src`
- Element Plus 元件庫與 `@element-plus/icons-vue`
- Pinia 狀態管理（`src/stores`）
- Axios HTTP 客戶端與 Token 自動刷新 (`src/lib/http.ts`)

## 快速開始
1. **安裝依賴**
   ```bash
   npm install
   ```
2. **環境變數**  
   建議在 `frontend/.env.local` 內設定連線位址：
   ```bash
   VITE_API_BASE=http://127.0.0.1:8000
   VITE_SSE_BASE=http://127.0.0.1:8000   # 選填，預設同 API_BASE
   VITE_ENABLE_SIGNUP=true              # 控制是否顯示註冊流程
   ```
3. **啟動開發伺服器**
   ```bash
   npm run dev
   ```
4. **正式建置與預覽**
   ```bash
   npm run build
   npm run preview
   ```
5. **容器模式**  
   `Dockerfile` 與 `entrypoint.sh` 用來在容器中安裝依賴並以 `npm run dev -- --host 0.0.0.0` 啟動專案，可透過 docker-compose 與後端一起運行。

## 目錄結構
```text
frontend/
├── Dockerfile            # 容器化設定
├── entrypoint.sh         # 容器啟動腳本
├── index.html            # Vite 單頁入口
├── public/               # 靜態資產 (build 時原樣輸出)
└── src/
    ├── main.ts           # Vue 入口：掛載 Pinia、Element Plus、Router
    ├── App.vue           # 頂層版面：Header + 側欄 + RouterView
    ├── app/
    │   ├── router.ts     # 路由表與頁面分組
    │   └── guards/       # 全域導航守衛（登入驗證）
    ├── assets/           # 全域樣式與圖片
    ├── components/       # 共用元件
    ├── composables/      # 可重用邏輯（如 SSE 串流）
    ├── config/           # 環境設定讀取
    ├── features/         # 以領域切分的頁面與 API 模組
    ├── lib/              # 泛用工具（HTTP、Storage）
    ├── stores/           # Pinia 狀態
    ├── types/            # 共用型別定義
    └── style.css         # 全域樣式覆寫
```

### features/ 子系統
- `auth`：登入/註冊頁 (`pages/`)、對應 API、Pinia `useAuthStore` 配合本地 Token。
- `books`：館藏列表、查詢條件、借閱/預約流程，與 `favorites`、`loans` 功能協同。
- `favorites`：收藏清單 API，提供 `loadFavoritesOnce` 以快取收藏狀態。
- `loans`：借閱紀錄頁面與續借/歸還動作，集中與 `/api/loans` 互動。
- `notifications`：通知中心頁面與 API，配合 `useNotificationsStore` 輪詢未讀數。
- `chat`：客服中心票單列表與明細，串接 AI 回覆（同步 API 與 `useAIStream` SSE）。
- `home`、`profile`：首頁展示區塊與個人資料頁。

## 核心邏輯與流程
- **應用初始化**：`src/main.ts` 建立 Vue App，掛載 Pinia、Element Plus 與 `router`。`App.vue` 組合全域框架，並監聽登入狀態決定頭像列與側欄行為。
- **路由與守衛**：`src/app/router.ts` 定義訪客區（登入/註冊）與會員區（館藏、借閱、通知、客服）。`guards/auth-guard.ts` 會在進入受保護路由前檢查 Pinia 狀態與 LocalStorage Token，必要時自動 `fetchMe()`，未登入則導向 `/login`。
- **狀態管理**：
  - `useAuthStore` 保存登入者資料與 Token，封裝登入、登出、`/auth/me/` 同步流程。
  - `useNotificationsStore` 輪詢未讀通知數量，提供 `ensurePolling()`、`dec()` 等方法讓頁面同步徽章計數。
- **HTTP 客戶端**：`src/lib/http.ts` 建立 Axios 實例，於 request interceptor 自動帶入 Bearer Token，response interceptor 則處理 401 時的 Refresh Token 流程並重送原請求。
- **環境設定**：`src/config/env.ts` 將 `import.meta.env` 正規化提供 `API_BASE`、`SSE_BASE`、`ENABLE_SIGNUP` 等旗標，便於在 API 及 UI 中使用。
- **資料載入與互動**：
  - 館藏清單支援分頁、搜尋、分類/排序，並利用 `AbortController` 與 debounce 避免過量請求。
  - 借閱流程會先嘗試 `/api/loans/`，若回傳 409 則改走預約 `/api/reservations/` 並提示使用者。
  - 收藏 API 透過前端集合快取維持書籍卡片的收藏狀態，減少重複呼叫。
  - 通知頁面支援「全部已讀」後同步更新未讀徽章與列表。
- **客服與 AI**：
  - `chat/api.ts` 封裝票單與訊息 CRUD，提供 `aiReply()` 進行一次性 AI 回覆。
  - `useAIStream.ts` 實作 SSE 串流解析器，支援逐字串回呼 (`onDelta`) 與自動處理心跳、緩衝、終止事件，可在票單頁整合成即時 AI 回覆。
- **型別與共用工具**：`src/types` 描述後端主要資源型別；`src/lib/storage.ts` 封裝 `localStorage` 操作並具備錯誤防護。

## 進一步開發建議
- 新增頁面時可在 `src/features/<domain>/pages` 建立檔案並於 `router.ts` 掛載，維持領域導向的結構。
- 若後端 API 需要新增欄位，先更新 `src/types` 對應型別，再調整各 `features/*/api.ts` 與頁面。
- 需要長連線時，優先考慮重用 `useAIStream` 中的 SSE 解析與控制流程。
