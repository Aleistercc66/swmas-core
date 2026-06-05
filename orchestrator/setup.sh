#!/bin/bash
# Setup Script for Telegram Orchestrator Agent
# =============================================

set -e

echo "🔥 SETUP: Telegram Orchestrator Agent"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python3 found${NC}"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ pip3 found${NC}"

# Create virtual environment if not exists
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Install additional packages
echo "📥 Installing additional packages..."
pip install aiohttp requests

# Create directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p skills

# Set permissions
chmod +x run_orchestrator.sh

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "To start the orchestrator:"
echo "  source venv/bin/activate"
echo "  ./run_orchestrator.sh"
echo ""
echo "Or directly:"
echo "  python3 telegram_orchestrator.py"
echo ""
echo "🔥 Ready to move!"
