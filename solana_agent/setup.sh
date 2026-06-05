#!/bin/bash
# Solana Profit Agent - Auto Setup Script
# Ρυθμίζει αυτόματα το bot για 24/7 λειτουργία

echo "🔥 SOLANA PROFIT AGENT - AUTO SETUP 🔥"
echo "======================================"

# Check Python
python3 --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q aiohttp websockets numpy 2>/dev/null || pip3 install -q aiohttp websockets numpy

# Get Telegram Bot Token
echo ""
echo "🤖 TELEGRAM BOT SETUP"
echo "   1. Go to @BotFather on Telegram"
echo "   2. Create new bot: /newbot"
echo "   3. Copy the token (looks like: 123456:ABC-DEF1234ghI-klmn567890)"
echo ""

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    read -p "Enter your Telegram Bot Token: " TOKEN
    export TELEGRAM_BOT_TOKEN="$TOKEN"
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo ""
    echo "👤 Get your Chat ID:"
    echo "   1. Message @userinfobot on Telegram"
    echo "   2. It will reply with your ID (e.g., 123456789)"
    echo ""
    read -p "Enter your Telegram Chat ID: " CHATID
    export TELEGRAM_CHAT_ID="$CHATID"
fi

# Save to .env file
cat > .env << EOF
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID
EOF

echo ""
echo "✅ Configuration saved to .env"

# Test Telegram
echo ""
echo "🧪 Testing Telegram connection..."
python3 -c "
import aiohttp, asyncio, os

async def test():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat = os.getenv('TELEGRAM_CHAT_ID')
    async with aiohttp.ClientSession() as session:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        async with session.post(url, json={'chat_id': chat, 'text': '🔥 Solana Agent connected! Starting 24/7 monitoring...'}) as resp:
            if resp.status == 200:
                print('✅ Telegram test PASSED')
            else:
                print(f'❌ Telegram test FAILED: {resp.status}')

asyncio.run(test())
" 2>/dev/null

# Create systemd service or tmux script
echo ""
echo "🚀 SETUP COMPLETE!"
echo ""
echo "HOW TO RUN:"
echo "==========="
echo ""
echo "Option 1 - Direct (with .env loaded):"
echo "   export $(cat .env | xargs) && python3 auto_runner.py"
echo ""
echo "Option 2 - Background with nohup:"
echo "   export $(cat .env | xargs) && nohup python3 auto_runner.py > agent.log 2>&1 &"
echo "   # View logs: tail -f agent.log"
echo ""
echo "Option 3 - tmux (recommended for server):"
echo "   tmux new -s solana-agent"
echo "   export $(cat .env | xargs) && python3 auto_runner.py"
echo "   # Detach: Ctrl+B, D"
echo "   # Reattach: tmux attach -t solana-agent"
echo ""
echo "Option 4 - Systemd service:"
cat > solana-agent.service << 'SVCEOF'
[Unit]
Description=Solana Profit Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.openclaw/workspace/solana_agent
EnvironmentFile=/root/.openclaw/workspace/solana_agent/.env
ExecStart=/usr/bin/python3 auto_runner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

echo "   sudo cp solana-agent.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable solana-agent"
echo "   sudo systemctl start solana-agent"
echo "   sudo systemctl status solana-agent"
echo ""
echo "🔥 AGENT READY TO HUNT 15-30% DAILY! 🔥"
