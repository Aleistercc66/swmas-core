#!/bin/bash
# 🛑 EVOLUTION ENGINE STOPPER

echo "🛑 Stopping Evolution Engine..."

# Kill evolution engine
pkill -f "evolution_engine.py" 2>/dev/null

# Remove PID file
rm -f /root/.openclaw/workspace/swarm_general/.evolution.pid

sleep 2

# Verify
if pgrep -f "evolution_engine.py" > /dev/null; then
    echo "⚠️  Still running, forcing kill..."
    pkill -9 -f "evolution_engine.py" 2>/dev/null
fi

echo "✅ Evolution Engine stopped"
