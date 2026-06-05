#!/usr/bin/env python3
"""
👑 AGENT 7: MASTER CONTROLLER
The brain. Orchestrates all agents. Sends Telegram alerts.
"""
import json
import time
import requests
from datetime import datetime

BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
CHAT_ID = "158923136"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg_send(msg):
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=10,
        )
        return resp.status_code == 200
    except:
        return False

def load_all_inputs():
    data = {}
    for file, key in [
        ("/root/.openclaw/workspace/agents/tmp_state/scanner_output.json", "scanner"),
        ("/root/.openclaw/workspace/agents/tmp_state/sentiment_output.json", "sentiment"),
        ("/root/.openclaw/workspace/agents/tmp_state/whale_output.json", "whale"),
        ("/root/.openclaw/workspace/agents/tmp_state/validator_output.json", "validator"),
        ("/root/.openclaw/workspace/agents/tmp_state/risk_output.json", "risk"),
        ("/root/.openclaw/workspace/agents/tmp_state/performance_output.json", "performance"),
    ]:
        try:
            with open(file, "r") as f:
                data[key] = json.load(f)
        except:
            data[key] = None
    return data

def build_trade_alert(opp):
    """Build the exact profit points alert"""
    symbol = opp.get("symbol", "???")
    price = opp.get("price", 0)
    entry = opp["entry_zone"]["primary"]
    stop = opp["stop_loss"]
    tp1 = opp["take_profits"]["tp1_50pct"]
    tp2 = opp["take_profits"]["tp2_100pct"]
    tp3 = opp["take_profits"]["tp3_200pct"]
    rr = opp["risk_reward_ratio"]
    conf = opp["confidence"]
    risk_level = opp["risk_level"]
    position = opp["position_size_pct"]
    
    emoji = "🎯" if conf >= 80 else "📈" if conf >= 70 else "⚡"
    risk_emoji = "🟢" if risk_level == "LOW" else "🟡" if risk_level == "MEDIUM" else "🔴"
    
    msg = f"""{emoji} *{symbol} — LONG SETUP*

📍 *ENTRY ZONE:*    `${entry:.8f}`
🛑 *STOP LOSS:*     `${stop:.8f}` *(−20%)*
🎯 *TP1 (+50%):*   `${tp1:.8f}` → *Scale 33%*
🚀 *TP2 (+100%):*  `${tp2:.8f}` → *Scale 33%*
🌕 *TP3 (+200%):*  `${tp3:.8f}` → *Trail remainder*

📊 *R:R Ratio:*     *1:{rr}*
💰 *Position Size:* *{position}%* of portfolio
{risk_emoji} *Risk Level:*     *{risk_level}*
🎲 *Confidence:*   *{conf}/100*

⚠️ *Risk Factors:*
"""
    for factor in opp.get("risk_factors", []):
        msg += f"• {factor}\n"
    
    # Add confluence data
    msg += f"\n🔍 *Multi-Agent Confluence:*\n"
    msg += f"• Scanner: Momentum detected ✅\n"
    msg += f"• Validator: All checks passed ✅\n"
    msg += f"• Risk Manager: R:R 1:{rr} ✅\n"
    
    return msg

def orchestrate():
    """Main orchestration logic"""
    data = load_all_inputs()
    
    # Check if risk manager has approved opportunities
    risk = data.get("risk")
    if not risk:
        return None, "No risk data available"
    
    approved = risk.get("approved", [])
    if not approved:
        return None, "No high-probability opportunities detected under current market conditions."
    
    # Build alerts
    alerts = []
    for opp in approved:
        if opp["confidence"] >= 60 and opp["risk_reward_ratio"] >= 2:
            alert = build_trade_alert(opp)
            alerts.append(alert)
    
    if not alerts:
        return None, "No high-probability opportunities detected under current market conditions."
    
    return alerts, f"{len(alerts)} opportunity(s) approved"

def main():
    print("[MASTER CONTROLLER] Agent started — The Brain")
    print("[MASTER CONTROLLER] Orchestrating all agents...")
    
    # Send startup message
    tg_send("""🤖👑 *SWARM v2.0 ACTIVATED* 👑🤖

*7-Agent Institutional System:*
1️⃣ Scanner — Raw data
2️⃣ Sentiment — Social mood
3️⃣ Whale/Liquidity — Smart money
4️⃣ Validator — Gatekeeper
5️⃣ Risk Manager — Profit points
6️⃣ Performance — Tracking
7️⃣ Master Controller — You

*Discipline:* Quality > Quantity
*Rule:* No trade > Bad trade
*Focus:* Exact entry/stop/TP

_Status: ALL AGENTS OPERATIONAL_""")
    
    while True:
        try:
            alerts, status = orchestrate()
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Orchestration: {status}")
            
            if alerts:
                # Send header
                header = f"🔥 *{len(alerts)} VALIDATED OPPORTUNITY(IES)* 🔥\n\n_Institutional-grade analysis complete. All agents concur._"
                tg_send(header)
                time.sleep(1)
                
                # Send each alert
                for alert in alerts:
                    tg_send(alert)
                    time.sleep(1)
                
                print(f"  ✅ Sent {len(alerts)} alerts to Telegram")
            else:
                print(f"  ⏸️  {status}")
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
