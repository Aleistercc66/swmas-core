#!/bin/bash
# SWARM DESKTOP SERVER LAUNCHER
# Run this to start the desktop dashboard

cd "$(dirname "$0")"

# Install Flask if needed
pip3 install flask -q 2>/dev/null

echo "=========================================="
echo "  SWARM DESKTOP SERVER"
echo "=========================================="
echo "  Starting server on port 7777..."
echo ""
echo "  Open your browser:"
echo "  http://localhost:7777"
echo "=========================================="
echo ""

# Start server
python3 desktop_server.py
