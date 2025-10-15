FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 系統相依：curl / pg_isready 必須要有
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash appuser

WORKDIR /app

# 先安裝依賴，加速快取
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 複製專案
COPY . /app
RUN chmod +x /app/entrypoint.sh

# 可選：先建立 STATIC_ROOT，避免 runtime collectstatic 找不到
# 若你的 settings.py 有 STATIC_ROOT，例如 /app/staticfiles
RUN mkdir -p /app/staticfiles
RUN chown -R appuser:appuser /app

# 不在 build 階段 collectstatic，交給 entrypoint（因為它已經會做）
# EXPOSE 只是文件化，保留
EXPOSE 8000

# 安全一點：用非 root 執行（可選）
USER appuser

# 交棒給 entrypoint（或保留 CMD，二擇一即可）
ENTRYPOINT ["/app/entrypoint.sh"]
# 如果你偏好 CMD，也可以改成：
# CMD ["/app/entrypoint.sh"]
