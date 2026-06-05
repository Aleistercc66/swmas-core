#!/bin/bash
# DexScreener Profit Scanner - Runs every 30 minutes
WORK_DIR="/root/.openclaw/workspace"
LOG_FILE="/tmp/dexscanner.log"

echo "[$(date)] Starting DexScreener Profit Scanner daemon..." >> $LOG_FILE

while true; do
    echo "[$(date)] Running scan..." >> $LOG_FILE
    cd $WORK_DIR && python3 profit_scanner_bot.py >> $LOG_FILE 2>&1
    echo "[$(date)] Scan complete. Sleeping 30 min..." >> $LOG_FILE
    sleep 1800
done
