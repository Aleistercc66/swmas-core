#!/bin/bash
# SWMAS Startup Script
# Reads .env and launches daemon with Telegram

cd "$(dirname "$0")"

# Load .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Pass through Kimi API key for LLM chat
export KIMI_API_KEY="${KIMI_API_KEY:-}"
export KIMI_BASE_URL="${KIMI_BASE_URL:-https://api.moonshot.cn/v1}"

# Use venv Python
PYTHON=./venv/bin/python

# Build allowed users list
ALLOWED=""
if [ ! -z "$ALLOWED_USERNAME" ]; then
    ALLOWED="--allowed-users $ALLOWED_USERNAME"
fi

echo "🚀 SWMAS — Starting Swarm Daemon..."
echo "   Telegram Bot: Enabled (Greek mode 🇬🇷)"
echo "   Allowed User: $ALLOWED_USERNAME"
echo "   LLM: $([ ! -z "$KIMI_API_KEY" ] && echo 'Connected ✅' || echo 'Not configured ❌')"
echo ""

exec $PYTHON main.py daemon --telegram-token "$TELEGRAM_BOT_TOKEN" $ALLOWED
