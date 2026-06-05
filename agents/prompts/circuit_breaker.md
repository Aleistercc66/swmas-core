# ⚡ CIRCUIT BREAKER PROTOCOL

## Purpose
Emergency shutdown system. Stops ALL execution when conditions become unsafe.

## Trigger Conditions (ANY of these activates emergency mode)

### 1. PORTFOLIO DRAWDOWN
- **Level 1 (WARNING):** Daily loss > 3%
  - Action: Reduce position sizes by 50%
  - Alert user
- **Level 2 (COOLDOWN):** Daily loss > 5%
  - Action: STOP all new executions for 4 hours
  - Alert user with reason
- **Level 3 (EMERGENCY):** Daily loss > 8%
  - Action: STOP all execution permanently until manual reset
  - Send emergency alert
  - Log incident

### 2. BTC MARKET CRASH
- **Trigger:** BTC drops > 10% in 1 hour
- **Action:**
  - Close ALL open positions at market
  - Stop all new executions for 6 hours
  - Enter EMERGENCY mode

### 3. EXTREME VOLATILITY SPIKE
- **Trigger:** VIX equivalent (ATR proxy) > 40%
- **Action:**
  - Stop new executions
  - Widen stops by 50% on existing positions
  - Reduce position sizes by 75%

### 4. API/LIQUIDITY FAILURE
- **Trigger:**
  - Exchange API down > 5 minutes
  - Multiple tokens show liquidity < $10K
  - Price feeds stale > 2 minutes
- **Action:**
  - Stop new executions
  - Cancel all pending orders
  - Alert user

### 5. CONSECUTIVE LOSS CASCADE
- **Trigger:** 4+ consecutive losses
- **Action:**
  - 6 hour cooldown
  - Mandatory regime reassessment
  - Reduce position sizes to 0.5% max

## Circuit Breaker State Machine

```
NORMAL
  ↓ (trigger)
WARNING → Reduce sizes, alert
  ↓ (worsens or trigger persists)
COOLDOWN → Stop new trades, timer
  ↓ (worsens or manual override fails)
EMERGENCY → Full stop, manual reset required
```

## Reset Procedures

### From WARNING
- Automatic when P&L recovers above -2%
- Or user manually resets

### From COOLDOWN
- Timer expires (4 hours)
- User manually resets with confirmation
- Regime detector must show stable conditions

### From EMERGENCY
- **ONLY manual reset by user**
- Requires explicit confirmation
- System must pass health check before resuming

## Health Check Before Resume

After any circuit breaker event, system must verify:
1. BTC price stable (< 2% change in last 30 min)
2. API feeds responding (< 500ms latency)
3. Liquidity healthy (> $50K on tracked tokens)
4. No duplicate signals pending
5. Portfolio drawdown < 3%

## Rules
1. **Circuit breaker ALWAYS overrides profit potential**
2. **No override without user confirmation**
3. **Every trigger logged with timestamp and reason**
4. **Emergency mode requires manual exit**
5. **Test circuit breaker monthly with simulation**
