#!/usr/bin/env bash
# =========================================================================
# Sanau.AI Background Service Manager for macOS (LaunchAgent)
# =========================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="kz.sanau.ai"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

case "$1" in
    install)
        echo "🔧 Установка фонового сервиса Sanau.AI в macOS LaunchAgents..."
        mkdir -p "$HOME/Library/LaunchAgents"
        cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${DIR}/run.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${DIR}/sanau_service.log</string>
    <key>StandardErrorPath</key>
    <string>${DIR}/sanau_service.log</string>
</dict>
</plist>
EOF
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        launchctl load "$PLIST_PATH"
        echo "✅ Сервис ${PLIST_LABEL} успешно установлен и запущен!"
        echo "💡 Теперь Sanau.AI автоматически запускается при включении Mac и работает в фоне 24/7."
        ;;

    uninstall)
        echo "🛑 Остановка и удаление фонового сервиса Sanau.AI..."
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        rm -f "$PLIST_PATH"
        for PORT in 8000 8501; do
            PID=$(lsof -ti:$PORT 2>/dev/null)
            [ -n "$PID" ] && kill -9 "$PID" 2>/dev/null || true
        done
        killall cloudflared 2>/dev/null || true
        echo "✅ Сервис удален."
        ;;

    start)
        if [ -f "$PLIST_PATH" ]; then
            launchctl load "$PLIST_PATH" 2>/dev/null || true
            launchctl start "$PLIST_LABEL"
            echo "🚀 Сервис запущен через launchctl."
        else
            echo "⚡ Фоновый запуск без LaunchAgent (nohup)..."
            nohup ./run.sh > sanau_service.log 2>&1 &
            echo "✅ Запущено в фоне (PID $!). Лог: sanau_service.log"
        fi
        ;;

    stop)
        echo "🛑 Остановка Sanau.AI..."
        if [ -f "$PLIST_PATH" ]; then
            launchctl stop "$PLIST_LABEL" 2>/dev/null || true
        fi
        for PORT in 8000 8501; do
            PID=$(lsof -ti:$PORT 2>/dev/null)
            [ -n "$PID" ] && kill -9 "$PID" 2>/dev/null || true
        done
        killall cloudflared 2>/dev/null || true
        echo "✅ Все фоновые процессы остановлены."
        ;;

    status)
        echo "🔍 Статус процессов Sanau.AI:"
        PID_8000=$(lsof -ti:8000 2>/dev/null)
        if [ -n "$PID_8000" ]; then
            echo "🟢 Backend & Telegram Bot активен (PID $PID_8000 на порту 8000)"
        else
            echo "🔴 Backend не запущен на порту 8000"
        fi
        
        PID_CF=$(pgrep cloudflared 2>/dev/null)
        if [ -n "$PID_CF" ]; then
            echo "🟢 Cloudflare Tunnel активен (PID $PID_CF)"
            URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -n 1)
            [ -n "$URL" ] && echo "📱 Публичный URL Mini App: $URL"
        else
            echo "⚪ Cloudflare Tunnel не запущен"
        fi
        ;;

    log)
        tail -n 40 -f "${DIR}/sanau_service.log"
        ;;

    *)
        echo "Использование: ./service.sh {install|uninstall|start|stop|status|log}"
        echo "  install   - настроить автозапуск при входе в macOS и запустить 24/7"
        echo "  uninstall - отключить автозапуск macOS"
        echo "  start     - запустить сервис"
        echo "  stop      - остановить сервис"
        echo "  status    - проверить статус работы и публичный URL"
        echo "  log       - смотреть логи в реальном времени"
        exit 1
        ;;
esac
