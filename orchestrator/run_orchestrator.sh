#!/bin/bash
# Run Script for Telegram Orchestrator Agent
# ===========================================

cd "$(dirname "$0")"

# Check if venv exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables
export ORCHESTRATOR_BOT_TOKEN="8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac"
export WORKSPACE_DIR="/root/.openclaw/workspace"
export LOG_LEVEL="INFO"

# Create logs directory
mkdir -p logs

echo "🔥 Starting Telegram Orchestrator Agent..."
echo "Bot: @WorkSS11_bot"
echo "Brain: AImind (OpenClaw)"
echo "Mode: Swarm Intelligence + Continuous Learning"
echo ""

# Run with auto-restart
while true; do
    echo "🚀 Launching orchestrator..."
    python3 telegram_orchestrator.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Orchestrator exited normally"
        break
    else
        echo "⚠️ Orchestrator crashed, restarting in 5 seconds..."
        sleep 5
    fi
done
