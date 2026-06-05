# 🔥 SOLANA PROFIT AGENT - AUTO-RUNNER GUIDE

## Τι κάνει το Auto-Runner

Τρέχει **24/7** και:
1. **Σκανάρει** DexScreener κάθε 3 λεπτά για trending Solana tokens
2. **Αναλύει** κάθε token για 15-30% ευκαιρίες
3. **Στέλνει Telegram alerts** με exact entry price + targets + stop loss
4. **Παρακολουθεί** τις τιμές κάθε 1 λεπτό για exits
5. **Στέλνει sell alerts** όταν χτυπάνε TP1/TP2/TP3 ή stop loss
6. **Μαθαίνει** αυτόματα κάθε 6 ώρες από τα data

## 🚀 Πως να το σετάρεις (3 βήματα)

### Βήμα 1: Extract
```bash
cd solana_agent
```

### Βήμα 2: Set Telegram
```bash
export TELEGRAM_BOT_TOKEN="8585099271:AAFQI6OZD8UdJp3lnq8oSbJOOm5njF2io8Y"
export TELEGRAM_CHAT_ID="158923136"
```

### Βήμα 3: Run
```bash
python3 auto_runner.py
```

## 📱 Τι θα λαμβάνεις στο Telegram

### BUY Alert
```
🔥🔥🔥 BUY ALERT 🔥🔥🔥

🪙 Token: BONK
📍 Address: DezX...wCA
💰 Entry Price: $0.00000234

🎯 TARGETS:
   TP1 (+10.0%) | TP2 (+17.5%) | TP3 (+25.0%)
🛑 Stop Loss: -12.0%
📊 Risk/Reward: 2.1x
💎 Score: 78/100
⚡ Urgency: HIGH
📈 Strategy: early_momentum

🚀 JUPITER SWAP:
https://jup.ag/swap/SOL-DezX...wCA

⏰ Detected: 14:32:15
```

### SELL Alert (Take Profit)
```
🎯 TP3 HIT: BONK

💰 Current Price: $0.00000292
📈 PnL: +25.0%

✅ Sell 100% here
🚀 Exit complete!

💸 JUPITER SELL:
https://jup.ag/swap/DezX...wCA-SOL
```

### SELL Alert (Stop Loss)
```
🔴 SELL ALERT: BONK

🛑 STOP LOSS HIT: -12.0%

💰 Exit Price: $0.00000206
📊 PnL: -12.0%

💸 JUPITER SELL:
https://jup.ag/swap/DezX...wCA-SOL
```

## 🎯 Πως δουλεύει

| Βήμα | Τι κάνει | Πόσο συχνά |
|------|----------|-----------|
| Scan | Ψάχνει trending tokens | Κάθε 3 λεπτά |
| Analyze | Υπολογίζει opportunity score | Real-time |
| Alert | Στέλνει buy alert στο Telegram | Όταν score > 70 |
| Monitor | Παρακολουθεί τιμές | Κάθε 1 λεπτό |
| Exit | Στέλνει sell alert | Στα targets/stop |
| Train | Βελτιστοποιεί parameters | Κάθε 6 ώρες |

## 🔄 Background Running (24/7)

### Με nohup (απλό)
```bash
export TELEGRAM_BOT_TOKEN="8585099271:AAFQI6OZD8UdJp3lnq8oSbJOOm5njF2io8Y"
export TELEGRAM_CHAT_ID="158923136"
nohup python3 auto_runner.py > agent.log 2>&1 &

# Δες logs
tail -f agent.log
```

### Με tmux (προτείνεται)
```bash
# Δημιούργησε session
tmux new -s solana-agent

# Μέσα στο session
export TELEGRAM_BOT_TOKEN="8585099271:AAFQI6OZD8UdJp3lnq8oSbJOOm5njF2io8Y"
export TELEGRAM_CHAT_ID="158923136"
python3 auto_runner.py

# Αποσύνδεση: Ctrl+B, D
# Επανασύνδεση: tmux attach -t solana-agent
```

## 📊 Commands

```bash
# Έναρξη
python3 auto_runner.py

# Logs
ls -la agent.log
tail -f agent.log

# Κατάσταση
ps aux | grep auto_runner

# Διακοπή
pkill -f auto_runner.py

# State (active alerts)
cat auto_runner_state.json
```

## 🎓 Training

Τρέχει αυτόματα κάθε 6 ώρες! Για manual training:
```bash
python3 train.py --quick
```

## ⚠️ Σημαντικά

1. **Real data**: Χρησιμοποιεί DexScreener API (πραγματικές τιμές)
2. **Real prices**: Jupiter API για live prices
3. **Alerts only**: Δεν κάνει trades αυτόματα — σου λέει τι να αγοράσεις/πουλήσεις
4. **Safety first**: Κάθε token περνάει safety check πριν alert
5. **Risk management**: Max 5 positions, stop loss πάντα

## 🔥 Ready to hunt 15-30% daily!

```bash
cd solana_agent
export TELEGRAM_BOT_TOKEN="8585099271:AAFQI6OZD8UdJp3lnq8oSbJOOm5njF2io8Y"
export TELEGRAM_CHAT_ID="158923136"
python3 auto_runner.py
```
