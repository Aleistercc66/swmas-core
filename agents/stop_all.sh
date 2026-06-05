#!/bin/bash
# ═══════════════════════════════════════════
# 🛑 STOP ALL — Complete System Shutdown
# ═══════════════════════════════════════════

echo "🛑 STOPPING ALL CRYPTO TRADING SYSTEMS..."
echo "================================================"

for s in v2-scanner v2-validator v2-dynamic-risk v2-fomo v2-risk v4-master v4-backtest telegram-poll meta-agent position-monitor auto-executor; do
    echo "Killing: $s"
    tmux kill-session -t $s 2>/dev/null
done

echo ""
echo "✅ ALL SYSTEMS STOPPED"
tmux list-sessions 2>/dev/null | grep -E "v2-|v4-|meta|telegram|position|auto" || echo "No trading sessions remaining"
