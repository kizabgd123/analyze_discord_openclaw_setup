#!/bin/bash

case "$1" in
    start)
        systemctl --user start discord-openclaw.service
        echo "Bot pokrenut."
        ;;
    stop)
        systemctl --user stop discord-openclaw.service
        echo "Bot zaustavljen."
        ;;
    restart)
        systemctl --user restart discord-openclaw.service
        echo "Bot restartovan."
        ;;
    status)
        systemctl --user status discord-openclaw.service
        ;;
    logs)
        journalctl --user -u discord-openclaw.service -f
        ;;
    dashboard-start)
        PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        cd "$PROJECT_DIR"
        if [ -f .dashboard.pid ] && kill -0 $(cat .dashboard.pid) 2>/dev/null; then
            echo "Dashboard već radi (PID: $(cat .dashboard.pid))."
        else
            PYTHONPATH="$PROJECT_DIR" nohup "$PROJECT_DIR/.venv/bin/python3" dashboard_server.py > dashboard.log 2>&1 &
            echo $! > .dashboard.pid
            echo "Dashboard pokrenut na http://localhost:8000 (PID: $(cat .dashboard.pid))."
        fi
        ;;
    dashboard-stop)
        if [ -f .dashboard.pid ]; then
            PID=$(cat .dashboard.pid)
            kill "$PID" 2>/dev/null && echo "Dashboard zaustavljen (PID: $PID)." || echo "Proces nije pronađen."
            rm -f .dashboard.pid
        else
            echo "Dashboard nije pokrenut."
        fi
        ;;
    dashboard-status)
        if [ -f .dashboard.pid ] && kill -0 $(cat .dashboard.pid) 2>/dev/null; then
            echo "Dashboard radi (PID: $(cat .dashboard.pid)) na http://localhost:8000"
        else
            echo "Dashboard nije aktivan."
        fi
        ;;
    dashboard-build)
        PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        echo "Building React + Vite frontend..."
        cd "$PROJECT_DIR/frontend" && npm run build
        ;;
    *)
        echo "Upotreba: ./manage_bot.sh {start|stop|restart|status|logs|dashboard-start|dashboard-stop|dashboard-status|dashboard-build}"
        exit 1
esac
