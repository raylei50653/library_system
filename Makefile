# ======================================
# 專案管理 Makefile
# 用於 Django + Docker + Ollama + 前端環境
# ======================================

COMPOSE           ?= docker compose
BACKEND_SERVICE   ?= backend
DB_SERVICE        ?= db
OLLAMA_SERVICE    ?= ollama
BACKEND_PORT      ?= 8000
MODEL             ?= llama3.1:8b-instruct
APP               ?=
BOOKS_CSV        ?= ./books_seed.csv
BOOKS_CSV_CONTAINER ?= /tmp/books_seed.csv

.DEFAULT_GOAL := help

# ======================================
# 說明
# ======================================
help: ## 顯示可用指令
	@echo ""
	@echo "可用目標（make <target>）:"
	@awk 'BEGIN {FS":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  [36m%-20s[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

# ======================================
# Docker Compose 基礎操作
# ======================================
up: ## 啟動所有服務（自動建置）
	$(COMPOSE) up -d

up-b: ## 重新建置並啟動（不使用快取）
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

build: ## 重新建置（使用快取）
	$(COMPOSE) build

down: ## 停止並移除容器
	$(COMPOSE) down

restart: ## 重新啟動服務
	$(COMPOSE) restart

ps: ## 顯示容器狀態
	$(COMPOSE) ps

logs: ## 查看所有服務日誌
	$(COMPOSE) logs -f

logs-backend: ## 查看後端日誌
	$(COMPOSE) logs -f $(BACKEND_SERVICE)

# ======================================
# Django 常用指令
# ======================================
check: ## 健檢 Django 設定
	$(COMPOSE) exec $(BACKEND_SERVICE) python manage.py check

show-urls: ## 列出所有 URL 與名稱
	$(COMPOSE) exec $(BACKEND_SERVICE) python manage.py show_urls

shell: ## 進入 backend shell
	-$(COMPOSE) exec $(BACKEND_SERVICE) bash || $(COMPOSE) exec $(BACKEND_SERVICE) sh

makemigrations: ## 產生遷移（可指定 APP）
	@if [ -n "$(APP)" ]; then \
		$(COMPOSE) exec $(BACKEND_SERVICE) python manage.py makemigrations $(APP); \
	else \
		$(COMPOSE) exec $(BACKEND_SERVICE) python manage.py makemigrations; \
	fi

migrate: ## 套用所有遷移
	$(COMPOSE) exec $(BACKEND_SERVICE) python manage.py migrate

superuser: ## 建立管理員帳號
	$(COMPOSE) exec $(BACKEND_SERVICE) python manage.py createsuperuser

collectstatic: ## 收集靜態檔案
	$(COMPOSE) exec $(BACKEND_SERVICE) python manage.py collectstatic --noinput

import-books: ## 匯入書籍 CSV（可覆寫 BOOKS_CSV）
	$(COMPOSE) up -d $(BACKEND_SERVICE)
	$(COMPOSE) cp $(BOOKS_CSV) $(BACKEND_SERVICE):$(BOOKS_CSV_CONTAINER)
	$(COMPOSE) exec $(BACKEND_SERVICE) python manage.py import_books $(BOOKS_CSV_CONTAINER)

# ======================================
# 測試與覆蓋率
# ======================================
test: ## 執行 pytest（含輸出）
	$(COMPOSE) up -d $(BACKEND_SERVICE)
	$(COMPOSE) exec $(BACKEND_SERVICE) pytest -v

test-q: ## 安靜模式執行 pytest
	$(COMPOSE) up -d $(BACKEND_SERVICE)
	$(COMPOSE) exec $(BACKEND_SERVICE) pytest -q

cov: ## 產生測試覆蓋率報告
	$(COMPOSE) up -d $(BACKEND_SERVICE)
	$(COMPOSE) exec $(BACKEND_SERVICE) pytest --cov --cov-report=term-missing

# ======================================
# 資料庫相關
# ======================================
psql: ## 進入 PostgreSQL 命令列
	$(COMPOSE) exec $(DB_SERVICE) psql -U $$POSTGRES_USER -d $$POSTGRES_DB

db-shell: ## 進入資料庫容器 shell
	-$(COMPOSE) exec $(DB_SERVICE) bash || $(COMPOSE) exec $(DB_SERVICE) sh

# ======================================
# Ollama 模型管理
# ======================================
ollama-tags: ## 列出目前模型
	$(COMPOSE) exec $(OLLAMA_SERVICE) curl -s http://localhost:11434/api/tags | jq .

ollama-pull: ## 拉取模型（MODEL=llama3.1:8b-instruct）
	$(COMPOSE) exec $(OLLAMA_SERVICE) ollama pull $(MODEL)

ollama-ps: ## 查看 Ollama 進程
	$(COMPOSE) exec $(OLLAMA_SERVICE) ps aux | head -n 20

# ======================================
# 健康檢查
# ======================================
health: ## 檢查後端與管理後台是否回應
	@curl -s -o /dev/null -w "GET / -> %{http_code}\n" http://localhost:$(BACKEND_PORT)/
	@curl -s -o /dev/null -w "GET /admin/login/ -> %{http_code}\n" http://localhost:$(BACKEND_PORT)/admin/login/

# ======================================
# 前端操作
# ======================================
fe-dev: ## 啟動前端開發伺服器
	cd frontend && npm run dev

fe-build: ## 打包前端（production）
	cd frontend && npm run build
