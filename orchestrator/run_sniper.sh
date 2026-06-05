#!/bin/bash
# Auto-Sniper Launcher
# Usage: ./run_sniper.sh [start|stop|status|restart]

SNIPER_DIR="/root/.openclaw/workspace/orchestrator"
LOG_FILE="$SNIPER_DIR/logs/sniper.log"
PID_FILE="/tmp/sniper.pid"

case "$1" in
  start)
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
      echo "🔫 Sniper already running (PID $(cat $PID_FILE))"
      exit 1
    fi
    echo "🔥 Starting Auto-Sniper Bot..."
    cd "$SNIPER_DIR"
    nohup python3 -m core.auto_sniper > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "✅ Sniper started (PID $(cat $PID_FILE))"
    echo "📊 Logs: $LOG_FILE"
    ;;
  stop)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      kill $PID 2>/dev/null && echo "🛑 Sniper stopped (PID $PID)" || echo "⚠️ Could not stop sniper"
      rm -f "$PID_FILE"
    else
      echo "⏹️ Sniper not running"
    fi
    ;;
  status)
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
      echo "🔥 Sniper RUNNING (PID $(cat $PID_FILE))"
      echo "📊 Last log lines:"
      tail -10 "$LOG_FILE" 2>/dev/null || echo "No logs yet"
    else
      echo "⏹️ Sniper STOPPED"
    fi
    ;;
  restart)
    $0 stop
    sleep 2
    $0 start
    ;;
  *)
    echo "Usage: $0 {start|stop|status|restart}"
    exit 1
    ;;
esac
