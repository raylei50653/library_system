FROM node:20-alpine

WORKDIR /app

# 安裝依賴（利用快取）
COPY package*.json ./
RUN npm ci

# 複製專案原始碼（提供預設 entrypoint）
COPY . .

EXPOSE 5173

CMD ["sh", "/app/entrypoint.sh"]
