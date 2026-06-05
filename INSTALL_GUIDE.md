# 🐺 ΟΔΗΓΟΣ ΕΓΚΑΤΑΣΤΑΣΗΣ — KreoPoly Swarm Beast Mode v2

> **Έκδοση:** 2.0 | **Ημερομηνία:** Μάιος 2026 | **Γλώσσα:** Ελληνικά + Technical Terms
> **Συγγραφέας:** AImind | **Στόχος:** 0% → 101% Πλήρης Απόδοση

---

## 📖 ΠΕΡΙΕΧΟΜΕΝΑ

1. [Τι Είναι Αυτό Το Σύστημα](#1-τι-είναι-αυτό-το-σύστημα)
2. [Τι Κάνει (Λειτουργίες)](#2-τι-κάνει-λειτουργίες)
3. [Τεχνολογίες & Μέσα](#3-τεχνολογίες--μέσα)
4. [Προαπαιτούμενα](#4-προαπαιτούμενα)
5. [Δομή Φακέλων](#5-δομή-φακέλων)
6. [Βήμα-βήμα Εγκατάσταση](#6-βήμα-βήμα-εγκατάσταση)
7. [Ρύθμιση API Keys](#7-ρύθμιση-api-keys)
8. [Εκκίνηση Συστήματος](#8-εκκίνηση-συστήματος)
9. [Dashboard UI](#9-dashboard-ui)
10. [Χειριστήρια & Controls](#10-χειριστήρια--controls)
11. [Monitoring & Logs](#11-monitoring--logs)
12. [Troubleshooting](#12-troubleshooting)
13. [Security Checklist](#13-security-checklist)
14. [Maintenance](#14-maintenance)

---

## 1. ΤΙ ΕΊΝΑΙ ΑΥΤΌ ΤΟ ΣΎΣΤΗΜΑ

### 🎯 Όνομα
**KreoPoly Swarm — Beast Mode v2**

### 🧠 Τι Είναι
Ένα **αυτόνομο σύστημα algorithmic trading** για cryptocurrency markets, ειδικευμένο σε:
- **Solana** (primary)
- **Base** (secondary)
- **Ethereum** (tertiary)

### 🐺 Philosophy
> "Μέγιστο αποτέλεσμα, ελάχιστη τριβή."
> Το σύστημα τρέχει 24/7, σκανάρει αυτόματα για ευκαιρίες, αξιολογεί risk, και εκτελεί trades χωρίς να χρειάζεται η παρουσία σου.

### 🏗️ Αρχιτεκτονική
```
┌─────────────────────────────────────────────────────┐
│                    USER (ΕΣΥ)                        │
│         Dashboard (Browser) / Telegram              │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              DASHBOARD SERVER (FastAPI)              │
│              Port 8080 — WebSocket                   │
│         └─> Real-time updates, Controls             │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│           BEAST MODE PAPER TRADING                   │
│    ├─ Multi-Chain Scanner (Solana/Base/ETH)        │
│    ├─ Composite Scoring Engine (0-100)             │
│    ├─ Dynamic Risk Manager                           │
│    ├─ Position Monitor (SL/TP trailing)            │
│    └─ Telegram Alert System                          │
└─────────────────────────────────────────────────────┘
```

---

## 2. ΤΙ ΚΆΝΕΙ (ΛΕΙΤΟΥΡΓΊΕΣ)

### 🔄 Συνεχής Λειτουργία (24/7)
1. **Scan** κάθε 2 λεπτά σε 3 blockchains
2. **Score** tokens με composite algorithm (0-100)
3. **Filter** με 6+ criteria (liquidity, volume, momentum, etc.)
4. **Signal** όταν βρίσκει ευκαιρία
5. **Risk Check** — daily budget, max positions, drawdown
6. **Execute** trade (paper ή real)
7. **Monitor** — trailing stops, take profits
8. **Alert** — Telegram με όλες τις λεπτομέρειες

### 📊 Τι Ελέγχει
| Parameter | Value | Περιγραφή |
|-----------|-------|-----------|
| Scan Interval | 120 sec | Κάθε πότε σκανάρει |
| Chains | 3 | Solana, Base, Ethereum |
| Min Score | 68 | Ελάχιστο composite score για signal |
| Min Liquidity | $65,000 | Ελάχιστη liquidity pool |
| Min Volume | $120,000 | Ελάχιστο 24h volume |
| Max Daily Trades | 6 | Ελάχιστο paper, real mode |
| Max Open Positions | 5 | Ταυτόχρονα |
| Position Size | $220-350 | Dynamic ανάλογα confidence |
| SL | -3.5% | Stop Loss |
| TP1 | +4% | Take Profit 1 |
| TP2 | +8% | Take Profit 2 |
| TP3 | +15% | Take Profit 3 |
| Daily Risk Budget | $500 | Μέγιστο ημερήσιο risk |

### 📈 Τι Σου Δίνει
- **Real-time dashboard** με WebSocket updates
- **Telegram alerts** για κάθε event
- **Portfolio tracking** (balance, PnL, win rate, drawdown)
- **Position management** (entry, SL, TP, time in trade)
- **Signal history** με scores και performance
- **Risk analytics** (budget usage, circuit breaker status)

---

## 3. ΤΕΧΝΟΛΟΓΊΕΣ & ΜΈΣΑ

### 🛠️ Τεχνολογίες
| Technology | Χρήση |
|------------|-------|
| **Python 3.11+** | Core language |
| **FastAPI** | Dashboard backend API |
| **Uvicorn** | ASGI server |
| **WebSocket** | Real-time updates |
| **AIOHTTP** | Async HTTP requests (DexScreener API) |
| **Jinja2** | HTML templating |
| **Tailwind CSS** | UI styling (CDN) |
| **ApexCharts** | Performance graphs |
| **tmux** | Background session management |
| **curl** | API testing |

### 🌐 Εξωτερικά APIs
| API | Purpose |
|-----|---------|
| **DexScreener** | Token prices, volume, liquidity, pairs |
| **Jupiter (Solana)** | DEX aggregation, swaps |
| **Telegram Bot API** | Alerts, notifications |
| **Binance API** | Real trading (optional) |
| **Bybit API** | Real trading (optional) |
| **OKX API** | Real trading (optional) |

### 💾 Αρχεία Δεδομένων
| File | Περιεχόμενο |
|------|-------------|
| `paper_trading.json` | Paper trading state (balance, positions, history) |
| `trading_log.jsonl` | Line-delimited event log |
| `config/settings.json` | System configuration |

---

## 4. ΠΡΟΑΠΑΙΤΟΎΜΕΝΑ

### 🔧 Υλικό (Hardware)
- **Server/VPS** με Linux (Ubuntu 22.04+ προτείνεται)
- **RAM:** 512MB minimum (1GB προτείνεται)
- **CPU:** 1 core αρκεί
- **Disk:** 2GB free space
- **Network:** Stable internet connection

### 🖥️ Λογισμικό (Software)
```bash
# Έλεγξε αν έχεις:
python3 --version    # Πρέπει: 3.8+
pip3 --version
tmux --version       # Πρέπει: 3.0+
curl --version
```

### 📦 Python Packages
```bash
pip3 install fastapi uvicorn aiohttp websockets jinja2 python-telegram-bot
```

### 🔑 Απαραίτητα Accounts
1. **Telegram Bot** — μέσω @BotFather
2. **DexScreener** — δεν χρειάζεται account (public API)
3. **Exchange APIs** (προαιρετικά για real trading):
   - Binance (API Key + Secret)
   - Bybit (API Key + Secret)
   - OKX (API Key + Secret + Passphrase)

---

## 5. ΔΟΜΉ ΦΑΚΈΛΩΝ

```
/root/.openclaw/workspace/
├── agents/
│   ├── dashboard/
│   │   ├── main.py              ← FastAPI backend
│   │   ├── models.py            ← Data models
│   │   ├── templates/
│   │   │   └── index.html       ← Dashboard UI
│   │   ├── static/
│   │   │   └── js/
│   │   │       └── dashboard.js ← Frontend logic
│   │   └── routers/             ← API routes
│   ├── .env                     ← API KEYS (ΜΗΝ ΤΟ ΚΟΙΝΟΠΟΙΗΣΕΙΣ)
│   ├── logs/
│   │   ├── paper_trading.json   ← Paper state
│   │   └── trading_log.jsonl    ← Event log
│   └── config/
│       └── settings.json        ← System config
├── solana_agent/                ← Solana-specific modules
└── downloads/                   ← Attachments, specs

/tmp/
├── beast_mode_paper.py          ← Main paper trading script
├── realtime_paper_loop.py       ← Alternative paper loop
└── start_paper_loop.sh          ← Helper script
```

---

## 6. ΒΉΜΑ-ΒΉΜΑ ΕΓΚΑΤΆΣΤΑΣΗ

### 🎯 STEP 0: Επιβεβαίωση Περιβάλλοντος

```bash
# SSH στον server σου
ssh user@your-server-ip

# Έλεγξε Python
python3 --version

# Έλεγξε αν υπάρχει ο φάκελος
ls -la /root/.openclaw/workspace/agents/
ls -la /tmp/beast_mode_paper.py
```

**Αν δεν υπάρχουν τα αρχεία, επικοινώνησε μαζί μου!**

---

### 🎯 STEP 1: Εγκατάσταση Εξαρτήσεων

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Εγκατάσταση βασικών εργαλείων
sudo apt install -y tmux curl git nano wget

# Εγκατάσταση Python packages
pip3 install --upgrade pip
pip3 install fastapi uvicorn aiohttp websockets jinja2 python-telegram-bot
```

**Επιβεβαίωση:**
```bash
python3 -c "import fastapi; print('FastAPI OK')"
python3 -c "import aiohttp; print('AIOHTTP OK')"
python3 -c "import websockets; print('WebSockets OK')"
```

---

### 🎯 STEP 2: Ρύθμιση API Keys

```bash
# Φτιάξε το .env αρχείο
nano /root/.openclaw/workspace/agents/.env
```

**Γράψε μέσα (αντικατέστησε τα YOUR_* με πραγματικά values):**

```env
# ═══════════════════════════════════════════════
# 🔴 REAL TRADING API KEYS — ΠΡΟΣΟΧΗ!
# ═══════════════════════════════════════════════

# Binance
BINANCE_API_KEY=YOUR_BINANCE_API_KEY
BINANCE_API_SECRET=YOUR_BINANCE_API_SECRET

# Bybit
BYBIT_API_KEY=YOUR_BYBIT_API_KEY
BYBIT_API_SECRET=YOUR_BYBIT_API_SECRET

# OKX
OKX_API_KEY=YOUR_OKX_API_KEY
OKX_API_SECRET=YOUR_OKX_API_SECRET
OKX_PASSPHRASE=YOUR_OKX_PASSPHRASE

# ═══════════════════════════════════════════════
# 🟡 TELEGRAM BOT — ΓΙΑ ALERTS
# ═══════════════════════════════════════════════
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
TELEGRAM_CHAT_ID=YOUR_CHAT_ID

# ═══════════════════════════════════════════════
# 🟢 SYSTEM CONFIGURATION
# ═══════════════════════════════════════════════
PAPER_MODE=true              # true = paper, false = real
AUTO_MODE=false              # false = manual approval
RISK_LEVEL=aggressive        # conservative / moderate / aggressive
MAX_POSITION_SIZE=350        # USD
MAX_DAILY_TRADES=6           # Hard limit
DAILY_RISK_BUDGET=500        # USD
MIN_LIQUIDITY=65000          # USD
MIN_VOLUME=120000            # USD
MIN_SCORE=68                 # Composite 0-100

# ═══════════════════════════════════════════════
# 🔵 CHAIN CONFIGURATION
# ═══════════════════════════════════════════════
SOLANA_ENABLED=true
BASE_ENABLED=true
ETH_ENABLED=false            # Άλλαξε σε true αν θες

# ═══════════════════════════════════════════════
# 🟣 DASHBOARD
# ═══════════════════════════════════════════════
DASHBOARD_PORT=8080
DASHBOARD_HOST=0.0.0.0
```

**Αποθήκευση στο nano:** `Ctrl+O` → `Enter` → `Ctrl+X`

---

### 🎯 STEP 3: Ρύθμιση Telegram Bot

Αν δεν έχεις bot ακόμα:

```bash
# 1. Άνοιξε Telegram
# 2. Βρες τον @BotFather
# 3. Στείλε: /newbot
# 4. Δώσε όνομα (π.χ. "KreoPolyAlerts")
# 5. Δώσε username (π.χ. "kreopoly_alerts_bot")
# 6. Πάρε το TOKEN (μοιάζει με: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
# 7. Βάλτο στο .env ως TELEGRAM_BOT_TOKEN
```

**Βρες το Chat ID:**
```bash
# Στείλε ένα μήνυμα στο bot σου
# Μετά τρέξε:
curl -s "https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates" | \
python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result'][-1]['message']['chat']['id'])"
```

---

### 🎯 STEP 4: Εκκίνηση Dashboard Server

```bash
# Μπες στον φάκελο
cd /root/.openclaw/workspace/agents

# Εκκίνηση με tmux (ΠΡΟΤΕΙΝΕΤΑΙ)
tmux new-session -d -s dashboard "python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080"

# Επιβεβαίωση
tmux ls
# Πρέπει να δεις: dashboard: 1 windows
```

**Επιβεβαίωση ότι τρέχει:**
```bash
# Test API
curl -s http://127.0.0.1:8080/api/state | python3 -m json.tool

# Expected output:
# {
#   "portfolio": { "balance": 10000.0, ... },
#   "open_positions": [],
#   "active_signals": [],
#   ...
# }
```

---

### 🎯 STEP 5: Εκκίνηση Paper Trading Engine

```bash
# Εκκίνηση Beast Mode με tmux
tmux new-session -d -s beast "python3 /tmp/beast_mode_paper.py"

# Επιβεβαίωση
tmux ls
# Πρέπει να δεις:
# beast: 1 windows
# dashboard: 1 windows
```

**Επιβεβαίωση ότι σκανάρει:**
```bash
# Δες τα logs
tmux capture-pane -t beast -p | tail -15

# Πρέπει να δεις κάτι σαν:
# [HH:MM:SS] 🔥 REAL-TIME PAPER SCAN 🔥
# [HH:MM:SS] 📊 Total pairs: 30
# [HH:MM:SS] 💼 Balance: $10,000 | Realized PnL: $+0.00
```

---

### 🎯 STEP 6: Πρόσβαση στο Dashboard

#### Τρόπος A — Τοπικά στον Server
```bash
# Αν έχεις GUI (desktop):
firefox http://localhost:8080
# ή
chromium http://localhost:8080
```

#### Τρόπος B — SSH Tunnel (Από απόσταση)
```bash
# Από το τοπικό σου PC (όχι στο server):
ssh -L 8080:localhost:8080 user@your-server-ip

# Μετά άνοιξε στο browser σου:
# http://localhost:8080
```

#### Τρόπος C — Public Access (αν έχεις public IP)
```bash
# Το dashboard είναι ήδη στο 0.0.0.0:8080
# Άνοιξε: http://YOUR-SERVER-IP:8080

# Αν θες domain + HTTPS (Nginx + Let's Encrypt):
# Μου λες "στήσε μου Nginx" και το κάνω!
```

---

## 7. ΡΎΘΜΙΣΗ API KEYS

### 🔴 Binance
1. Πήγαινε: https://www.binance.com/en/my/settings/api-management
2. Δημιούργησε New API Key
3. Ενεργοποίησε: **Enable Reading**, **Enable Spot & Margin Trading**
4. **ΜΗΝ** επιτρέψεις Withdrawal
5. Αντιγράψε API Key και Secret
6. Βάλτα στο `.env`

### 🔴 Bybit
1. Πήγαινε: https://www.bybit.com/app/user/api-management
2. Δημιούργησε New Key
3. Δικαιώματα: **Read**, **Trade**
4. **ΜΗΝ** επιτρέψεις Withdraw
5. Βάλε keys στο `.env`

### 🔴 OKX
1. Πήγαινε: https://www.okx.com/account/my-api
2. Create API Key
3. Permissions: **Read**, **Trade**
4. Θυμήσου το **Passphrase**
5. Βάλε όλα στο `.env`

### 🟡 Telegram Bot
1. Άνοιξε Telegram
2. Βρες @BotFather
3. `/newbot` → όνομα → username
4. Πάρε το token
5. Στείλε μήνυμα στο bot για να πάρεις chat ID

---

## 8. ΕΚΚΊΝΗΣΗ ΣΥΣΤΉΜΑΤΟΣ

### 🚀 One-Command Startup
```bash
#!/bin/bash
# Αποθήκευσε ως: /root/start_all.sh

# Kill existing
tmux kill-session -t beast 2>/dev/null
tmux kill-session -t dashboard 2>/dev/null

# Start Dashboard
tmux new-session -d -s dashboard \
    "cd /root/.openclaw/workspace/agents && \
     python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080"

# Start Paper Trading
tmux new-session -d -s beast \
    "python3 /tmp/beast_mode_paper.py"

echo "🐺 KreoPoly Swarm started!"
echo "Dashboard: http://localhost:8080"
echo ""
echo "Commands:"
echo "  tmux attach -t beast      # Paper trading logs"
echo "  tmux attach -t dashboard  # Dashboard logs"
echo "  tmux ls                   # List sessions"
```

```bash
# Κάνε το executable
chmod +x /root/start_all.sh

# Τρέξε το
/root/start_all.sh
```

### 🔄 Restart Μετά από Reboot
```bash
# Πρόσθεσε στο crontab:
crontab -e

# Πρόσθεσε αυτή τη γραμμή:
@reboot /root/start_all.sh
```

---

## 9. DASHBOARD UI

### 🖥️ Τι Βλέπεις στο Browser

#### Header
- **🐺 KreoPoly Swarm** — Logo + version
- **📊 Market Regime** — BULL / BEAR / CHOP / HIGH_VOL
- **🟢/🔴 WS Status** — Online/Offline
- **📊/💰 Mode** — Paper ή Real
- **🤖 Auto/Manual** — Τρόπος λειτουργίας
- **🛑 Emergency Stop** — Κόκκινο κουμπί

#### Section 1: Portfolio Overview
| Metric | Τι Είναι |
|--------|----------|
| Balance | Τρέχον balance |
| Daily PnL | Κέρδος/Ζημιά σήμερα |
| Total PnL | Συνολικό κέρδος/ζημιά |
| Win Rate | % επιτυχημένων trades |
| Max Drawdown | Μέγιστο drawdown |
| Risk Used | Πόσο risk έχεις χρησιμοποιήσει |

#### Section 2: Multi-Chain Overview
- **⚡ Solana** — Pairs, Signals, Volume
- **🔵 Base** — Pairs, Signals, Volume
- **💎 Ethereum** — Pairs, Signals, Volume

#### Section 3: Live Positions
- Symbol, Entry Price, Current Price, PnL %, PnL $, Time, SL/TP

#### Section 4: Active Signals
- Chain, Symbol, Composite Score (0-100), TP1, SL

#### Section 5: Agent Health
- 7 agents με status (healthy/warning/down) και fitness score

#### Section 6: Performance Analytics
- Chart με PnL over time (1h / 24h / 7d)

#### Section 7: Signal Quality Heatmap
- Ποιες κατηγορίες tokens έχουν καλύτερο performance

#### Section 8: Whale Activity
- Μεγάλες αγορές/πωλήσεις (αν tracking ενεργοποιηθεί)

#### Section 9: Event Log
- Χρονολογημένο log όλων των events

#### Section 10: Manual Controls
- 8 κουμπιά για manual control

---

## 10. ΧΕΙΡΙΣΤΉΡΙΑ & CONTROLS

### 🎛️ Dashboard Buttons

| Button | Τι Κάνει | Πότε Χρησιμοποιείται |
|--------|----------|----------------------|
| **✅ Confirm Trade** | Εγκρίνει το επόμενο signal | Manual mode |
| **🔄 Toggle Auto** | Αλλάζει Auto ↔ Manual | Όταν θες hands-off |
| **📊 Toggle Paper** | Αλλάζει Paper ↔ Real | Όταν είσαι έτοιμος για real |
| **⏸️ Pause** | Παύει scanning | Break time |
| **▶️ Resume** | Συνεχίζει scanning | Μετά το pause |
| **🔒 Close All** | Κλείνει όλες τις positions | Panic mode |
| **🔄 Reset** | Μηδενίζει stats | New day |
| **🛑 Emergency Stop** | Σταματάει ΤΑ ΠΑΝΤΑ | EMERGENCY |

### ⌨️ Keyboard Shortcuts
| Key | Action |
|-----|--------|
| **E** | Emergency Stop |
| **P** | Pause |
| **A** | Approve Trade |
| **R** | Resume |

### 🔌 API Controls (cURL)
```bash
# Emergency Stop
curl -X POST http://localhost:8080/control/emergency-stop

# Pause
curl -X POST http://localhost:8080/control/pause

# Resume
curl -X POST http://localhost:8080/control/resume

# Toggle Auto
curl -X POST http://localhost:8080/control/toggle-auto

# Toggle Paper/Real
curl -X POST http://localhost:8080/control/toggle-paper

# Close All Positions
curl -X POST http://localhost:8080/control/close-all

# Confirm Trade (manual mode)
curl -X POST http://localhost:8080/control/confirm-trade

# Reset System
curl -X POST http://localhost:8080/control/reset
```

---

## 11. MONITORING & LOGS

### 📊 Tmux Sessions
```bash
# Δες όλα τα sessions
tmux ls

# Μπες στο paper trading
tmux attach -t beast

# Μπες στο dashboard
tmux attach -t dashboard

# Βγες (χωρίς να σκοτώσεις)
Ctrl+B, D

# Σκότωσε session
tmux kill-session -t beast
```

### 📁 Log Files
```bash
# Paper trading state
cat /root/.openclaw/workspace/agents/logs/paper_trading.json

# Event log (line by line)
tail -20 /root/.openclaw/workspace/agents/logs/trading_log.jsonl

# Dashboard API test
curl -s http://localhost:8080/api/state | python3 -m json.tool

# Portfolio
curl -s http://localhost:8080/api/portfolio | python3 -m json.tool

# Positions
curl -s http://localhost:8080/api/positions | python3 -m json.tool

# Signals
curl -s http://localhost:8080/api/signals | python3 -m json.tool

# Events
curl -s http://localhost:8080/api/events?limit=20 | python3 -m json.tool

# Health
curl -s http://localhost:8080/api/health | python3 -m json.tool
```

---

## 12. TROUBLESHOOTING

### ❌ Port 8080 Already in Use
```bash
# Βρες ποιο process το κρατάει
lsof -i :8080

# Σκότωσε το
kill -9 PID

# Ή χρησιμοποίησε άλλο port
python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8081
```

### ❌ Import Error
```bash
# Εγκατάσταση missing package
pip3 install fastapi uvicorn aiohttp websockets jinja2

# Επιβεβαίωση
python3 -c "import fastapi; print(fastapi.__version__)"
```

### ❌ Dashboard Not Loading
```bash
# Έλεγξε αν τρέχει
curl -v http://127.0.0.1:8080/api/state

# Έλεγξε logs
tmux capture-pane -t dashboard -p | tail -20

# Restart
tmux kill-session -t dashboard
tmux new-session -d -s dashboard "cd /root/.openclaw/workspace/agents && python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080"
```

### ❌ Paper Trading Not Scanning
```bash
# Έλεγξε αν τρέχει
tmux capture-pane -t beast -p | tail -10

# Restart
tmux kill-session -t beast
tmux new-session -d -s beast "python3 /tmp/beast_mode_paper.py"
```

### ❌ No Opportunities Found
- **Κανονικό:** Οι αγορές μπορεί να είναι ήσυχες
- **Έλεγξε filters:** Min liquidity $65K, volume $120K είναι strict
- **Ώρα:** Crypto είναι πιο ενεργό 8AM-8PM UTC
- **Δες raw data:** `curl -s https://api.dexscreener.com/latest/dex/tokens/solana | python3 -m json.tool | head -50`

### ❌ Telegram Not Sending
```bash
# Έλεγξε bot token
curl -s "https://api.telegram.org/botYOUR_TOKEN/getMe"

# Έλεγξε chat ID
curl -s "https://api.telegram.org/botYOUR_TOKEN/getUpdates"

# Test message
curl -s -X POST "https://api.telegram.org/botYOUR_TOKEN/sendMessage" \
  -d "chat_id=YOUR_CHAT_ID" \
  -d "text=Test message"
```

### ❌ WebSocket Offline
- Refresh page
- Έλεγξε αν dashboard τρέχει: `curl http://localhost:8080/api/state`
- Κοίτα console logs στο browser (F12 → Console)

---

## 13. SECURITY CHECKLIST

### 🔒 Πριν Πας Real Trading
- [ ] Paper mode: ON για τουλάχιστον 1 εβδομάδα
- [ ] Win rate > 55% σε paper
- [ ] Drawdown < 15% σε paper
- [ ] Καταλαβαίνεις κάθε metric στο dashboard
- [ ] Ξέρεις πώς να κάνεις Emergency Stop
- [ ] API keys έχουν ΜΟΝΟ trade permissions (όχι withdrawal)
- [ ] 2FA ενεργοποιημένο σε όλα τα exchanges
- [ ] Έχεις tested το Emergency Stop 3+ φορές

### 🔐 API Key Best Practices
- **ΜΗΝ** αποθηκεύεις keys σε git
- **ΜΗΝ** μοιράζεσαι το `.env` αρχείο
- **ΜΗΝ** δίνεις withdrawal permissions
- **ΧΡΗΣΙΜΟΠΟΙΕΙ** IP whitelist αν υποστηρίζεται
- **ROTATE** keys κάθε 3 μήνες

---

## 14. MAINTENANCE

### 🔄 Καθημερινά
```bash
# Έλεγξε αν τρέχει
tmux ls

# Δες PnL
curl -s http://localhost:8080/api/portfolio | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Balance: {d[\"balance\"]} | PnL: {d[\"total_pnl\"]}')"

# Έλεγξε positions
curl -s http://localhost:8080/api/positions | python3 -m json.tool
```

### 🔄 Εβδομαδιαία
```bash
# Καθάρισε logs (αν είναι μεγάλα)
truncate -s 0 /root/.openclaw/workspace/agents/logs/trading_log.jsonl

# Έλεγξε disk space
df -h

# Update packages
pip3 install --upgrade fastapi uvicorn aiohttp
```

### 🔄 Μηνιαία
- Review performance metrics
- Adjust risk parameters αν χρειάζεται
- Rotate API keys
- Backup configuration

---

## 🎯 CHECKLIST — ΕΊΣΑΙ ΈΤΟΙΜΟΣ?

### Phase 1: Εγκατάσταση
- [ ] Python 3.8+ installed
- [ ] pip3 working
- [ ] tmux installed
- [ ] All pip packages installed
- [ ] `.env` file created with API keys
- [ ] Telegram bot created and tested

### Phase 2: Εκκίνηση
- [ ] Dashboard server running on port 8080
- [ ] Paper trading engine running
- [ ] Both visible in `tmux ls`
- [ ] Dashboard accessible in browser
- [ ] API endpoints responding

### Phase 3: Testing
- [ ] Paper trades executing
- [ ] Telegram alerts received
- [ ] Dashboard updates in real-time
- [ ] Emergency stop tested
- [ ] Pause/Resume tested

### Phase 4: Go Live (Προαιρετικά)
- [ ] Paper mode: 7+ days
- [ ] Win rate > 55%
- [ ] Drawdown < 15%
- [ ] Real API keys configured
- [ ] Withdrawal permissions OFF
- [ ] 2FA enabled everywhere
- [ ] Emergency stop muscle memory

---

## 📞 ΥΠΟΣΤΉΡΙΞΗ

Αν κολλήσεις:
1. **Τσέκαρε το troubleshooting section**
2. **Στείλε μου logs:** `tmux capture-pane -t beast -p | tail -30`
3. **Στείλε μου error:** Copy-paste το πλήρες error message
4. **Πες μου:** Ποιο βήμα; Τι περίμενες; Τι είδες;

---

> **🐺 ΚΑΛΗ ΤΥΧΗ! ΤΟ ΣΎΣΤΗΜΑ ΕΊΝΑΙ ΕΤΟΙΜΟ ΝΑ ΔΟΥΛΈΨΕΙ ΓΙΑ ΣΈΝΑ 24/7!**

---

*Τελευταία ενημέρωση: 2026-05-18 | Έκδοση: Beast Mode v2*
