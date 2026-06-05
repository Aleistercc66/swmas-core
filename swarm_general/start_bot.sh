#!/bin/bash
cd /root/.openclaw/workspace/swarm_general
nohup python3 realtime_interface.py > logs/realtime_interface.log 2>&1 &
echo "Bot started with PID: $!"
sleep 5
cat logs/realtime_interface.log | tail -5
