# CashOut System 💰

Real-time sports betting cash-out monitoring and analysis system.

## Features

- ✅ Live odds scraping from Stoiximan & Novibet
- ✅ Real-time EV (Expected Value) tracking
- ✅ Price drift simulation
- ✅ Smart cash-out alerts via Telegram
- ✅ Desktop notifications with sound
- ✅ Manual cash-out tracking
- ✅ Multi-bet monitoring

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/cashout` | Dashboard |
| `/cashout status` | System status |
| `/cashout track <id> <home> <away> <bookmaker> <odds> <stake>` | Track a bet |
| `/cashout list` | List tracked bets |
| `/cashout check` | Check all matches now |
| `/cashout analysis <match_id>` | Get analysis |

## Example Usage

```
/cashout track 12345 Olympiacos PAOK Stoiximan 2.50 100
```

This tracks a €100 bet on Olympiacos at 2.50 odds.

## Alerts

The system sends alerts when:
- 🟢 Cash-out ROI > 20% (Good opportunity)
- 🔥 Cash-out ROI > 50% (Optimal cash-out)
- 📊 Price drift > 15% (Significant change)

## Files

- `scrapers/stoiximan_scraper.py` - Stoiximan odds scraper
- `scrapers/novibet_scraper.py` - Novibet odds scraper
- `core/cashout_calculator.py` - EV calculation engine
- `alerts/telegram_alerts.py` - Alert system
- `cashout_orchestrator.py` - Main orchestrator

## Configuration

Edit `cashout_orchestrator.py` to set:
- Check interval (default: 30 seconds)
- Bot token and chat ID
- Alert thresholds

## Running Locally

```bash
cd /root/.openclaw/workspace/cashout_system
python3 cashout_orchestrator.py
```

## Requirements

- Python 3.8+
- aiohttp
- numpy
- python-telegram-bot
