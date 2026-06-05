#!/bin/bash
# 🛑 ENHANCED SWARM STOPPER
# Σταματάει ΟΛΑ τα enhanced components

echo "🛑 Stopping Enhanced Swarm System..."

pkill -f "general_orchestrator.py" 2>/dev/null
pkill -f "realtime_interface.py" 2>/dev/null
pkill -f "enhanced_scanner.py" 2>/dev/null
pkill -f "background_monitor.py" 2>/dev/null
pkill -f "multichain_scanner.py" 2>/dev/null
pkill -f "auto_discovery.py" 2>/dev/null
pkill -f "websocket_feeds.py" 2>/dev/null

sleep 2

echo "✅ All Enhanced Swarm components stopped"

# Verify
running=$(ps aux | grep -E "general_orchestrator|realtime_interface|enhanced_scanner|multichain_scanner|auto_discovery|background_monitor|websocket_feeds" | grep -v grep | wc -l)

if [ "$running" -eq 0 ]; then
    echo "🟢 Confirmed: All stopped"
else
    echo "🟡 Warning: $running processes still running"
fi
