#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 🤖 SMART MONEY TRACKER — Launcher
# ═══════════════════════════════════════════════════════════

set -e

AGENT_DIR="/root/.openclaw/workspace/agents"
LOG_FILE="/root/.openclaw/workspace/logs/smart_money.log"
PID_FILE="/tmp/smart_money_tracker.pid"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

mkdir -p /root/.openclaw/workspace/logs

function show_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
   _____                      __  __      _       _   _             
  / ____|                    |  \/  |    | |     | | (_)            
 | (___  _ __ ___   __ _ _ __| \  / | ___| |_ ___| |_ _  ___  _ __  
  \___ \| '_ ` _ \ / _` | '__| |\/| |/ _ \ __/ __| __| |/ _ \| '_ \ 
  ____) | | | | | | (_| | |  | |  | |  __/ || (__| |_| | (_) | | | |
 |_____/|_| |_| |_|\__,_|_|  |_|  |_|\___|\__\___|\__|_|\___/|_| |_|
                                                                  
EOF
    echo -e "${NC}"
    echo -e "${GREEN}🎯 Smart Money Tracker Agent${NC}"
    echo -e "${GREEN}📡 Real-time blockchain analysis & wallet tracking${NC}"
    echo ""
}

function start() {
    show_banner
    
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo -e "${YELLOW}⚠️ Agent is already running!${NC}"
        echo "PID: $(cat $PID_FILE)"
        return 1
    fi
    
    echo -e "${GREEN}🚀 Starting Smart Money Tracker...${NC}"
    
    cd "$AGENT_DIR"
    
    nohup python3 smart_money_commands.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 2
    
    if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo -e "${GREEN}✅ Agent started successfully!${NC}"
        echo -e "${CYAN}📊 PID: $(cat $PID_FILE)${NC}"
        echo -e "${CYAN}📝 Log: $LOG_FILE${NC}"
        echo ""
        echo -e "${YELLOW}Commands:${NC}"
        echo -e "  /discover  — Find smart money wallets"
        echo -e "  /track     — Track a specific wallet"
        echo -e "  /list      — List all discovered wallets"
        echo -e "  /stats     — Agent statistics"
        echo -e "  /top       — Top performing wallets"
        echo -e "  /analyze   — Deep wallet analysis"
    else
        echo -e "${RED}❌ Failed to start agent!${NC}"
        return 1
    fi
}

function stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${YELLOW}🛑 Stopping Smart Money Tracker...${NC}"
            kill "$PID"
            sleep 1
            if ! kill -0 "$PID" 2>/dev/null; then
                echo -e "${GREEN}✅ Agent stopped!${NC}"
            else
                echo -e "${RED}⚠️ Force killing...${NC}"
                kill -9 "$PID"
            fi
        fi
        rm -f "$PID_FILE"
    else
        echo -e "${YELLOW}⚠️ Agent is not running.${NC}"
    fi
}

function status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo -e "${GREEN}✅ Smart Money Tracker is RUNNING${NC}"
        echo -e "${CYAN}📊 PID: $(cat $PID_FILE)${NC}"
        
        if [ -f "$LOG_FILE" ]; then
            echo -e "${CYAN}📝 Recent log entries:${NC}"
            tail -n 10 "$LOG_FILE"
        fi
    else
        echo -e "${RED}❌ Smart Money Tracker is NOT RUNNING${NC}"
    fi
}

function logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${CYAN}📝 Showing logs (Ctrl+C to exit)...${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${RED}❌ No log file found.${NC}"
    fi
}

function restart() {
    stop
    sleep 2
    start
}

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs|log)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
