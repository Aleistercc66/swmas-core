#!/usr/bin/env python3
"""
SWMAS Telegram Bridge — Real-time message bridge
Φέρνει μηνύματα από Telegram bot → εδώ (AImind) και αντίστροφα
"""

import asyncio
import json
import os
import time
from pathlib import Path

INBOX = Path("/root/.openclaw/workspace/swmas_v2/telegram_inbox.jsonl")
OUTBOX = Path("/root/.openclaw/workspace/swmas_v2/telegram_outbox.jsonl")
ALERTS = Path("/tmp/swmas_alerts.jsonl")
SEEN_FILE = Path("/tmp/swmas_seen.json")

BOT_TOKEN = "8585099271:AAFQI6OZD8UdJp3lnq8oSbJOOm5njF2io8Y"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def load_seen() -> set:
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE) as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

async def send_telegram_message(chat_id: int, text: str):
    """Send message back to Telegram via Bot API."""
    import aiohttp
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if data.get("ok"):
                    print(f"[✅ SENT] chat_id={chat_id}")
                else:
                    print(f"[❌ FAIL] {data}")
    except Exception as e:
        print(f"[❌ ERROR] {e}")

async def poll_inbox():
    """Poll inbox file and write alerts for new messages."""
    seen = load_seen()
    last_size = 0

    while True:
        try:
            if INBOX.exists() and INBOX.stat().st_size != last_size:
                with open(INBOX, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                new_messages = []
                for line in lines:
                    line = line.strip()
                    if not line or line in seen:
                        continue
                    seen.add(line)
                    try:
                        data = json.loads(line)
                        new_messages.append(data)
                    except:
                        continue

                if new_messages:
                    # Write alerts file for AImind to read
                    with open(ALERTS, "a", encoding="utf-8") as f:
                        for msg in new_messages:
                            alert = {
                                "timestamp": time.time(),
                                "type": "telegram_inbound",
                                "chat_id": msg.get("chat_id"),
                                "username": msg.get("username"),
                                "message": msg.get("message"),
                            }
                            f.write(json.dumps(alert, ensure_ascii=False) + "\n")
                            print(f"[📩 ALERT] {msg.get('username')}: {msg.get('message')[:60]}")

                    save_seen(seen)

                last_size = INBOX.stat().st_size

        except Exception as e:
            print(f"[Poll error] {e}")

        await asyncio.sleep(2)

async def poll_outbox():
    """Poll for responses from AImind and send to Telegram."""
    processed = set()
    last_size = 0

    while True:
        try:
            if OUTBOX.exists() and OUTBOX.stat().st_size != last_size:
                with open(OUTBOX, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line in lines:
                    line = line.strip()
                    if not line or line in processed:
                        continue
                    processed.add(line)
                    try:
                        data = json.loads(line)
                        chat_id = data.get("chat_id")
                        text = data.get("message", "")
                        if chat_id and text:
                            await send_telegram_message(chat_id, text)
                    except Exception as e:
                        print(f"[Outbox parse error] {e}")

                last_size = OUTBOX.stat().st_size

        except Exception as e:
            print(f"[Outbox error] {e}")

        await asyncio.sleep(3)

async def main():
    print("=" * 50)
    print("🌉 SWMAS Telegram Bridge")
    print("=" * 50)
    print(f"Inbox:  {INBOX}")
    print(f"Outbox: {OUTBOX}")
    print(f"Alerts: {ALERTS}")
    print("")
    print("Waiting for messages...")
    print("")

    await asyncio.gather(
        poll_inbox(),
        poll_outbox(),
    )

if __name__ == "__main__":
    asyncio.run(main())
