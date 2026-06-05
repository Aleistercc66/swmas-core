#!/bin/bash
# Arbitrage Bot Launcher
# Runs all 3 arbitrage strategies in parallel

echo "🚀 ARBITRAGE BOT LAUNCHER"
echo "=========================="
echo ""

# Create logs directory
mkdir -p /root/.openclaw/workspace/agents/logs

# Check Python
echo "Checking Python..."
python3 --version || exit 1

# Install deps if needed
echo "Installing dependencies..."
pip install -q ccxt aiohttp 2>/dev/null || true

echo ""
echo "Select mode:"
echo "1) Paper Trading (safe, simulated)"
echo "2) Live Trading (⚠️ REAL MONEY)"
echo ""
read -p "Enter choice [1-2]: " choice

if [ "$choice" = "2" ]; then
    echo "⚠️ LIVE MODE SELECTED!"
    read -p "Type 'CONFIRM' to proceed: " confirm
    if [ "$confirm" != "CONFIRM" ]; then
        echo "Aborted."
        exit 1
    fi
    PAPER_FLAG=""
else
    echo "🧪 PAPER TRADING MODE"
    PAPER_FLAG="--paper"
fi

echo ""
echo "Choose strategy:"
echo "1) All Strategies (Cross-Exchange + Triangular + Funding)"
echo "2) Cross-Exchange Only"
echo "3) Triangular Only"
echo "4) Funding Rate Only"
echo ""
read -p "Enter choice [1-4]: " strategy

cd /root/.openclaw/workspace/agents

case $strategy in
    1)
        echo "🎯 Starting ALL ARBITRAGE STRATEGIES..."
        echo "   → Cross-Exchange Arbitrage"
        echo "   → Triangular Arbitrage"
        echo "   → Funding Rate Arbitrage"
        python3 arbitrage_orchestrator.py $PAPER_FLAG 2>&1 | tee logs/orchestrator_$(date +%Y%m%d_%H%M%S).log
        ;;
    2)
        echo "🔁 Starting Cross-Exchange Arbitrage..."
        python3 cross_exchange_arbitrage.py $PAPER_FLAG 2>&1 | tee logs/cross_$(date +%Y%m%d_%H%M%S).log
        ;;
    3)
        echo "🔺 Starting Triangular Arbitrage..."
        python3 triangular_arbitrage.py $PAPER_FLAG 2>&1 | tee logs/triangular_$(date +%Y%m%d_%H%M%S).log
        ;;
    4)
        echo "💸 Starting Funding Rate Arbitrage..."
        python3 funding_rate_arbitrage.py $PAPER_FLAG 2>&1 | tee logs/funding_$(date +%Y%m%d_%H%M%S).log
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Done!"
