#!/bin/bash
# 🚀 GENERAL SWARM LAUNCHER
# Starts the General Purpose Swarm System

echo "🔥 SWMAS General Purpose Swarm 🔥"
echo "================================"

# Check if swarm_general directory exists
if [ ! -d "/root/.openclaw/workspace/swarm_general" ]; then
    echo "❌ swarm_general directory not found!"
    exit 1
fi

cd /root/.openclaw/workspace/swarm_general

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p memory
mkdir -p skills
mkdir -p tools
mkdir -p data

# Check Python
echo "🐍 Checking Python..."
python3 --version || { echo "❌ Python3 not found!"; exit 1; }

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q pyyaml 2>/dev/null || echo "⚠️ pyyaml install failed (may be already installed)"

# Check if orchestrator is already running
echo "🔍 Checking for existing processes..."
if pgrep -f "general_orchestrator.py" > /dev/null; then
    echo "⚠️ General Orchestrator already running!"
    echo "   PID: $(pgrep -f "general_orchestrator.py")"
    echo ""
    echo "Options:"
    echo "  1. Kill existing and restart"
    echo "  2. Attach to existing"
    echo "  3. Exit"
    read -p "Choice (1/2/3): " choice
    
    case $choice in
        1)
            echo "💀 Killing existing orchestrator..."
            pkill -f "general_orchestrator.py"
            sleep 2
            ;;
        2)
            echo "🔌 Attaching..."
            exit 0
            ;;
        *)
            echo "👋 Exiting..."
            exit 0
            ;;
    esac
fi

# Start the orchestrator
echo "🚀 Starting General Orchestrator..."
echo "=================================="
echo ""
echo "🌐 SWARM DIRECTIONS:"
echo "  1. 🕵️ Research & Intelligence"
echo "  2. ✍️ Content & Creation"
echo "  3. 🤖 Automation & Execution"
echo "  4. 📊 Monitoring & Alerting"
echo "  5. 🗣️ Communication & Coordination"
echo "  6. 🧮 Analysis & Decision Support"
echo "  7. 🔧 Problem Solving & Debugging"
echo "  8. 📚 Learning & Adaptation"
echo ""
echo "🤖 AGENTS READY:"
echo "  • ResearchAgent"
echo "  • ContentAgent"
echo "  • AutomationAgent"
echo "  • MonitorAgent"
echo "  • CommsAgent"
echo "  • AnalysisAgent"
echo "  • SolverAgent"
echo "  • LearnAgent"
echo ""
echo "📡 TELEGRAM: @WorkSS11_bot"
echo ""
echo "💪 POWER ON!"
echo ""

# Run in background with logging
nohup python3 general_orchestrator.py > logs/orchestrator.out 2>> logs/orchestrator.log &

# Save PID
echo $! > .orchestrator.pid

echo "✅ General Orchestrator started!"
echo "   PID: $(cat .orchestrator.pid)"
echo ""
echo "Commands:"
echo "  tail -f logs/orchestrator.log  # View logs"
echo "  ./stop.sh                      # Stop swarm"
echo "  ./status.sh                    # Check status"
echo ""
echo "🎯 Ready for tasks!"
