#!/usr/bin/env python3
"""
Airdrop Farming System — Autonomous Tracker
Tracks airdrops, monitors deadlines, sends reminders
"""
import requests, json, sqlite3, os, time, sys
from datetime import datetime, timedelta
from threading import Thread

TELEGRAM_BOT_TOKEN = "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac"
TELEGRAM_CHAT_ID = "158923136"

DB_PATH = "/root/.openclaw/workspace/data/airdrop_tracker.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS airdrops (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            protocol TEXT NOT NULL,
            chain TEXT,
            status TEXT DEFAULT 'active',
            confidence TEXT,
            deadline TEXT,
            snapshot_date TEXT,
            estimated_value TEXT,
            min_deposit REAL,
            actions_required TEXT,
            priority INTEGER DEFAULT 5,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_reminder TEXT,
            completed INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY,
            airdrop_id INTEGER,
            reminder_type TEXT,
            scheduled_for TEXT,
            sent INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def send_alert(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}")

def add_airdrop(name, protocol, chain, confidence, deadline, snapshot, est_value, min_deposit, actions, priority=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO airdrops (name, protocol, chain, confidence, deadline, snapshot_date, estimated_value, min_deposit, actions_required, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, protocol, chain, confidence, deadline, snapshot, est_value, min_deposit, actions, priority))
    conn.commit()
    conn.close()

def load_initial_airdrops():
    airdrops = [
        ("Meteora Season 2", "meteora", "solana", "HIGH", "2026-07-01", "2026-06-15", "$300-$1,500", 100, "LP into pools, generate fees, maintain 30+ days", 5),
        ("marginfi Points", "marginfi", "solana", "HIGH", "2026-06-30", "2026-06-01", "$200-$700", 100, "Deposit + borrow, use swap/stake/bridge, earn hourly points", 4),
        ("Kamino Vaults", "kamino", "solana", "HIGH", "2026-07-15", "2026-06-30", "$150-$600", 100, "Deposit USDC/SOL into vaults, use multiply/leverage", 4),
        ("Jito Restaking", "jito", "solana", "MEDIUM", "2026-08-01", "2026-07-01", "$300-$1,200", 50, "Stake SOL -> jitoSOL -> restake into vaults", 3),
        ("Hyperliquid Future", "hyperliquid", "arbitrum", "MEDIUM", "TBD", "TBD", "$500-$2,000", 200, "Trade perps, stake, provide liquidity", 3),
        ("Drift FUEL", "drift", "solana", "MEDIUM", "Ongoing", "Monthly", "$300-$800", 100, "Trade perps, accumulate FUEL points", 2),
        ("Backpack Season 4", "backpack", "solana", "MEDIUM", "2026-06-30", "2026-06-15", "$500-$5,000", 200, "Trade on exchange, climb tiers", 2),
        ("Polymarket Token", "polymarket", "polygon", "LOW", "TBD", "TBD", "$100-$500", 50, "Trade prediction markets, provide liquidity", 1),
    ]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for a in airdrops:
        c.execute('SELECT id FROM airdrops WHERE name = ?', (a[0],))
        if not c.fetchone():
            add_airdrop(*a)
    conn.commit()
    conn.close()
    print(f"Loaded {len(airdrops)} airdrop opportunities")

def check_reminders():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    c.execute('''
        SELECT id, name, protocol, deadline, snapshot_date, actions_required, confidence
        FROM airdrops 
        WHERE completed = 0 AND status = 'active'
        AND (deadline != 'TBD' AND deadline != 'Ongoing')
    ''')
    for row in c.fetchall():
        id, name, protocol, deadline, snapshot, actions, confidence = row
        try:
            deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
            days_left = (deadline_dt - now).days
            if days_left in [7, 3, 1, 0]:
                c.execute('''
                    SELECT id FROM reminders 
                    WHERE airdrop_id = ? AND reminder_type = ? AND sent = 1
                ''', (id, f"deadline_{days_left}d"))
                if not c.fetchone():
                    alert = f"""⏰ **AIRDROP REMINDER: {days_left} days left!**

🎯 **{name}** | Confidence: {confidence}
📅 Deadline: {deadline}
📸 Snapshot: {snapshot}

📝 **Actions needed:**
{actions}

⚡ Don't miss this! Set up now if you haven't already.
"""
                    send_alert(alert)
                    c.execute('''
                        INSERT INTO reminders (airdrop_id, reminder_type, scheduled_for, sent)
                        VALUES (?, ?, ?, 1)
                    ''', (id, f"deadline_{days_left}d", now.strftime("%Y-%m-%d %H:%M")))
        except Exception as e:
            print(f"Error checking {name}: {e}")
    conn.commit()
    conn.close()

def daily_report():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT name, protocol, confidence, deadline, snapshot_date, completed
        FROM airdrops WHERE status = 'active' ORDER BY priority DESC
    ''')
    lines = ["📊 **DAILY AIRDROP TRACKER** 📊\n"]
    for row in c.fetchall():
        name, protocol, conf, deadline, snapshot, completed = row
        status = "✅ Done" if completed else "⏳ Active"
        lines.append(f"{status} **{name}** | {conf} | 📅 {deadline} | 📸 {snapshot}")
    conn.close()
    report = "\n".join(lines)
    report += "\n\n💡 Use `/airdrop_status` anytime for live updates!"
    send_alert(report)

def main_loop():
    print("🤖 Airdrop Farming System started!")
    last_report_day = None
    while True:
        now = datetime.now()
        check_reminders()
        if now.hour == 9 and now.day != last_report_day:
            daily_report()
            last_report_day = now.day
        if now.hour % 6 == 0 and now.minute < 5:
            print(f"[{now.strftime('%H:%M')}] Research cycle complete.")
        time.sleep(300)

if __name__ == "__main__":
    init_db()
    load_initial_airdrops()
    main_loop()
