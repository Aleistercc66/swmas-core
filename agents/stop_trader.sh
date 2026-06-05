#!/bin/bash
# 🛑 Stop Solana Pro Trader

DIR="/root/.openclaw/workspace/agents"
PID_FILE="$DIR/tmp_state/pro_trader.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if kill -0 "$PID" 2>/dev/null; then
        echo "🔪 Killing trader (PID $PID)..."
        kill -9 "$PID" 2>/dev/null
        echo "✅ Trader stopped"
    else
        echo "⚠️ Process not found, cleaning up..."
    fi
    rm -f "$PID_FILE"
else
    echo "No PID file found, checking for processes..."
    pkill -f solana_pro_trader.py 2>/dev/null
    echo "✅ Cleanup done"
fi

# Send Telegram alert
python3 -c "
import urllib.request
import json
TOKEN='8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc'
CHAT='158923136'
url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
data = json.dumps({
    'chat_id': CHAT,
    'text': '🛑 *Solana Pro Trader STOPPED*',
    'parse_mode': 'Markdown'
}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except:
    pass
" 2>/dev/null
