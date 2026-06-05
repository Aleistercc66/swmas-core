#!/bin/bash
# Wallet Setup Script — Run this ONCE with your password
# Usage: ./set_wallet_password.sh

echo "🔐 Wallet Password Setup"
echo ""
echo "This will save your wallet password securely for the bot to use."
echo ""
read -s -p "Enter your wallet password: " password
echo ""

# Save password to file (restricted permissions)
mkdir -p /root/.openclaw/workspace/orchestrator/config
echo "$password" > /root/.openclaw/workspace/orchestrator/config/.wallet_password
chmod 600 /root/.openclaw/workspace/orchestrator/config/.wallet_password

echo "✅ Password saved!"
echo ""
echo "Now restart the live sniper with:"
echo "  kill \$(ps aux | grep live_sniper | grep -v grep | awk '{print \$2}')"
echo "  cd /root/.openclaw/workspace/orchestrator && nohup python3 -m core.live_sniper > logs/live_sniper.log 2>&1 &"
