#!/bin/bash
# RESTART ALL SWARM SYSTEMS

echo "=========================================="
echo "  SWARM SYSTEM RESTART"
echo "=========================================="

# Kill everything
echo "🔴 Killing old processes..."
pkill -f "realtime_interface.py" 2>/dev/null
pkill -f "money_action_engine.py" 2>/dev/null
pkill -f "evolution_engine.py" 2>/dev/null
pkill -f "enhanced_scanner.py" 2>/dev/null
pkill -f "desktop_server.py" 2>/dev/null
pkill -f "telegram_alert.py" 2>/dev/null
pkill -f "profit_engine.py" 2>/dev/null
sleep 3

echo "✅ Old processes killed"
echo ""

# Start everything
cd /root/.openclaw/workspace/swarm_general

echo "🤖 Starting Telegram Bot..."
nohup python3 realtime_interface.py > logs/realtime_interface.log 2>&1 &
echo "  PID: $!"
sleep 2

echo "🔍 Starting Enhanced Scanner..."
nohup python3 core/enhanced_scanner.py > logs/scanner.log 2>&1 &
echo "  PID: $!"
sleep 1

echo "💰 Starting Money Engine..."
nohup python3 core/money_action_engine.py > logs/money_action.log 2>&1 &
echo "  PID: $!"
sleep 1

echo "🧬 Starting Evolution Engine..."
nohup python3 core/evolution_engine.py > logs/evolution.log 2>&1 &
echo "  PID: $!"
sleep 1

echo "📤 Starting Telegram Alerts..."
nohup python3 core/telegram_alert.py > logs/telegram_alerts.log 2>&1 &
echo "  PID: $!"
sleep 1

echo "💻 Starting Desktop Server..."
cd /root/.openclaw/workspace/swarm_general/desktop_server
nohup python3 desktop_server.py > server.log 2>&1 &
echo "  PID: $!"

echo ""
echo "=========================================="
echo "  ALL SYSTEMS STARTED!"
echo "=========================================="
echo ""
echo "  🤖 Bot: @WorkSS11_bot"
echo "  💻 Dashboard: http://localhost:7777"
echo ""
sleep 2

# Show status
echo "📊 Running Processes:"
ps aux | grep -E "realtime_interface|money_action|evolution_engine|enhanced_scanner|desktop_server|telegram_alert" | grep -v grep | awk '{printf "  PID: %s | %s | CPU: %s%% | MEM: %s%%\n", $2, $11, $3, $4}'
