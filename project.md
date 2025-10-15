# 專案管理 Makefile

適用於 **Django + Docker + Ollama + 前端環境**

這份 Makefile 提供一鍵式的開發、測試與維運指令，  
適合多人協作或自動化 CI/CD 使用。  

---

## 一、基本參數

```makefile
COMPOSE           ?= docker compose
BACKEND_SERVICE   ?= backend
DB_SERVICE        ?= db
OLLAMA_SERVICE    ?= ollama
BACKEND_PORT      ?= 8000
MODEL             ?= llama3.1:8b-instruct
APP               ?=        # 範例：make makemigrations APP=books

.DEFAULT_GOAL := help
```

---

## 二、使用說明

這份 Makefile 整合以下常用操作：

- 啟動 / 停止 / 重建 Docker 容器  
- 執行 Django 管理指令（migrate、superuser、collectstatic）  
- 執行測試（pytest、coverage）  
- 管理 PostgreSQL、Ollama 模型  
- 啟動前端開發伺服器  

---

## 三、常用指令範例

### 1. 啟動與重建專案

```bash
make up        # 啟動所有服務
make up-b      # 不使用快取重新建置
make down      # 停止並移除容器
make ps        # 查看容器狀態
make logs      # 查看所有日誌
make logs-backend  # 查看後端日誌
```

---

### 2. Django 管理與資料庫

```bash
make check                # 健檢設定
make show-urls            # 列出 URL 對照表
make makemigrations APP=books
make migrate
make superuser
make collectstatic
```

---

### 3. 測試與覆蓋率

```bash
make test     # 執行 pytest
make test-q   # 安靜模式
make cov      # 顯示覆蓋率報告
```

---

### 4. 資料庫操作

```bash
make psql         # 進入 PostgreSQL 命令列
make db-shell     # 進入 DB 容器 shell
```

---

### 5. Ollama 模型管理

```bash
make ollama-tags   # 查看目前模型
make ollama-pull MODEL=llama3.1:8b-instruct
make ollama-ps     # 查看 Ollama 進程
```

---

### 6. 健康檢查與前端

```bash
make health      # 檢查後端 /admin 狀態
make fe-dev      # 啟動前端開發伺服器
make fe-build    # 打包前端（production）
```

---

## 四、設計理念

- **模組化**：後端、資料庫、Ollama、前端均可獨立啟動。  
- **一致性**：所有命令都透過 `docker compose exec` 執行。  
- **可讀性**：每個命令都附有註解與說明。  
- **可擴充**：可新增 `lint`、`format`、`deploy` 等 CI 指令。  
