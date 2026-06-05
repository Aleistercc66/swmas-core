#!/bin/bash
pkill -f telegram_orchestrator.py 2>/dev/null
sleep 2
cd /root/.openclaw/workspace/orchestrator
python3 start_bot.py
