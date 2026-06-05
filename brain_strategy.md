# 🧠 BRAIN STRATEGY — DexScreener Altcoin Hunter

## Εγώ είμαι ο εγκέφαλος. Τα scripts είναι απλά χέρια.

### Τι κάνω ΕΓΩ:
1. **Analysis** — διαβάζω market data με τα tools μου
2. **Decisions** — αποφασίζω ποια coins είναι worth it
3. **Strategy** — προσαρμόζω τη στρατηγική based on market conditions
4. **Alerts** — στέλνω Telegram alerts μέσω message tool

### Τι κάνουν τα scripts:
1. **Data collection** — μαζεύουν raw data από DexScreener API
2. **Basic filtering** — αφαιρούν trash (liquidity < $20K, volume < $5K)
3. **Alert delivery** — στέλνουν formatted messages στο Telegram

### 7-Dimension Analysis Framework (ΕΓΩ το εφαρμόζω):
1. **Momentum** — 24h/6h/1h/5m price action
2. **Volume** — vs liquidity (hot = 2x+)
3. **Buy Pressure** — buyers vs sellers ratio
4. **Market Cap** — small cap = more upside
5. **Breakout** — ATH ή resistance break
6. **Social** — Telegram groups sentiment
7. **Risk/Reward** — entry vs target ratio

### Entry Criteria (Confidence > 60/100):
- 24h change > 10% with positive momentum
- Volume > 1x liquidity
- Buy ratio > 1.2x
- Liquidity > $50K

### Exit Strategy:
- Stop Loss: -20% from entry
- TP1: +50% (take 33%)
- TP2: +100% (take 33%)
- TP3: +200% (take rest)

### Risk Management:
- NEVER alert on < $20K liquidity
- Max 3 opportunities per scan
- Avoid already pumped +20% in 1h (too late)
