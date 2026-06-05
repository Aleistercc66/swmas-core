#!/bin/bash
# 🔥 EMERGENCY SYSTEM RESTORE + PROFIT PIPELINE ACTIVATION
# Επαναφέρει τον scanner και ενεργοποιεί το profit pipeline

SWARM_DIR="/root/.openclaw/workspace/swarm_general"
LOG_DIR="$SWARM_DIR/logs"

cd $SWARM_DIR

echo "🔥 RESTORING SWARM SYSTEM + PROFIT PIPELINE"
echo "============================================"
echo ""

# 1. Kill any zombie scanner processes
pkill -f "enhanced_scanner.py" 2>/dev/null
sleep 1

# 2. Restart Enhanced Scanner (with new tuning-aware code)
echo "🚀 Restarting Enhanced Scanner..."
nohup python3 -u core/enhanced_scanner.py >> logs/scanner.log 2>&1 &
SCANNER_PID=$!
echo "   Scanner PID: $SCANNER_PID"
sleep 2

# 3. Verify scanner is running
if kill -0 $SCANNER_PID 2>/dev/null; then
    echo "   ✅ Scanner RUNNING"
else
    echo "   ❌ Scanner FAILED to start"
fi

echo ""

# 4. Show current system state
echo "📊 CURRENT SYSTEM STATE:"
echo "----------------------"

# Evolution state
if [ -f "$SWARM_DIR/data/evolution_state.json" ]; then
    python3 -c "
import json
with open('$SWARM_DIR/data/evolution_state.json') as f:
    d = json.load(f)
print(f'  Evolution: Gen {d[\"generation\"]}, Score {d[\"current_score\"]:.2f}/10')
print(f'  Improvements: {len([i for i in d.get(\"improvements\",[]) if i.get(\"status\")==\"applied\"])} applied')
" 2>/dev/null
fi

# Scanner tuning
if [ -f "$SWARM_DIR/data/scanner_tuning.json" ]; then
    echo "  Scanner tuning:"
    cat "$SWARM_DIR/data/scanner_tuning.json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"    interval: {d.get('scan_interval')}s, liq: \${d.get('min_liquidity'):,}\")"
fi

# Active processes
echo ""
echo "  Active processes:"
ps aux | grep -E "orchestrator|realtime|multichain|auto_discovery|background_monitor|websocket_feeds|evolution_engine|enhanced_scanner" | grep -v grep | awk '{print "    PID " $2 ": " $11}'

echo ""
echo "============================================"
echo "✅ SYSTEM RESTORED!"
echo ""
echo "🔍 MONITORING:"
echo "  tail -f $LOG_DIR/scanner.log     # Scanner"
echo "  tail -f $LOG_DIR/evolution.log   # Evolution"
echo "  tail -f $LOG_DIR/discovery.log     # Signals"
echo ""
echo "🎯 PROFIT PIPELINE STATUS:"
echo "  Scanner → AI Scoring → Signal Generation → Telegram Alerts"
echo ""
echo "📈 Next: Scanner will pick up tuning (60s interval) and"
echo "        start finding opportunities with relaxed filters"
