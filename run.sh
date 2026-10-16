#!/usr/bin/env bash
cd "$(dirname "$0")"

# Освобождаем порты 8000 и 8501, если там завис старый процесс
for PORT in 8000 8501; do
    PID=$(lsof -ti:$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "⚠️ Завершаем предыдущий процесс на порту $PORT (PID $PID)..."
        kill -9 "$PID" 2>/dev/null || true
        sleep 0.5
    fi
done

# Завершаем старый cloudflared если был
killall cloudflared 2>/dev/null || true

source venv/bin/activate
export PYTHONPATH=.

# Автоопределение архитектуры Python (поддержка Apple Silicon и x86_64)
PYTHON_CMD="./venv/bin/python3"
if ! $PYTHON_CMD -c "import sys" 2>/dev/null; then
    if arch -x86_64 $PYTHON_CMD -c "import sys" 2>/dev/null; then
        PYTHON_CMD="arch -x86_64 ./venv/bin/python3"
    fi
fi

echo "=========================================================="
echo "🚀 Запуск Qabyldau AI: Backend + Telegram Mini App + Bot"
echo "🌐 Локальный адрес: http://localhost:8000"
echo "=========================================================="

# Запуск cloudflared tunnel в фоне
if [ -f "./cloudflared" ]; then
    ./cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflared.log 2>&1 &
    CF_PID=$!
    echo "⚡ Запущен Cloudflare HTTPS Tunnel (PID $CF_PID)"
    # Ждем появления публичного HTTPS URL
    for i in {1..12}; do
        TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -n 1)
        if [ -n "$TUNNEL_URL" ]; then
            echo "📱 Публичный адрес Telegram Mini App: $TUNNEL_URL"
            $PYTHON_CMD -c "
import requests
from database.db import set_setting
import config
set_setting('webapp_url', '$TUNNEL_URL')
token = config.TELEGRAM_BOT_TOKEN
if token:
    try:
        requests.post(f'https://api.telegram.org/bot{token}/setChatMenuButton', json={
            'menu_button': {'type': 'web_app', 'text': '📱 Открыть Mini App', 'web_app': {'url': '$TUNNEL_URL'}}
        }, timeout=8)
    except Exception:
        pass
" 2>/dev/null || true
            break
        fi
        sleep 1
    done
fi

$PYTHON_CMD -m uvicorn server:app --host 0.0.0.0 --port 8000
