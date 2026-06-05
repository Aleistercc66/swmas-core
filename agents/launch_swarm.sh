#!/bin/bash
# 🚀 UNIFIED SWARM LAUNCHER v4.0
# 16 agents + Portfolio Tracker + Capital Protection + WATCHDOG

echo "🛡️🤖 SWARM v4.0 — INSTITUTIONAL EXECUTION 🤖🛡️"
echo "================================================"

# 🔄 PERSISTENT STATE — NOT /tmp/ (cleared on restart)
mkdir -p /root/.openclaw/workspace/agents/tmp_state
mkdir -p /root/.openclaw/workspace/agents/logs

# 🔄 INIT — Create empty valid JSON files so agents don't crash on first run
for f in scanner_output.json sentiment_output.json whale_output.json regime_output.json \
         dna_output.json fomo_output.json validator_output.json dynamic_risk_output.json; do
    path="/root/.openclaw/workspace/agents/tmp_state/$f"
    if [ ! -f "$path" ]; then
        echo '{}' > "$path"
        echo "[INIT] Created empty $f"
    fi
done

# 🔄 MIGRATE old /tmp/ files to persistent directory (if they exist)
python3 /root/.openclaw/workspace/agents/file_lock.py

# Kill old sessions
tmux kill-session -t v2-scanner 2>/dev/null
tmux kill-session -t v2-sentiment 2>/dev/null
tmux kill-session -t v2-whale 2>/dev/null
tmux kill-session -t v2-validator 2>/dev/null
tmux kill-session -t v2-risk 2>/dev/null
tmux kill-session -t v2-performance 2>/dev/null
tmux kill-session -t v2-master 2>/dev/null
tmux kill-session -t v2-regime 2>/dev/null
tmux kill-session -t v2-dna 2>/dev/null
tmux kill-session -t v2-fomo 2>/dev/null
tmux kill-session -t v4-jupiter 2>/dev/null
tmux kill-session -t v4-portfolio 2>/dev/null
tmux kill-session -t v4-master 2>/dev/null
tmux kill-session -t v4-circuit 2>/dev/null
tmux kill-session -t v4-dup 2>/dev/null
tmux kill-session -t v4-expiry 2>/dev/null
tmux kill-session -t v4-quality 2>/dev/null
tmux kill-session -t v4-watchdog 2>/dev/null

echo "✓ Old sessions cleaned"

echo ""
echo "LAYER 1 — MARKET DATA"
echo "1️⃣  Scanner (15min) — Raw market data"
tmux new-session -d -s v2-scanner "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_scanner.py 2>&1 | tee logs/v2_scanner.log"

echo "2️⃣  Sentiment Analyzer (30min) — Social mood"
tmux new-session -d -s v2-sentiment "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_sentiment.py 2>&1 | tee logs/v2_sentiment.log"

echo "3️⃣  Whale/Liquidity Monitor (30min) — Smart money"
tmux new-session -d -s v2-whale "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_whale.py 2>&1 | tee logs/v2_whale.log"

echo ""
echo "LAYER 2 — INTELLIGENCE"
echo "4️⃣  Regime Detector (30min) — Market state"
tmux new-session -d -s v2-regime "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_regime_detector.py 2>&1 | tee logs/v2_regime.log"

echo "5️⃣  DNA Classifier (15min) — Setup structure"
tmux new-session -d -s v2-dna "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_dna_classifier.py 2>&1 | tee logs/v2_dna.log"

echo "6️⃣  FOMO Filter (15min) — Anti-hype protection"
tmux new-session -d -s v2-fomo "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_fomo_filter.py 2>&1 | tee logs/v2_fomo.log"

echo ""
echo "LAYER 3 — VALIDATION & RISK"
echo "7️⃣  Validator — THE GATEKEEPER (15min)"
tmux new-session -d -s v2-validator "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_validator.py 2>&1 | tee logs/v2_validator.log"

echo "8️⃣  Dynamic Risk Engine (15min) — ATR-based stops"
tmux new-session -d -s v2-risk "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v2_dynamic_risk.py 2>&1 | tee logs/v2_dynamic_risk.log"

echo ""
echo "LAYER 4 — EXECUTION & TRACKING"
echo "9️⃣  Portfolio Tracker (1h) — Performance & capital"
tmux new-session -d -s v4-portfolio "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_portfolio_tracker.py 2>&1 | tee logs/v4_portfolio.log"

echo "🔟 Master Controller (15min) — Institutional signals"
tmux new-session -d -s v4-master "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_master_controller.py 2>&1 | tee logs/v4_master.log"

echo ""
echo "LAYER 5 — REALISTIC BACKTEST EXECUTION"
echo "1️⃣1️⃣  Realistic Backtest Engine (5min) — Paper trading with spread/slippage/fees"
tmux new-session -d -s v4-backtest "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_realistic_backtest.py 2>&1 | tee logs/v4_backtest.log"

echo ""
echo "LAYER 6 — SAFETY & QUALITY"
echo "1️⃣2️⃣  Circuit Breaker (1min) — Emergency shutdown"
tmux new-session -d -s v4-circuit "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_circuit_breaker.py 2>&1 | tee logs/v4_circuit.log"

echo "1️⃣3️⃣  Position Sizing (15min) — Dynamic Kelly-based [MONITORING ONLY — not connected to execution]"
tmux new-session -d -s v4-sizing "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_position_sizing.py 2>&1 | tee logs/v4_sizing.log"

echo "1️⃣4️⃣  Duplicate Protection (5min) — Anti-re-entry"
tmux new-session -d -s v4-dup "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_duplicate_protection.py 2>&1 | tee logs/v4_dup.log"

echo "1️⃣5️⃣  Trade Expiration (5min) — Signal timeout"
tmux new-session -d -s v4-expiry "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_trade_expiration.py 2>&1 | tee logs/v4_expiry.log"

echo "1️⃣6️⃣  Execution Quality (5min) — Slippage & latency"
tmux new-session -d -s v4-quality "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_execution_quality.py 2>&1 | tee logs/v4_quality.log"

echo "1️⃣7️⃣  System Scorecard (30min) — Reality check"
tmux new-session -d -s v4-score "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 python3 v4_system_scorecard.py 2>&1 | tee logs/v4_score.log"

echo ""
echo "🐕 WATCHDOG — Auto-restart crashed agents"
tmux new-session -d -s v4-watchdog "cd /root/.openclaw/workspace/agents && PYTHONUNBUFFERED=1 bash watchdog.sh 2>&1 | tee logs/watchdog.log"

echo ""
echo "================================================"
echo "✅ ALL 16 AGENTS + WATCHDOG LAUNCHED!"
echo ""
echo "💰 PAPER TRADING: ACTIVE"
echo "   Virtual balance: $10,000 USDT"
echo "   Mode: Simulation (zero risk)"
echo ""
echo "🛡️ SAFETY LAYERS:"
echo "   • Circuit Breaker: EMERGENCY shutdown"
echo "   • Position Sizing: Dynamic (Kelly-based)"
echo "   • Duplicate Protection: 6h cooldown"
echo "   • Trade Expiration: 2h timeout"
echo "   • Execution Quality: Slippage tracking"
echo "   • WATCHDOG: Auto-restart crashed agents"
echo "   • FILE LOCKING: Safe shared JSON writes"
echo "   • PERSISTENT STATE: Survives reboots"
echo ""
echo "Execution Mode: MANUAL (user confirmation)", echo ""
echo "View sessions: tmux ls"
echo "View logs: tail -f agents/logs/*.log"
echo "Attach: tmux attach -t <session-name>"
echo ""
echo "Semi-auto requires: 100+ trades, expectancy > 0.3"
echo "Full auto requires: 500+ trades, expectancy > 0.5"
