#!/bin/bash
# 🧬 SWARM EVOLUTION LAUNCHER
# Ενσωματώνει το Evolution Engine στο swarm

SWARM_DIR="/root/.openclaw/workspace/swarm_general"
LOG_DIR="$SWARM_DIR/logs"
PID_DIR="$SWARM_DIR"

echo ""
echo "🧬 SWARM EVOLUTION ENGINE"
echo "=========================="
echo ""
echo "🎯 Goal: 9+/10 through continuous self-improvement"
echo "🔄 Mode: Auto-tune, self-monitor, evolve"
echo ""

# Create directories
mkdir -p $LOG_DIR
mkdir -p $SWARM_DIR/data

echo "📁 Directories ready"
echo ""

# Check if already running
if pgrep -f "evolution_engine.py" > /dev/null; then
    echo "⚠️  Evolution Engine already running!"
    echo "   Run './stop_evolution.sh' first if you want to restart"
    exit 1
fi

# Start Evolution Engine
echo "🚀 Starting Evolution Engine..."
cd $SWARM_DIR
nohup python3 -u core/evolution_engine.py > $LOG_DIR/evolution.log 2>&1 &
EVO_PID=$!
echo $EVO_PID > $PID_DIR/.evolution.pid

echo "   PID: $EVO_PID"
echo "   Log: $LOG_DIR/evolution.log"
echo ""

# Wait a moment for startup
sleep 3

# Check if running
if kill -0 $EVO_PID 2>/dev/null; then
    echo "✅ Evolution Engine RUNNING!"
    echo ""
    echo "📊 Monitoring:"
    echo "   tail -f $LOG_DIR/evolution.log"
    echo ""
    echo "🧬 Evolution Features:"
    echo "   • Auto-tuning based on performance"
    echo "   • Bottleneck detection every 60s"
    echo "   • Self-improvement recommendations"
    echo "   • Score tracking and optimization"
    echo "   • Pattern learning from history"
    echo ""
    echo "🎯 Current Score: Check with ./evolution_status.sh"
else
    echo "❌ Failed to start Evolution Engine"
    echo "   Check log: $LOG_DIR/evolution.log"
fi

echo ""
echo "🔥 Evolution is ACTIVE! 🧬"
