#!/bin/bash

# =========================================================
# OpenClaw Discord Bot - Menadžer Proces
# =========================================================

BOT_DIR="/home/kizamladjanijebac/Desktop/discord-openclaw"
LOG_FILE="$BOT_DIR/discord_bot.log"
BOT_SCRIPT="discord_bot.py"
PYTHON_BIN="$BOT_DIR/venv/bin/python"

echo "🔄 Proveravam trenutni status bota..."

# 1. Ubijamo stare procese
OLD_PIDS=$(pgrep -f "$BOT_SCRIPT")
if [ -n "$OLD_PIDS" ]; then
    echo "⚠️ Pronađeni aktivni procesi ($OLD_PIDS). Isključujem..."
    pkill -f "$BOT_SCRIPT"
    sleep 2
else
    echo "✅ Bot trenutno ne radi (nema procesa)."
fi

# 2. Ulazak u direktorijum bota
cd "$BOT_DIR" || { echo "❌ Greška: Direktorijum $BOT_DIR ne postoji!"; exit 1; }

# 3. Bekap starog loga
if [ -f "$LOG_FILE" ]; then
    mv "$LOG_FILE" "${LOG_FILE}.bak"
    echo "💾 Stari log je sačuvan kao ${LOG_FILE}.bak"
fi

# 4. Provera Pythona
if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ Greška: VENV Python ($PYTHON_BIN) nije pronađen!"
    exit 1
fi

# 5. Pokretanje bota
echo "🚀 Pokrećem OpenClaw Discord Bot u pozadini..."
nohup "$PYTHON_BIN" "$BOT_SCRIPT" > "$LOG_FILE" 2>&1 &

# Dohvatanje novog PID-a
NEW_PID=$!
echo "✅ Bot je uspešno pokrenut sa PID: $NEW_PID"
echo "📄 Log fajl: $LOG_FILE"
echo ""
echo "Da pratiš šta bot radi uživo, pokreni:"
echo "tail -f $LOG_FILE"
echo ""
read -p "Pritisni Enter za izlaz..."
