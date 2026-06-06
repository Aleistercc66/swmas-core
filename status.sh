#!/bin/bash
# CHECK STATUS OF ALL COMPONENTS

echo "📊 AUTONOMOUS REVENUE ENGINE STATUS"
echo "───────────────────────────────────────"

for name in Revenue Telegram Dashboard; do
    pid_file=$(echo $name | tr '[:upper:]' '[:lower:]').pid
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if kill -0 $PID 2>/dev/null; then
            echo "✅ $name: RUNNING (PID: $PID)"
        else
            echo "❌ $name: STOPPED (PID: $PID dead)"
        fi
    else
        echo "⚠️  $name: NOT STARTED"
    fi
done

echo ""
echo "📈 Revenue Log (last 5 lines):"
tail -5 /root/.openclaw/workspace/logs/revenue.log 2>/dev/null || echo "   No log yet"

echo ""
echo "💰 Latest State:"
cat /root/.openclaw/workspace/revenue_state.json 2>/dev/null | python3 -m json.tool || echo "   No state yet"
