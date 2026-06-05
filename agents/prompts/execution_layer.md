# ⚡ EXECUTION LAYER PROTOCOL

## Purpose
Handle trade execution with strict safety controls. Default to manual confirmation.

## Execution Modes

### 1. MANUAL CONFIRMATION (DEFAULT)
**Behavior:**
- System detects opportunity
- System sends alert to user
- User must CONFIRM within 5 minutes
- If no confirmation → trade auto-cancelled
- User can APPROVE, MODIFY, or REJECT

**Use this mode until:**
- 200+ logged trades
- Stable expectancy > 0.5
- Max drawdown < 15%
- Win rate > 45%

### 2. SEMI-AUTOMATIC MODE
**Behavior:**
- System auto-approves setups with confidence > 80 AND R:R > 1:3
- Everything else requires manual confirmation
- System tracks all executions

**Requirements to enable:**
- 100+ manual trades logged
- Expectancy > 0.3
- No major drawdown events

### 3. FULL AUTONOMOUS (FUTURE)
**Behavior:**
- System executes all approved setups
- Still subject to capital protection rules
- Emergency shutdown always available

**Requirements to enable:**
- 500+ trades logged
- Expectancy > 0.5
- Max drawdown < 10%
- Stable performance across 3+ regimes

## Execution Safety Checks

### Pre-Execution
1. **Liquidity check:** Confirm liquidity > $50K
2. **Spread check:** Confirm spread < 2%
3. **Slippage estimate:** Project slippage < 2%
4. **Contract safety:** Verify token contract (if on-chain)
5. **Balance check:** Confirm sufficient funds
6. **Exposure check:** Confirm not exceeding correlated exposure limits

### During Execution
1. **Slippage monitoring:** Abort if slippage > 3%
2. **Price movement:** Abort if price moves > 2% against position during execution
3. **Time limit:** Cancel if not filled within 2 minutes

### Post-Execution
1. **Position verification:** Confirm position size matches plan
2. **Stop placement:** Verify stop-loss is set correctly
3. **Alert sent:** Notify user of execution

## Signal Format (Standardized)

```
═══════════════════════════════════════
[SYMBOL] — [LONG]

📍 ENTRY ZONE:    $X.XXXXXXXX
🛑 STOP LOSS:     $X.XXXXXXXX (X.X%)
🎯 TAKE PROFIT 1: $X.XXXXXXXX (X.X%)
🚀 TAKE PROFIT 2: $X.XXXXXXXX (X.X%)
🌕 TAKE PROFIT 3: $X.XXXXXXXX (X.X%)

📊 RISK/REWARD:   1:X.X
🎲 CONFIDENCE:   XX/100
⚠️  RISK LEVEL:   [LOW/MEDIUM/HIGH]

💰 POSITION SIZE: X% of portfolio
🧬 SETUP DNA:     [BREAKOUT/ACCUMULATION/etc]
🌍 MARKET REGIME: [TRENDING/RANGING/etc]

🧠 REASONING:
• [Point 1]
• [Point 2]
• [Point 3]

═══════════════════════════════════════
[CONFIRM]    [MODIFY]    [REJECT]
═══════════════════════════════════════
```

## Execution Commands

### CONFIRM Trade
```
User replies: "CONFIRM [SYMBOL]"
System: Executes trade with planned parameters
```

### MODIFY Trade
```
User replies: "MODIFY [SYMBOL] entry=X stop=X size=X"
System: Recalculates R:R and confidence with new parameters
System: Requires re-confirmation if R:R < 2 or confidence < 60
```

### REJECT Trade
```
User replies: "REJECT [SYMBOL]"
System: Cancels alert, logs rejection reason
```

### EMERGENCY CLOSE ALL
```
User replies: "EMERGENCY CLOSE"
System: Closes ALL positions immediately at market
System: Sends confirmation of closure
System: Enters emergency cooldown (6 hours)
```

## Rules
1. **Manual mode is default** — Never assume consent
2. **Semi-auto requires explicit enable** — User must opt in
3. **Full auto is future-only** — Requires proven track record
4. **Emergency shutdown always available** — One command away
5. **Every execution logged** — Complete audit trail
6. **Rejected trades tracked** — Improve filtering over time
