#!/bin/bash
# Live Sniper Launcher
cd /root/.openclaw/workspace/orchestrator
export PYTHONPATH=/root/.openclaw/workspace/orchestrator:$PYTHONPATH

# Kill old sniper
pkill -f "auto_sniper" 2>/dev/null
sleep 2

# Start live sniper
nohup python3 -m core.live_sniper > logs/live_sniper.log 2>&1 &
echo "Live Sniper started! PID: $!"
echo "Mode: LIVE"
echo "Log: logs/live_sniper.log"
