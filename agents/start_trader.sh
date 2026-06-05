#!/bin/bash
# 🚀 Start Solana Pro Trader
# Usage: ./start_trader.sh [paper|live] [--force]

MODE="${1:-paper}"
FORCE="${2:-}"
DIR="/root/.openclaw/workspace/agents"
LOG="$DIR/logs/trader_startup.log"

mkdir -p "$DIR/logs"

echo "🎯 Starting Solana Pro Trader..." | tee -a "$LOG"
echo "   Mode: $MODE" | tee -a "$LOG"
echo "   Time: $(date)" | tee -a "$LOG"

# Check if already running
PID_FILE="$DIR/tmp_state/pro_trader.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if kill -0 "$PID" 2>/dev/null; then
        echo "⚠️ Trader already running (PID $PID)" | tee -a "$LOG"
        if [ "$FORCE" == "--force" ]; then
            echo "🔪 Killing existing process..." | tee -a "$LOG"
            kill -9 "$PID" 2>/dev/null
            rm -f "$PID_FILE"
            sleep 2
        else
            echo "   Use: ./start_trader.sh $MODE --force" | tee -a "$LOG"
            exit 1
        fi
    else
        rm -f "$PID_FILE"
    fi
fi

# Start trader
cd "$DIR"
python3 solana_pro_trader.py --mode "$MODE" $FORCE 2>&1 | tee -a "$LOG" &
TRADER_PID=$!

# Save PID
echo $TRADER_PID > "$PID_FILE"

echo "✅ Trader started (PID $TRADER_PID)" | tee -a "$LOG"
echo "   Logs: $DIR/logs/pro_trader.log" | tee -a "$LOG"
echo "   Monitor: tail -f $DIR/logs/pro_trader.log" | tee -a "$LOG"

# Send Telegram alert
python3 -c "
import urllib.request
import json
TOKEN='8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc'
CHAT='158923136'
url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
data = json.dumps({
    'chat_id': CHAT,
    'text': '🎯 *Solana Pro Trader STARTED*\n\nMode: \`$MODE\`\nPID: \`$TRADER_PID\`\nTime: $(date +%H:%M:%S)',
    'parse_mode': 'Markdown'
}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except:
    pass
" 2>/dev/null

echo ""
echo "To stop: kill $TRADER_PID or pkill -f solana_pro_trader.py"
