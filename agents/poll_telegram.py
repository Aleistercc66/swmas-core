#!/usr/bin/env python3
"""
📨 TELEGRAM RESPONSE POLLER
Listens for CONFIRM/MODIFY/REJECT from user
"""
import requests
import time
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
CHAT_ID = "158923136"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

last_update_id = 0
pending_signals = {}

def tg_send(msg):
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
    except:
        pass

def poll_responses():
    global last_update_id
    try:
        url = f"{TELEGRAM_API}/getUpdates"
        params = {"offset": last_update_id + 1, "limit": 10}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        for update in data.get("result", []):
            last_update_id = update["update_id"]
            
            if "message" not in update:
                continue
            
            msg = update["message"]
            chat = msg.get("chat", {})
            if str(chat.get("id")) != CHAT_ID:
                continue
            
            text = msg.get("text", "").strip().upper()
            
            if text.startswith("CONFIRM"):
                parts = text.split()
                if len(parts) >= 2:
                    symbol = parts[1]
                    # Read latest dynamic risk output
                    risk = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/dynamic_risk_output.json", {})
                    
                    # Find the signal in approved list
                    for opp in risk.get("approved", []):
                        if opp.get("symbol") == symbol:
                            # Write to confirmed_trades
                            confirmed = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/confirmed_trades.json", {"confirmed": []})
                            confirmed["confirmed"].append(opp)
                            safe_write_json("/root/.openclaw/workspace/agents/tmp_state/confirmed_trades.json", confirmed)
                            
                            tg_send(f"✅ *{symbol} CONFIRMED*\nProceeding with execution...")
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ CONFIRMED: {symbol}")
                            break
                    else:
                        tg_send(f"⚠️ No signal found for {symbol}")
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ CONFIRM: {symbol} not found")
                else:
                    tg_send("Usage: CONFIRM SYMBOL")
            
            elif text.startswith("REJECT"):
                parts = text.split()
                if len(parts) >= 2:
                    symbol = parts[1]
                    tg_send(f"❌ *{symbol} REJECTED*")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ REJECTED: {symbol}")
            
            elif text.startswith("MODIFY"):
                parts = text.split()
                if len(parts) >= 2:
                    symbol = parts[1]
                    tg_send(f"📝 *{symbol} MODIFY* — Please specify new parameters")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📝 MODIFY: {symbol}")
            
            elif text == "STATUS":
                tg_send("📊 *SYSTEM STATUS*\nListening for signals...")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Poll error: {e}")

def main():
    print("[POLLER] Telegram response listener started")
    print("[POLLER] Commands: CONFIRM SYMBOL | REJECT SYMBOL | MODIFY SYMBOL | STATUS")
    while True:
        poll_responses()
        time.sleep(5)

if __name__ == "__main__":
    main()
