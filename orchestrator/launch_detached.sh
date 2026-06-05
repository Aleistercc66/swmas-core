#!/bin/bash
# Robust detached launcher for Telegram Orchestrator Bot
# This script detaches the bot completely from the parent process

cd /root/.openclaw/workspace/orchestrator

# Kill any existing instances
pkill -9 -f "python3 telegram_orchestrator.py" 2>/dev/null
sleep 1

# Ensure logs dir exists
mkdir -p logs

# Launch with complete detachment:
# - setsid: new session, detach from terminal
# - nohup: ignore SIGHUP
# - >/dev/null 2>&1: close stdio
# - &: background
# - disown: remove from shell job table

(
  cd /root/.openclaw/workspace/orchestrator
  exec setsid nohup python3 telegram_orchestrator.py >> logs/bot_output.log 2>&1 &
)

# Wait a moment then check
sleep 2
PID=$(pgrep -f "python3 telegram_orchestrator.py" | head -1)

if [ -n "$PID" ]; then
    echo "✅ Bot running with PID: $PID"
    echo $PID > /tmp/orchestrator_bot.pid
    tail -20 logs/bot_output.log
else
    echo "❌ Failed to start bot"
    tail -30 logs/bot_output.log
fi
