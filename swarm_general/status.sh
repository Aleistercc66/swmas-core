#!/bin/bash
# 📊 ENHANCED SWARM STATUS CHECKER

echo ""
echo "📊 ENHANCED SWARM SYSTEM STATUS"
echo "================================"
echo ""

# Check all processes
echo "🤖 Active Processes:"
echo "------------------"

components=(
    "general_orchestrator.py:🧠 Orchestrator"
    "realtime_interface.py:📱 Telegram RT"
    "enhanced_scanner.py:🔍 Market Scanner"
    "multichain_scanner.py:🌐 Multi-Chain"
    "auto_discovery.py:🎯 Auto-Discovery"
    "background_monitor.py:👁️ Background Monitor"
    "websocket_feeds.py:📡 WebSocket Feeds"
)

running=0
total=0

for component in "${components[@]}"; do
    IFS=':' read -r script name <<< "$component"
    total=$((total + 1))
    
    pid=$(pgrep -f "$script")
    if [ -n "$pid" ]; then
        echo "  ✅ $name | PID: $pid"
        running=$((running + 1))
    else
        echo "  ❌ $name | STOPPED"
    fi
done

echo ""
echo "📈 Component Status: $running/$total running"
echo ""

# System resources
echo "💾 System Resources:"
echo "-------------------"

# Memory
mem_total=$(free -m | grep Mem | awk '{print $2}')
mem_used=$(free -m | grep Mem | awk '{print $3}')
mem_pct=$((mem_used * 100 / mem_total))
echo "  Memory: ${mem_used}MB / ${mem_total}MB (${mem_pct}%)"

# Disk
disk_usage=$(df -h / | tail -1 | awk '{print $5}')
echo "  Disk: $disk_usage used"

# Load
load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
echo "  Load: $load"

# CPU cores
cores=$(nproc)
echo "  CPU Cores: $cores"

echo ""

# Score calculation
echo "🎯 Performance Score:"
echo "--------------------"

# Calculate score based on running components and system health
score=0

# Component score (up to 50 points)
component_score=$((running * 50 / total))
score=$((score + component_score))

# System health score (up to 30 points)
if [ "$mem_pct" -lt 50 ]; then
    health_score=30
elif [ "$mem_pct" -lt 75 ]; then
    health_score=20
elif [ "$mem_pct" -lt 90 ]; then
    health_score=10
else
    health_score=5
fi
score=$((score + health_score))

# Load score (up to 20 points)
# Ideal load: 1.0-2.0 per core
load_num=$(echo "$load" | awk '{printf "%d", $1}')
if [ "$load_num" -ge 1 ] && [ "$load_num" -le 3 ]; then
    load_score=20
elif [ "$load_num" -ge 4 ] && [ "$load_num" -le 6 ]; then
    load_score=15
elif [ "$load_num" -gt 0 ]; then
    load_score=10
else
    load_score=0
fi
score=$((score + load_score))

# Display score
echo "  Component Score: $component_score/50"
echo "  System Health: $health_score/30"
echo "  Load Score: $load_score/20"
echo ""
echo "  TOTAL SCORE: $score/100"

# Grade
if [ "$score" -ge 90 ]; then
    echo "  Grade: 🔥🔥🔥 S-TIER (9-10/10)"
elif [ "$score" -ge 75 ]; then
    echo "  Grade: 🔥🔥 A-TIER (7-8/10)"
elif [ "$score" -ge 60 ]; then
    echo "  Grade: 🔥 B-TIER (5-6/10)"
elif [ "$score" -ge 40 ]; then
    echo "  Grade: ⚡ C-TIER (3-4/10)"
else
    echo "  Grade: ⚠️ D-TIER (0-2/10)"
fi

echo ""
echo "================================"

# Recommendations
echo ""
if [ "$running" -lt "$total" ]; then
    echo "💡 Run ./start_enhanced.sh to start all components"
fi

if [ "$load_num" -lt 1 ]; then
    echo "💡 Load is low. System is underutilized."
fi

echo ""
