#!/bin/bash
# Solana Agent Wrapper - Loads env and runs auto_runner
DIR="/root/.openclaw/workspace/solana_agent"
cd "$DIR"

# Load .env properly
set -a
source "$DIR/.env"
set +a

export PYTHONPATH="$DIR:$PYTHONPATH"
exec /usr/bin/python3 "$DIR/auto_runner.py"
