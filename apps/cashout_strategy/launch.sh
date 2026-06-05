#!/bin/bash
# Stoiximan Cashout Strategy - Desktop Launcher
# ===============================================
# Usage: ./launch.sh [start|stop|status|install]

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$APP_DIR/.app.pid"
LOG_FILE="$APP_DIR/logs/launcher.log"
PORT=8080

# Check if port is available, if not find an open one
find_free_port() {
    local port=$1
    while lsof -i :$port >/dev/null 2>&1 || ss -tlnp 2>/dev/null | grep -q ":$port "; do
        port=$((port + 1))
    done
    echo $port
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 not found. Please install Python 3.8+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "✅ Python $PYTHON_VERSION found"
}

install_deps() {
    echo "📦 Installing dependencies..."
    cd "$APP_DIR"
    
    # Create virtual environment if not exists
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Virtual environment created"
    fi
    
    # Activate and install
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ Dependencies installed"
}

start_app() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "⚠️ App is already running (PID: $(cat "$PID_FILE"))"
        echo "   Visit: http://localhost:$PORT"
        return
    fi
    
    echo "🚀 Starting Cashout Strategy App..."
    cd "$APP_DIR"
    
    # Activate venv
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Find free port
    PORT=$(find_free_port $PORT)
    echo "📡 Using port: $PORT"
    
    # Save port for later
    echo $PORT > "$APP_DIR/.port"
    
    # Start the server in background
    nohup python3 -c "
import sys
sys.path.insert(0, '.')
from dashboard.server import run_server
run_server(port=$PORT)
" > "$LOG_FILE" 2>&1 &
    
    echo $! > "$PID_FILE"
    
    sleep 3
    
    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "✅ App started successfully!"
        echo ""
        echo "🌐 Dashboard: http://localhost:$PORT"
        echo "📊 API: http://localhost:$PORT/api"
        echo "📁 Guide: http://localhost:$PORT/guide"
        echo ""
        
        # Try to open browser
        if command -v xdg-open &> /dev/null; then
            xdg-open "http://localhost:$PORT" &
        elif command -v open &> /dev/null; then
            open "http://localhost:$PORT" &
        fi
        
        echo "Commands:"
        echo "  ./launch.sh status  - Check status"
        echo "  ./launch.sh stop    - Stop app"
    else
        echo "❌ Failed to start app. Check logs: $LOG_FILE"
        rm -f "$PID_FILE"
    fi
}

stop_app() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️ App is not running"
        return
    fi
    
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "🛑 Stopping app (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 1
        
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null
        fi
        
        echo "✅ App stopped"
    else
        echo "⚠️ App was not running"
    fi
    
    rm -f "$PID_FILE"
    rm -f "$APP_DIR/.port"
}

status_app() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        PID=$(cat "$PID_FILE")
        PORT=$(cat "$APP_DIR/.port" 2>/dev/null || echo "8080")
        echo "✅ App is RUNNING (PID: $PID)"
        echo "   Dashboard: http://localhost:$PORT"
        echo "   Log file: $LOG_FILE"
    else
        echo "⚠️ App is NOT running"
        rm -f "$PID_FILE"
    fi
}

# Main
case "${1:-start}" in
    install)
        check_python
        install_deps
        ;;
    start)
        check_python
        start_app
        ;;
    stop)
        stop_app
        ;;
    status)
        status_app
        ;;
    restart)
        stop_app
        sleep 1
        start_app
        ;;
    *)
        echo "Usage: $0 [install|start|stop|status|restart]"
        exit 1
        ;;
esac
