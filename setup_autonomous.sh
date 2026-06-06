#!/bin/bash
# FULL AUTONOMOUS REVENUE ENGINE SETUP
# Sets up everything: Telegram, Dashboard, Cron, 24/7 Background

echo "🔥🔥🔥 AUTONOMOUS REVENUE ENGINE SETUP 🔥🔥🔥"
echo ""

WORKSPACE="/root/.openclaw/workspace"

# 1. Check if Python and required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import aiohttp, asyncio, websockets" 2>/dev/null || pip install aiohttp websockets

# 2. Create Telegram Bot Config
echo "🤖 Setting up Telegram Bot..."
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "⚠️  TELEGRAM_BOT_TOKEN not set!"
    echo "   Get one from @BotFather on Telegram"
    echo "   Then run: export TELEGRAM_BOT_TOKEN='your_token'"
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "⚠️  TELEGRAM_CHAT_ID not set!"
    echo "   Get your ID from @userinfobot on Telegram"
    echo "   Then run: export TELEGRAM_CHAT_ID='your_id'"
fi

# 3. Create dashboard directory
mkdir -p $WORKSPACE/dashboard

# 4. Setup cron for auto-start
echo "⏰ Setting up cron (auto-start every hour)..."
(crontab -l 2>/dev/null | grep -v "launch_revenue.py"; echo "0 * * * * cd $WORKSPACE && python3 launch_revenue.py >> revenue.log 2>&1") | crontab -

# 5. Create start script
cat > $WORKSPACE/start_all.sh << 'EOF'
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
EOF

chmod +x $WORKSPACE/start_all.sh

# 6. Create stop script
cat > $WORKSPACE/stop_all.sh << 'EOF'
#!/bin/bash
# STOP ALL AUTONOMOUS REVENUE COMPONENTS

echo "⏹️  Stopping Autonomous Revenue Engine..."

for pid_file in revenue.pid telegram.pid dashboard.pid; do
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "   ✅ Stopped $pid_file (PID: $PID)"
        fi
        rm -f "$pid_file"
    fi
done

echo "✅ All components stopped"
EOF

chmod +x $WORKSPACE/stop_all.sh

# 7. Create status script
cat > $WORKSPACE/status.sh << 'EOF'
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
EOF

chmod +x $WORKSPACE/status.sh

echo ""
echo "🔥🔥🔥 SETUP COMPLETE! 🔥🔥🔥"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Set Telegram credentials:"
echo "   export TELEGRAM_BOT_TOKEN='your_bot_token'"
echo "   export TELEGRAM_CHAT_ID='your_chat_id'"
echo ""
echo "2. Set Live Wallet (optional):"
echo "   export SOLANA_PRIVATE_KEY='your_base58_key'"
echo "   export USE_LIVE_WALLET=true"
echo ""
echo "3. Start everything:"
echo "   bash $WORKSPACE/start_all.sh"
echo ""
echo "4. Check status:"
echo "   bash $WORKSPACE/status.sh"
echo ""
echo "5. View dashboard:"
echo "   http://localhost:8080"
echo ""
echo "🚀 Ready to print money autonomously!"