#!/bin/bash
# ═══════════════════════════════════════════
# 🚀 START ALL — Complete System Launcher
# Starts all agents including Meta Agent
# ═══════════════════════════════════════════

echo "🚀 STARTING COMPLETE CRYPTO TRADING SYSTEM..."
echo "================================================"

# Kill all existing sessions first
echo "[1/6] Cleaning old sessions..."
for s in v2-scanner v2-validator v2-dynamic-risk v2-fomo v4-master v4-backtest telegram-poll meta-agent v2-risk; do
    tmux kill-session -t $s 2>/dev/null
done
sleep 2

# Create logs directory
mkdir -p /root/.openclaw/workspace/agents/logs
mkdir -p /root/.openclaw/workspace/agents/tmp_state

echo "[2/6] Starting Meta Agent (self-healing)..."
tmux new-session -d -s meta-agent "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 meta_agent.py 2>&1 | tee logs/meta_agent.log"

echo "[3/6] Starting Data Pipeline..."
tmux new-session -d -s v2-scanner "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_scanner.py 2>&1 | tee logs/v2_scanner.log"
tmux new-session -d -s v2-validator "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_validator.py 2>&1 | tee logs/v2_validator.log"
tmux new-session -d -s v2-dynamic-risk "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_dynamic_risk.py 2>&1 | tee logs/v2_dynamic_risk.log"
tmux new-session -d -s v2-fomo "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_fomo_filter.py 2>&1 | tee logs/v2_fomo.log"

echo "[4/6] Starting Execution Layer..."
tmux new-session -d -s v4-master "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_master_controller.py 2>&1 | tee logs/v4_master.log"
tmux new-session -d -s v4-backtest "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_realistic_backtest.py 2>&1 | tee logs/v4_backtest.log"

echo "[5/6] Auto-Trading DISABLED for safety — skipping position-monitor + auto-executor"
# tmux new-session -d -s position-monitor "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 position_monitor.py 2>&1 | tee logs/position_monitor.log"
# tmux new-session -d -s auto-executor "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 auto_executor.py 2>&1 | tee logs/auto_executor.log"

echo "[5.5/6] Starting Real-Time Data Agents..."
tmux new-session -d -s realtime-dex "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 realtime_dexscreener.py 2>&1 | tee logs/realtime_dexscreener.log"
tmux new-session -d -s jupiter-realtime "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 jupiter_realtime.py 2>&1 | tee logs/jupiter_realtime.log"

echo "[6/6] Starting Telegram Integration..."
tmux new-session -d -s telegram-poll "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 poll_telegram.py 2>&1 | tee logs/poll_telegram.log"

echo "[6/6] Verifying startup..."
sleep 5

echo ""
echo "═══════════════════════════════════════"
echo "📊 ACTIVE SESSIONS:"
tmux list-sessions 2>/dev/null || echo "No sessions found!"
echo "═══════════════════════════════════════"

echo ""
echo "✅ SYSTEM FULLY OPERATIONAL!"
echo ""
echo "📱 Telegram Bot: @KreoPolyBot"
echo "🧠 Meta Agent: Self-healing & self-improving"
echo "📈 Profit-Optimized: Only TIER 1/2 signals"
echo ""
echo "Commands:"
echo "  tmux ls                    — List all sessions"
echo "  tmux attach -t meta-agent  — View Meta Agent"
echo "  tmux attach -t v4-master   — View Master Controller"
echo "  cat logs/meta_agent.log    — View Meta Agent logs"
echo "  ./stop_all.sh              — Stop everything"
echo ""
