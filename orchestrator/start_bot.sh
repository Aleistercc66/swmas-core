#!/bin/bash
cd /root/.openclaw/workspace/orchestrator
python3 telegram_orchestrator.py > logs/bot_output.log 2>&1 &
echo "Bot PID: $!"
sleep 5
tail -20 logs/bot_output.log
