#!/bin/bash
cd /root/.openclaw/workspace/swarm_general/desktop_server
nohup python3 desktop_server.py > server.log 2>&1 &
echo "Server started on port 7777"
sleep 2
curl -s http://localhost:7777 | head -3
