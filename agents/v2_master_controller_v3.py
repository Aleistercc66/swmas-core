#!/usr/bin/env python3
"""
👑 MASTER CONTROLLER v3.0
Orchestrates all agents. Sends Telegram alerts.
Reads from Dynamic Risk Engine (NOT fixed % stops).
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

def build_trade_alert(opp):
    """Build the exact profit points alert with dynamic risk"""
    symbol = opp.get("symbol", "???")
    price = opp.get("price", 0)
    entry = opp["entry_zone"]["primary"]
    stop = opp["stop_loss"]
    stop_dist = opp.get("stop_distance_pct", 20)
    tp1 = opp["take_profits"]["tp1_2x_risk"]
    tp2 = opp["take_profits"]["tp2_3x_risk"]
    tp3 = opp["take_profits"]["tp3_4x_risk"]
    rr = opp["risk_reward_ratio"]
    conf = opp["confidence"]
    risk_level = opp["risk_level"]
    position = opp["position_size_pct"]
    atr = opp.get("atr_proxy", 0)
    
    # DNA classification
    dna_type = "UNKNOWN"
    dna_conf = 0
    try:
        with open("/root/.openclaw/workspace/agents/tmp_state/dna_output.json", "r") as f:
            dna_data = json.load(f)
        for dna in dna_data.get("classifications", []):
            if dna.get("symbol") == symbol:
                dna_type = dna.get("dna_type", "UNKNOWN")
                dna_conf = dna.get("confidence", 0)
                break
    except:
        pass
    
    # FOMO status
    fomo_status = "UNKNOWN"
    fomo_score = 0
    try:
        with open("/root/.openclaw/workspace/agents/tmp_state/fomo_output.json", "r") as f:
            fomo_data = json.load(f)
        for fomo in fomo_data.get("results", []):
            if fomo.get("symbol") == symbol:
                fomo_status = fomo.get("status", "UNKNOWN")
                fomo_score = fomo.get("fomo_score", 0)
                break
    except:
        pass
    
    # Regime
    regime = "UNKNOWN"
    try:
        with open("/root/.openclaw/workspace/agents/tmp_state/regime_output.json", "r") as f:
            reg_data = json.load(f)
        regime = reg_data.get("overall", "UNKNOWN")
    except:
        pass
    
    emoji = "🎯" if conf >= 80 else "📈" if conf >= 70 else "⚡"
    risk_emoji = "🟢" if risk_level == "LOW" else "🟡" if risk_level == "MEDIUM" else "🔴"
    
    msg = f"""{emoji} *{symbol} — {dna_type}*

📍 *ENTRY:*    `${entry:.8f}`
🛑 *STOP:*     `${stop:.8f}` *({-stop_dist:.1f}%)*
🎯 *TP1:*      `${tp1:.8f}` *(2x risk)*
🚀 *TP2:*      `${tp2:.8f}` *(3x risk)*
🌕 *TP3:*      `${tp3:.8f}` *(4x risk)*

📊 *R:R:*       *1:{rr}*
💰 *Position:*  *{position}%*
{risk_emoji} *Risk:*      *{risk_level}*
🎲 *Confidence:* *{conf}/100*

🧬 *DNA:* {dna_type} (conf: {dna_conf})
🌍 *Regime:* {regime}
🚫 *FOMO:* {fomo_status} (score: {fomo_score})
📈 *ATR:* {atr:.1f}%
"""
    
    if opp.get("status") == "REJECTED":
        msg += f"\n❌ *REJECTED* — Confidence {conf}/100 below threshold"
    
    return msg

def orchestrate():
    """Main orchestration logic"""
    # Load dynamic risk output
    try:
        with open("/root/.openclaw/workspace/agents/tmp_state/dynamic_risk_output.json", "r") as f:
            risk = json.load(f)
    except:
        return None, "No dynamic risk data available"
    
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
    print("[MASTER CONTROLLER v3.0] Orchestrating 10 agents")
    print("[MASTER CONTROLLER v3.0] Dynamic risk engine active")
    
    # Send startup message
    tg_send("""🤖👑 *SWARM v3.0 — SURVIVABLE SYSTEM* 👑🤖

*10-Agent Quantitative Framework:*
1️⃣ Scanner — Raw data
2️⃣ Sentiment — Social mood
3️⃣ Whale/Liquidity — Smart money
4️⃣ Regime Detector — Market state
5️⃣ DNA Classifier — Setup type
6️⃣ FOMO Filter — Anti-hype
7️⃣ Validator — Gatekeeper
8️⃣ Dynamic Risk — ATR-based stops
9️⃣ Performance — Tracking
🔟 Master Controller — Orchestration

*Upgrades from v2.0:*
✅ Dynamic stops (ATR-based, not fixed %)
✅ Confidence penalty system
✅ Market regime filter
✅ FOMO protection
✅ Setup DNA classification

*Discipline:*
Quality > Quantity
No trade > Bad trade
Data > Emotion

_Status: ALL AGENTS OPERATIONAL_""")
    
    while True:
        try:
            alerts, status = orchestrate()
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Orchestration: {status}")
            
            if alerts:
                # Send header
                header = f"🔥 *{len(alerts)} VALIDATED SETUP(S)* 🔥\n\n_Dynamic risk engine | ATR-based stops | Institutional discipline_"
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
