# Heartbeat Instructions
## Every Heartbeat Run (every 60 minutes)
### Market Scan Check
1. Check if it's time for DexScreener scan (every 30 min ideally)
2. If scan needed:
   - Use exec to run curl commands to DexScreener API
   - Get latest boosted tokens and hot pairs
   - Analyze for momentum (24h/6h/1h/5m), volume vs liquidity, buy/sell pressure
   - Identify opportunities with 50%+ profit potential
   - Send Telegram alert to user 158923136 with entry, stop, TP1/TP2/TP3
   - Only alert on confidence >60/100
3. Log scan results to memory

### Conditions for Alerts
- Price momentum positive across multiple timeframes
- Volume > 2x liquidity (hot activity)
- Buy pressure > Sell pressure (1.5x ratio)
- 24h change > 10% with stable 1h/5m

### Risk Management
- Never alert on coins with < $20K liquidity
- Stop loss always at -20% from entry
- Take profits: 50% / 100% / 200%
- Confidence score must be > 60/100