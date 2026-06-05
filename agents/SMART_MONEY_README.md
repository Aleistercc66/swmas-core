# 🎯 SMART MONEY TRACKER AGENT

**Εντοπίζει, αναλύει και παρακολουθεί τους πιο κερδοφόρους wallets στο Solana blockchain.**

---

## 🧠 ΤΙ ΚΑΝΕΙ

### Phase 1: DISCOVERY 🔍
- **Ανακαλύπτει** κερδοφόρα wallets από:
  - Hot pairs στο DexScreener
  - Token graduations (pump.fun bonding curve winners)
  - Manual lists από community
  
### Phase 2: ANALYSIS 📊
- **Αναλύει** κάθε wallet βαθιά:
  - Win rate (ποσοστό κερδοφόρων trades)
  - Total PnL (σε SOL)
  - Risk management (drawdown, position sizing)
  - Consistency (trades per day)
  - Entry/exit timing

### Phase 3: SCORING ⭐
- **Βαθμολογεί** κάθε wallet 0-100:
  - **S-Tier (85+):** 🏆 Legendary traders
  - **A-Tier (70-84):** 🥇 Elite performers
  - **B-Tier (55-69):** 🥈 Profitable but inconsistent
  - **C-Tier (40-54):** 🥉 Promising
  - **D-Tier (<40):** 📊 Needs more data

### Phase 4: TRACKING 👁️
- **Παρακολουθεί** real-time τα κινήματα των wallets
- **Instant alerts** στο Telegram για κάθε:
  - BUY (αγορά)
  - SELL (πώληση)
  - ADD_LIQUIDITY
  - REMOVE_LIQUIDITY

---

## 🚀 ΕΓΚΑΤΑΣΤΑΣΗ

### 1. Requirements
```bash
pip install python-telegram-bot aiohttp requests
```

### 2. API Keys (πρόσθεσε στο `.env`)
```
HELIUS_API_KEY=your_key_here
BIRDEYE_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac
TELEGRAM_CHAT_ID=158923136
```

### 3. Run
```bash
cd /root/.openclaw/workspace/agents
chmod +x run_smart_money.sh
./run_smart_money.sh start
```

---

## 📱 TELEGRAM COMMANDS

| Command | Description | Example |
|---------|-------------|---------|
| `/discover` | Ανακάλυψη smart money wallets | `/discover` ή `/discover dexscreener` |
| `/track` | Ξεκίνα tracking ενός wallet | `/track 7nY7H...` |
| `/untrack` | Σταμάτα tracking | `/untrack 7nY7H...` |
| `/list` | Λίστα wallets | `/list` ή `/list S` ή `/list tracked` |
| `/top` | Top wallets | `/top` ή `/top 20` |
| `/analyze` | Βαθιά ανάλυση | `/analyze 7nY7H...` |
| `/stats` | Stats του agent | `/stats` |
| `/follow` | Alias για track | `/follow 7nY7H...` |

---

## 📡 ΠΩΣ ΔΟΥΛΕΥΕΙ ΤΟ TRACKING

### Ρυθμός Polling
- **Με signals:** Κάθε 5 δευτερόλεπτα
- **Χωρίς signals:** Κάθε 10-15 δευτερόλεπτα

### Urgency Score
Κάθε alert έχει urgency score 0-100:
- **🔥🔥🔥 (80+):** S-Tier wallet + μεγάλο position
- **🔥🔥 (60-79):** A-Tier ή σημαντικό buy signal
- **🔥 (40-59):** Standard alert

### Rate Limiting
- Max 1 alert ανά wallet ανά token ανά 30 δευτερόλεπτα
- Αποφυγή spam!

---

## 🏗️ ΑΡΧΙΤΕΚΤΟΝΙΚΗ

```
smart_money_tracker.py
├── HeliusClient          # RPC calls για blockchain data
├── BirdeyeClient         # Token prices & market data
├── BlockchainAnalyzer    # Κύρια μηχανή ανάλυσης
│   ├── discover_profitable_wallets()
│   ├── start_tracking_wallet()
│   └── poll_tracked_wallets()
├── TelegramAlerter       # Telegram notifications
└── SmartMoneyAgent       # Main orchestrator

smart_money_commands.py
└── SmartMoneyCommandHandler  # Telegram command handlers
```

---

## 📊 ΠΑΡΑΔΕΙΓΜΑ ALERT

```
🔥🔥🔥 SMART MONEY ALERT 🔥🔥🔥

🏆 Wallet: 7nY7H...xYz9
⭐ Score: 92.3/100 | Tier: S

🟢 BUY
🪙 Token: $BONK
📍 Address: DezX...k1mz
💰 Amount: 15.5 SOL (2,450,000 tokens)
💵 Price: $0.00001234

📊 Context:
• Wallet PnL on this token: +45.2 SOL
• Token Liquidity: $1,250,000
• 24h Volume: $5,400,000

🔗 Tx: 5xKj...pQm2
⏰ 14:32:15 UTC
```

---

## 🔧 ΠΡΟΧΩΡΗΜΕΝΕΣ ΡΥΘΜΙΣΕΙΣ

### Auto-Discovery Schedule
- Τρέχει κάθε **6 ώρες**
- Auto-track τα **S και A tier** wallets

### State Persistence
- Αποθήκευση κάθε **5 λεπτά**
- File: `smart_money_state.json`

### Stats Reporting
- Hourly stats logging
- Διαθέσιμα μέσω `/stats`

---

## 🆘 TROUBLESHOOTING

### Δεν λαμβάνω alerts
1. Ελέγξτε αν το wallet είναι tracked: `/list tracked`
2. Ελέγξτε τα logs: `./run_smart_money.sh logs`
3. Επιβεβαιώστε API keys

### Αργά alerts
- Ελέγξτε Helius API rate limits
- Αυξήστε polling frequency (γραμμή 590 στον κώδικα)

### No wallets found
- Ελέγξτε Birdeye API key
- Δοκιμάστε `/discover graduation` αντί για `dexscreener`

---

## 🔗 INTEGRATION ΜΕ ΟRCHESTRATOR

Ο agent είναι έτοιμος για ενσωμάτωση στον @WorkSS11_bot:

```python
# Στον orchestrator:
from agents.smart_money_commands import SmartMoneyCommandHandler

# Initialize
self.smart_money = SmartMoneyCommandHandler(self.app, agent)
self.smart_money.register_with_bot(self.app)
```

---

**Built by AImind | Part of SWMAS Trading Intelligence Layer** 🧠🔥
