#!/bin/bash
# 🐕 WATCHDOG — Agent Process Monitor & Auto-Restart
# Runs continuously, checks every 60 seconds if agents are alive

echo "🐕 WATCHDOG STARTED — Monitoring agent health..."
echo "================================================"

AGENTS=(
    "v2_scanner"
    "v2_sentiment"
    "v2_whale"
    "v2_regime_detector"
    "v2_dna_classifier"
    "v2_fomo_filter"
    "v2_validator"
    "v2_dynamic_risk"
    "v4_master_controller"
    "v4_portfolio_tracker"
    "v4_realistic_backtest"
    "v4_circuit_breaker"
    "v4_duplicate_protection"
    "v4_trade_expiration"
    "v4_execution_quality"
    "v4_system_scorecard"
)

# Skip position_sizing (Agent 14 — disconnected, not used)
# Skip jupiter_executor (Agent 11 — deprecated)

while true; do
    for agent in "${AGENTS[@]}"; do
        if ! pgrep -f "${agent}.py" > /dev/null 2>&1; then
            echo "[$(date '+%H:%M:%S')] ⚠️  $agent.py DEAD — restarting..."
            
            # Map agent to tmux session name
            session=""
            case "$agent" in
                v2_scanner) session="v2-scanner" ;;
                v2_sentiment) session="v2-sentiment" ;;
                v2_whale) session="v2-whale" ;;
                v2_regime_detector) session="v2-regime" ;;
                v2_dna_classifier) session="v2-dna" ;;
                v2_fomo_filter) session="v2-fomo" ;;
                v2_validator) session="v2-validator" ;;
                v2_dynamic_risk) session="v2-risk" ;;
                v4_master_controller) session="v4-master" ;;
                v4_portfolio_tracker) session="v4-portfolio" ;;
                v4_realistic_backtest) session="v4-backtest" ;;
                v4_circuit_breaker) session="v4-circuit" ;;
                v4_duplicate_protection) session="v4-dup" ;;
                v4_trade_expiration) session="v4-expiry" ;;
                v4_execution_quality) session="v4-quality" ;;
                v4_system_scorecard) session="v4-score" ;;
            esac
            
            if [ -n "$session" ]; then
                # Kill stale tmux session if exists
                tmux kill-session -t "$session" 2>/dev/null
                # Restart agent in tmux
                tmux new-session -d -s "$session" "cd /root/.openclaw/workspace/agents && python3 ${agent}.py >> logs/${agent}.log 2>&1"
                echo "[$(date '+%H:%M:%S')] ✅ $agent.py restarted in tmux session $session"
            fi
        fi
    done
    
    # Also check if the main backtest agent is writing to the file (heartbeat check)
    if [ -f "/root/.openclaw/workspace/agents/tmp_state/last_backtest_heartbeat" ]; then
        last_beat=$(cat /root/.openclaw/workspace/agents/tmp_state/last_backtest_heartbeat)
        now=$(date +%s)
        diff=$((now - last_beat))
        if [ "$diff" -gt 600 ]; then  # No heartbeat for 10 minutes
            echo "[$(date '+%H:%M:%S')] 🚨 BACKTEST AGENT STALE — no heartbeat for ${diff}s"
        fi
    fi
    
    sleep 60
done
