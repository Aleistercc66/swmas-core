# Stoiximan Cashout Strategy - Desktop Application

⚡ **Production-grade desktop app** with real-time dashboard for implementing the Two-Step Cashout strategy.

## 🎯 Strategy Overview

**Two-Step Cashout:**
1. **Monitor Pinnacle** (sharp bookmaker) for dropping odds (>5% = smart money signal)
2. **Check Stoiximan** (soft bookmaker) - if they haven't adjusted yet, there's a value window
3. **Golden Hour Cashout** (60-90 min before kickoff) - lock in 1-4% profit pre-match

## 📁 Files

```
cashout_strategy/
├── app.py                          # Main application engine
├── dashboard/
│   ├── server.py                   # FastAPI web server
│   ├── templates/
│   │   └── index.html              # Dashboard UI
│   └── static/
│       ├── style.css               # Dark theme styling
│       └── dashboard.js            # Frontend logic
├── data/                           # SQLite database
├── logs/                           # Application logs
├── Stoiximan_Cashout_Strategy_Guide.docx  # Full 10,424-word strategy guide
├── requirements.txt                # Python dependencies
├── launch.sh                       # Desktop launcher script
└── README.md                       # This file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd /root/.openclaw/workspace/apps/cashout_strategy
./launch.sh install
```

### 2. Start the Application
```bash
./launch.sh start
```

### 3. Open Dashboard
```
http://localhost:8080
```

## 🎮 Dashboard Features

- **Real-time Opportunities Table** - Live tracking of all detected opportunities
- **Stats Cards** - Total, executed, profit %, win rate, today's count, active tracking
- **Golden Hour Alerts** - Automatic highlighting when 60-90 min window is active
- **Confidence Scoring** - Visual bars showing opportunity quality (0-100)
- **Status Filtering** - Filter by detected/tracking/cashout_ready/executed
- **Two-Step Strategy Visual Guide** - Built-in strategy explanation
- **Settings Panel** - Configure scan interval, min drop %, confidence threshold, bankroll
- **Activity Log** - Real-time log of all system events

## 🔔 Telegram Integration (Optional)

To enable Telegram alerts for Golden Hour opportunities:

1. Set your bot token in settings
2. Enable "Telegram Alerts" checkbox
3. Get instant notifications when cashout opportunities are ready

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/api/dashboard` | GET | Full dashboard data |
| `/api/start` | POST | Start scanning |
| `/api/stop` | POST | Stop scanning |
| `/api/opportunities` | GET | List opportunities |
| `/api/opportunities/{id}/execute` | POST | Mark as executed |
| `/api/settings` | POST | Update settings |
| `/api/stats` | GET | Performance stats |
| `/api/health` | GET | Health check |
| `/guide` | GET | Download strategy guide (docx) |

## ⚙️ Configuration

Edit these settings in the dashboard or via API:

| Setting | Default | Description |
|---------|---------|-------------|
| Scan Interval | 120s | How often to check for new opportunities |
| Min Drop % | 5% | Minimum odds drop to trigger alert |
| Min Confidence | 60 | Minimum confidence score (0-100) |
| Bankroll | €2000 | Your total bankroll |
| Max Stake % | 3% | Maximum stake per opportunity |
| Telegram Alerts | On | Enable/disable Telegram notifications |

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│  FastAPI Server  │────▶│  Cashout Engine │
│  (Browser)      │     │  (Port 8080)     │     │  (Python)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │                          │
                              ▼                          ▼
                        ┌─────────────┐            ┌──────────────┐
                        │  SQLite DB  │            │ Pinnacle   │
                        │  (Data)     │            │ API        │
                        └─────────────┘            └──────────────┘
                                                   │ Stoiximan  │
                                                   │ API        │
                                                   └──────────────┘
```

## 📝 Commands

```bash
./launch.sh install   # Install dependencies
./launch.sh start     # Start the app
./launch.sh stop      # Stop the app
./launch.sh status    # Check status
./launch.sh restart   # Restart the app
```

## ⚠️ Important Notes

- **This is a strategy tool, not a guarantee.** The cashout has mathematical -EV, but pre-match cashout on dropping odds creates positive expected value opportunities.
- **Requires discipline** - Bankroll management, stake limits, and emotional control are essential.
- **Account longevity** - Use "mug bets" for camouflage to avoid gubbing. Expect 3-12 months before account limitations.
- **Taxation** - Keep profits under €100 for 0% tax rate in Greece.

## 🎓 Strategy Guide

The full 10,424-word strategy guide with 173 citations is included:
- `Stoiximan_Cashout_Strategy_Guide.docx`
- Access via: `http://localhost:8080/guide`

## 🔧 Advanced Usage

### Custom Odds Sources
Edit `app.py` to add real Pinnacle/Stoiximan API integrations:

```python
class PinnacleMonitor:
    async def fetch_odds(self, sport: str = "Soccer"):
        # Replace with real API calls
        # e.g., requests.get("https://api.pinnacle.com/odds")
        pass
```

### WebSocket Real-time Updates
The dashboard supports WebSocket for instant updates. Uncomment the WebSocket connection in `dashboard.js` and add a WebSocket endpoint in `server.py`.

## 📞 Support

For issues or questions:
1. Check logs: `logs/cashout_YYYYMMDD.log`
2. Check status: `./launch.sh status`
3. Review the strategy guide for detailed explanations

---

**Version:** 1.0  
**Built:** 2026-05-31  
**Strategy:** Two-Step Cashout (Pre-match)  
**Target Platform:** Stoiximan Greece
