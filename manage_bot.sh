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
    *)
        echo "Upotreba: ./manage_bot.sh {start|stop|restart|status|logs}"
        exit 1
esac
