# 🛡️ CAPITAL PROTECTION PROTOCOL

## Purpose
Capital preservation is ALWAYS the highest priority. These rules override ALL other logic.

## Mandatory Protection Rules

### 1. MAX LOSS PER TRADE
- **Default:** 1% of portfolio per trade
- **High confidence (>80):** 2% max
- **Never exceed 3% under any circumstances**

### 2. MAX DAILY DRAWDOWN
- **Warning at:** 3% daily loss
- **Cooldown at:** 5% daily loss (no new trades for 4 hours)
- **Emergency shutdown at:** 8% daily loss (stop all activity)

### 3. MAX CORRELATED EXPOSURE
- **Same sector max:** 20% total exposure
- **Same token type max:** 15% (e.g., all memecoins)
- **Total portfolio exposure max:** 50% (keep 50% cash)

### 4. COOLDOWN PERIODS
- **After 2 consecutive losses:** 30 min cooldown
- **After 3 consecutive losses:** 2 hour cooldown
- **After 4+ consecutive losses:** 6 hour cooldown + regime reassessment

### 5. SLIPPAGE PROTECTION
- **Max acceptable slippage:** 2%
- **If slippage > 2%:** Reject execution
- **If slippage > 5%:** Flag as manipulation risk

### 6. LIQUIDITY MINIMUMS (Hard Filters)
- **Minimum liquidity:** $50,000
- **Minimum 24h volume:** $10,000
- **If liquidity < $25K:** Reject immediately
- **If volume < 2x liquidity:** Reduce position by 50%

### 7. VOLATILITY FILTERS
- **If ATR > 15%:** Reduce position to 1%
- **If ATR > 25%:** Reject (untradeable chaos)
- **If 5m candle > 8%:** Reject (chasing parabolic)

### 8. EMERGENCY SHUTDOWN
**Trigger conditions (ANY of these):**
- BTC drops > 10% in 1 hour
- Portfolio down > 8% in 24h
- 3 consecutive losses with avg R:R < 1:1
- Liquidity crisis detected (multiple tokens at < $10K)
- Exchange/API failure for > 5 minutes

**Emergency actions:**
1. Stop all new position opening
2. Send emergency alert
3. Wait for manual override to resume

## Capital Protection State Machine

```
NORMAL → WARNING (3% daily loss)
  ↓
COOLDOWN (5% daily loss) — 4hr pause
  ↓
EMERGENCY (8% daily loss) — Manual resume required
```

## Position Sizing Formula

```
Position Size = (Portfolio × Risk%) / Stop Distance

Where:
- Portfolio = Total available capital
- Risk% = 1% (default), 2% (high confidence), 3% (max emergency)
- Stop Distance = ATR × multiplier (from Dynamic Risk Engine)
```

## Daily Budget

```
Max daily trades: 5
Max daily risk: 5% of portfolio
Max daily loss before cooldown: 5%
```

## Rules
1. **Capital preservation > profit maximization** — Always
2. **No trade > Bad trade** — Always
3. **Cash is a position** — 50% minimum cash reserve
4. **When in doubt, stay out** — Always
5. **Survive first, profit second** — Always
