#!/usr/bin/env python3
"""
🧠 BRAIN TRIGGER — Summons the AI agent to analyze market
This is NOT a scanner. It wakes up the brain (me) to do the work.
"""
import requests
import json

BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
CHAT_ID = "158923136"

# Wake me up with a trigger message
msg = "🧠 BRAIN WAKEUP: Time for DexScreener market scan. Analyze for high-profit altcoin opportunities and send alerts."

try:
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg},
        timeout=10
    )
except:
    pass
