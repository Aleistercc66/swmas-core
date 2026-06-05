#!/bin/bash
# Unified DeFi Trading Bot Launcher
# Launches ALL DeFi trading strategies

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        🌐 UNIFIED DEFI TRADING ORCHESTRATOR 🌐           ║"
echo "║                                                            ║"
echo "║  Strategies:                                               ║"
echo "║    🔄 Cross-Exchange Arbitrage (CEX: Binance/Bybit/OKX)   ║"
echo "║    ⚡ Flash Loan Arbitrage (Aave/dYdX - Zero Capital)      ║"
echo "║    ☀️ Solana Jupiter Trading (Raydium/Orca/Phoenix)       ║"
echo "║    🔗 Web3 Ethereum Trading (Uniswap/SushiSwap/Curve)    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found${NC}"
    exit 1
fi

# Create logs directory
mkdir -p /root/.openclaw/workspace/agents/logs

# Check dependencies
echo -e "${BLUE}📦 Checking dependencies...${NC}"
python3 -c "
import sys
required = ['web3', 'solana', 'ccxt', 'aiohttp']
missing = []
for pkg in required:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print(f'❌ Missing: {', '.join(missing)}')
    print('Installing...')
    sys.exit(1)
else:
    print('✅ All dependencies installed')
    sys.exit(0)
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}📥 Installing dependencies...${NC}"
    pip install -r /root/.openclaw/workspace/agents/requirements_defi.txt --break-system-packages 2>&1 | tail -5
fi

echo ""
echo -e "${YELLOW}⚙️  Configuration:${NC}"
echo "1) Paper Trading (safe, simulated)"
echo "2) Live Trading (⚠️  REAL MONEY - requires private keys)"
echo ""
read -p "Select mode [1-2]: " mode

if [ "$mode" = "2" ]; then
    echo -e "${RED}⚠️  LIVE MODE SELECTED${NC}"
    echo "This will trade with REAL money!"
    read -p "Type 'LIVE' to confirm: " confirm
    if [ "$confirm" != "LIVE" ]; then
        echo -e "${YELLOW}Switched to paper trading${NC}"
        mode=1
    fi
fi

echo ""
echo -e "${YELLOW}🎯 Strategy Selection:${NC}"
echo "1) ALL STRATEGIES (recommended)"
echo "2) Web3 Ethereum Trading only"
echo "3) Solana Jupiter Trading only"
echo "4) Flash Loan Arbitrage only"
echo "5) Cross-Exchange CEX Arbitrage only"
echo "6) Custom combination"
echo ""
read -p "Select strategy [1-6]: " strategy

cd /root/.openclaw/workspace/agents

case $strategy in
    1)
        echo -e "${GREEN}🚀 Starting ALL strategies...${NC}"
        python3 defi_orchestrator.py 2>&1 | tee logs/defi_$(date +%Y%m%d_%H%M%S).log
        ;;
    2)
        echo -e "${GREEN}🔗 Starting Web3 Ethereum Trading...${NC}"
        python3 web3_trading_connector.py 2>&1 | tee logs/web3_$(date +%Y%m%d_%H%M%S).log
        ;;
    3)
        echo -e "${GREEN}☀️ Starting Solana Jupiter Trading...${NC}"
        python3 solana_jupiter_connector.py 2>&1 | tee logs/solana_$(date +%Y%m%d_%H%M%S).log
        ;;
    4)
        echo -e "${GREEN}⚡ Starting Flash Loan Arbitrage...${NC}"
        python3 flash_loan_arbitrage.py 2>&1 | tee logs/flashloan_$(date +%Y%m%d_%H%M%S).log
        ;;
    5)
        echo -e "${GREEN}🔄 Starting Cross-Exchange Arbitrage...${NC}"
        python3 cross_exchange_arbitrage.py 2>&1 | tee logs/cross_$(date +%Y%m%d_%H%M%S).log
        ;;
    6)
        echo -e "${GREEN}🔧 Custom configuration...${NC}"
        echo "Edit defi_orchestrator.py and run: python3 defi_orchestrator.py"
        ;;
    *)
        echo -e "${RED}Invalid selection${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Trading session complete!${NC}"
echo "Logs saved to: /root/.openclaw/workspace/agents/logs/"