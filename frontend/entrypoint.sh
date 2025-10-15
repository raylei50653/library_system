#!/bin/sh
set -e

cd /app

if [ ! -d node_modules ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
  echo "Installing frontend dependencies..."
  npm ci
fi

VITE_PORT="${VITE_PORT:-5173}"

exec npm run dev -- --host 0.0.0.0 --port "${VITE_PORT}" --strictPort
