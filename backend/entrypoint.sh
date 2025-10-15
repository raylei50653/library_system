#!/bin/sh
set -eu

log() { printf '%s %s\n' "[entrypoint]" "$*"; }

# --- 等待資料庫 ---
log "waiting for database..."
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

i=0
until pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; do
  i=$((i+1))
  if [ "$i" -ge 60 ]; then
    log "ERROR: database not ready after 60s"
    exit 1
  fi
  sleep 1
done
log "database is ready"

# --- 等待 Ollama，並確保模型存在（如果設定了 OLLAMA_URL） ---
if [ -n "${OLLAMA_URL:-}" ]; then
  log "waiting for ollama at ${OLLAMA_URL}..."
  i=0
  until curl -fsS "${OLLAMA_URL}/api/version" >/dev/null 2>&1; do
    i=$((i+1))
    if [ "$i" -ge 180 ]; then
      log "ERROR: ollama not ready after 180s"
      exit 1
    fi
    sleep 1
  done
  log "ollama is ready"

  MODEL="${INIT_OLLAMA_MODEL:-${OLLAMA_MODEL:-}}"
  if [ -n "${MODEL}" ]; then
    log "ensuring model '${MODEL}' exists (will pull if missing)..."

    # 取 tags 並在單行內檢查 "name":"<MODEL>"
    TAGS="$(curl -fsS "${OLLAMA_URL}/api/tags" || true)"
    echo "$TAGS" | tr -d '\n' | grep -F "\"name\":\"${MODEL}\"" >/dev/null 2>&1 || {
      log "pulling ${MODEL} via Ollama HTTP API..."
      JSON="$(printf '{"name":"%s"}' "$MODEL")"
      # 觸發拉取（非串流），失敗不致命，之後後端用到時也會觸發下載
      curl -fsS -H 'Content-Type: application/json' \
        -X POST "${OLLAMA_URL}/api/pull" -d "$JSON" || \
        log "WARN: pull request non-zero (download may continue in background)"
    }
  fi
fi

# --- Django 啟動 ---
python manage.py migrate --noinput
if ! python manage.py collectstatic --noinput; then
  log "WARN: collectstatic failed (continuing; static assets may be stale)"
fi
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
log "starting gunicorn with timeout ${GUNICORN_TIMEOUT}s"
exec gunicorn config.wsgi:application -b 0.0.0.0:8000 --timeout "$GUNICORN_TIMEOUT"
