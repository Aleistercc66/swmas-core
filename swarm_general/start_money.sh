#!/bin/bash
cd /root/.openclaw/workspace/swarm_general
pkill -f "money_action_engine.py" 2>/dev/null
sleep 2
python3 core/money_action_engine.py >> logs/money_action.log 2>&1 &
echo "Money Engine restarted"
