#!/bin/bash
# START ALL AUTONOMOUS REVENUE COMPONENTS

WORKSPACE="/root/.openclaw/workspace"
LOG_DIR="$WORKSPACE/logs"
mkdir -p $LOG_DIR

echo "🔥🔥🔥 STARTING AUTONOMOUS REVENUE ENGINE 🔥🔥🔥"
echo "📅 $(date)"
echo ""

# 1. Start Revenue Engine (background)
echo "🚀 Starting Revenue Engine (24/7)..."
nohup python3 $WORKSPACE/launch_revenue.py > $LOG_DIR/revenue.log 2>&1 &
echo $! > $WORKSPACE/revenue.pid

# 2. Start Telegram Bot (background)
echo "🤖 Starting Telegram Bot..."
nohup python3 $WORKSPACE/telegram_bot.py > $LOG_DIR/telegram.log 2>&1 &
echo $! > $WORKSPACE/telegram.pid

# 3. Start WebSocket Dashboard Server
echo "📊 Starting Dashboard Server..."
nohup python3 $WORKSPACE/dashboard_server.py > $LOG_DIR/dashboard.log 2>&1 &
echo $! > $WORKSPACE/dashboard.pid

echo ""
echo "✅ ALL SYSTEMS RUNNING!"
echo ""
echo "📊 Dashboard: http://localhost:8080"
echo "📁 Logs: $LOG_DIR/"
echo "📱 Telegram: Check your bot for alerts"
echo ""
echo "🛑 To stop: bash $WORKSPACE/stop_all.sh"
echo "🔍 Status: bash $WORKSPACE/status.sh"
