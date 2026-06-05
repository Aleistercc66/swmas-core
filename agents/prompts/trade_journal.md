# 🔒 TRADE JOURNAL PROTOCOL

## Purpose
Every trade must be documented with full context for continuous learning.

## Required Fields per Trade

### Identity
- trade_id (unique)
- timestamp_opened
- timestamp_closed
- symbol
- direction (LONG/SHORT)

### Setup Context
- setup_dna (BREAKOUT/ACCUMULATION/etc)
- confidence_at_entry (0-100)
- regime_at_entry (TRENDING_BULLISH/RANGING/etc)

### Market State at Entry
- btc_price
- btc_change_24h
- market_regime
- volatility_proxy (ATR)
- liquidity_level
- volume_24h
- sentiment_score
- whale_signal

### Execution Details
- planned_entry
- actual_entry
- entry_deviation_pct
- planned_stop
- actual_stop
- stop_distance_pct
- planned_tp1
- planned_tp2
- planned_tp3
- actual_exit
- exit_reason (TP1/TP2/TP3/STOP/MANUAL)
- execution_quality_score (0-100)
- slippage_pct
- latency_ms

### Position Management
- position_size_usd
- risk_pct_of_portfolio
- actual_risk_reward
- portfolio_exposure_at_entry

### Outcome
- pnl_usd
- pnl_pct
- outcome (WIN/LOSS/BREAKEVEN)
- holding_time_minutes
- max_drawdown_during_trade
- max_profit_during_trade

### Post-Trade Analysis
- what_worked
- what_failed
- lessons_learned
- would_take_again (YES/NO/MODIFIED)

## Journal Rules
1. **Log EVERY trade** — No exceptions
2. **Be honest** — Losing trades are learning data
3. **Context matters** — Market state is as important as setup
4. **Review weekly** — Identify patterns
5. **Update DNA performance** — Track per-setup-type win rates

## Learning Loop
```
Trade Executed
    ↓
Journal Entry (full context)
    ↓
Outcome Determined
    ↓
Performance Update (DNA, Regime)
    ↓
System Adjustment (if needed)
    ↓
Next Trade (improved)
```
