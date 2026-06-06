#!/bin/bash
# STOP ALL AUTONOMOUS REVENUE COMPONENTS

echo "⏹️  Stopping Autonomous Revenue Engine..."

for pid_file in revenue.pid telegram.pid dashboard.pid; do
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "   ✅ Stopped $pid_file (PID: $PID)"
        fi
        rm -f "$pid_file"
    fi
done

echo "✅ All components stopped"
