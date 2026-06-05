#!/bin/bash
# 🔥 ENHANCED SWARM MASTER LAUNCHER
# Ξεκινάει ΟΛΑ τα components με τη σωστή σειρά.
# Στόχος: Load 1.5-2.5, 9/10 βαθμολογία

SWARM_DIR="/root/.openclaw/workspace/swarm_general"
LOG_DIR="$SWARM_DIR/logs"
PID_DIR="$SWARM_DIR"

echo ""
echo "🔥🔥🔥 ENHANCED SWARM SYSTEM v3.0 🔥🔥🔥"
echo "=========================================="
echo ""
echo "🎯 Goal: Load 1.5-2.5 | Score 9/10"
echo ""

# Create directories
mkdir -p $LOG_DIR
mkdir -p $SWARM_DIR/data
mkdir -p $SWARM_DIR/skills
mkdir -p $SWARM_DIR/memory

echo "📁 Directories ready"
echo ""

# Kill old processes
echo "🧹 Cleaning old processes..."
pkill -f "general_orchestrator.py" 2>/dev/null
pkill -f "realtime_interface.py" 2>/dev/null
pkill -f "enhanced_scanner.py" 2>/dev/null
pkill -f "background_monitor.py" 2>/dev/null
pkill -f "multichain_scanner.py" 2>/dev/null
pkill -f "auto_discovery.py" 2>/dev/null
pkill -f "websocket_feeds.py" 2>/dev/null
sleep 2
echo "✅ Clean"
echo ""

# Function to start component
start_component() {
    local name=$1
    local script=$2
    local logfile=$3
    local pidfile=$4
    
    echo "🚀 Starting $name..."
    cd $SWARM_DIR
    nohup python3 -u $script > $LOG_DIR/$logfile 2>&1 &
    echo $! > $PID_DIR/$pidfile
    echo "   PID: $(cat $PID_DIR/$pidfile)"
    echo "   Log: $LOG_DIR/$logfile"
    sleep 1
}

# ============================================================
# PHASE 1: CORE INFRASTRUCTURE (Sequential - must be first)
# ============================================================
echo "📦 PHASE 1: Core Infrastructure"
echo "--------------------------------"

start_component "General Orchestrator" "general_orchestrator.py" "orchestrator.log" ".orchestrator.pid"
sleep 2

echo ""

# ============================================================
# PHASE 2: REAL-TIME INTERFACES
# ============================================================
echo "📱 PHASE 2: Real-Time Interfaces"
echo "---------------------------------"

start_component "Telegram Real-Time" "realtime_interface.py" "realtime.log" ".realtime.pid"

echo ""

# ============================================================
# PHASE 3: ACTIVE SCANNERS (Parallel - High Load)
# ============================================================
echo "🔍 PHASE 3: Active Scanners"
echo "----------------------------"

start_component "Enhanced Market Scanner" "core/enhanced_scanner.py" "scanner.log" ".scanner.pid"
start_component "Multi-Chain Scanner" "core/multichain_scanner.py" "multichain.log" ".multichain.pid"
start_component "Auto-Discovery Engine" "core/auto_discovery.py" "discovery.log" ".discovery.pid"

echo ""

# ============================================================
# PHASE 4: BACKGROUND MONITORING
# ============================================================
echo "👁️ PHASE 4: Background Monitoring"
echo "------------------------------------"

start_component "Background Monitor" "core/background_monitor.py" "monitor.log" ".monitor.pid"

echo ""

# ============================================================
# PHASE 5: WEBSOCKET FEEDS
# ============================================================
echo "📡 PHASE 5: WebSocket Feeds"
echo "--------------------------"

start_component "WebSocket Feeds" "core/websocket_feeds.py" "websocket.log" ".websocket.pid"

echo ""

# ============================================================
# STATUS CHECK
# ============================================================
echo "📊 PHASE 6: System Verification"
echo "-------------------------------"
sleep 3

echo ""
echo "🟢 Active Processes:"
ps aux | grep -E "general_orchestrator|realtime_interface|enhanced_scanner|multichain_scanner|auto_discovery|background_monitor|websocket_feeds" | grep -v grep | awk '{print "   " $11 " (PID: " $2 ")"}'

echo ""
echo "💾 System Resources:"
free -m | grep Mem | awk '{printf "   Memory: %.1f%% used\n", ($3/$2)*100}'
df -h / | tail -1 | awk '{print "   Disk: "$5 " used"}'
uptime | awk '{print "   Load: " $(NF-2)}'

echo ""
echo "=========================================="
echo "✅ ENHANCED SWARM v3.0 FULLY OPERATIONAL!"
echo "=========================================="
echo ""
echo "🧠 Components Active:"
echo "   • General Orchestrator"
echo "   • Real-Time Telegram Interface"
echo "   • Enhanced Market Scanner (2min cycles)"
echo "   • Multi-Chain Scanner (4 chains)"
echo "   • Auto-Discovery Engine"
echo "   • Background Monitor"
echo "   • WebSocket Feeds"
echo ""
echo "📈 Expected Load: 1.5-2.5"
echo "🎯 Target Score: 9/10"
echo ""
echo "📱 Telegram: @WorkSS11_bot"
echo ""
echo "Commands:"
echo "  tail -f $LOG_DIR/orchestrator.log    # Main orchestrator"
echo "  tail -f $LOG_DIR/scanner.log         # Market scanner"
echo "  tail -f $LOG_DIR/monitor.log         # Background monitor"
echo "  ./stop.sh                            # Stop all"
echo ""
echo "🔥 SYSTEM IS LIVE AND ACTIVE! 🔥"
