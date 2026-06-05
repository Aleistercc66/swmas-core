#!/bin/bash
# ⚡ REAL-TIME SWARM LAUNCHER
# Starts the swarm with real-time interaction

echo "⚡ REAL-TIME SWARM INTERFACE ⚡"
echo "==============================="

# Check if orchestrator is running
if ! pgrep -f "general_orchestrator.py" > /dev/null; then
    echo "🔥 Starting General Swarm..."
    cd /root/.openclaw/workspace/swarm_general
    python3 general_orchestrator.py &
    sleep 2
fi

# Check if already running
if pgrep -f "realtime_interface.py" > /dev/null; then
    echo "⚡ Real-time interface already running!"
    echo "   PID: $(pgrep -f "realtime_interface.py")"
    exit 0
fi

echo "📡 Starting Real-Time Telegram Interface..."
echo "   Bot: @WorkSS11_bot"
echo ""
echo "🚀 Commands:"
echo "  /ask — Ask anything instantly"
echo "  /do  — Execute immediately"
echo "  /quick — Quick research"
echo "  /task — Submit task"
echo ""
echo "💡 Or just type anything!"
echo ""

# Run real-time interface
cd /root/.openclaw/workspace/swarm_general
nohup python3 realtime_interface.py > logs/realtime.log 2>> logs/realtime.log &
echo $! > .realtime.pid

echo "✅ Real-Time Interface STARTED!"
echo "   PID: $(cat .realtime.pid)"
echo ""
echo "🎯 Ready for instant interaction!"
