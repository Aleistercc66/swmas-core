#!/usr/bin/env python3
"""
👑 MASTER CONTROLLER v4.0 — INSTITUTIONAL EXECUTION
Manual confirmation mode | Capital protection | Standardized signals
"""
import json
import time
import requests
import threading
from datetime import datetime
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
CHAT_ID = "158923136"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Capital protection state
portfolio_state = {
    "daily_pnl": 0.0,
    "daily_trades": 0,
    "consecutive_losses": 0,
    "total_exposure": 0.0,
    "last_trade_time": None,
    "mode": "MANUAL",  # MANUAL | SEMI_AUTO | AUTO
    "emergency_active": False,
    "daily_starting_balance": 10000.0,  # Example
}

# Pending signals waiting for confirmation
pending_signals = {}
last_update_id = 0

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

def check_capital_protection(opp):
    """Apply capital protection rules before any alert"""
    
    # Emergency shutdown check
    if portfolio_state["emergency_active"]:
        return False, "EMERGENCY_SHUTDOWN — Manual resume required"
    
    # Daily drawdown check
    daily_loss_pct = abs(portfolio_state["daily_pnl"]) / portfolio_state["daily_starting_balance"] * 100
    if daily_loss_pct >= 8:
        portfolio_state["emergency_active"] = True
        return False, "EMERGENCY_SHUTDOWN — Daily loss > 8%"
    
    if daily_loss_pct >= 5:
        return False, "COOLDOWN — Daily loss > 5% (4hr pause)"
    
    if daily_loss_pct >= 3:
        return False, "WARNING — Daily loss > 3% (reduced activity)"
    
    # Max daily trades
    if portfolio_state["daily_trades"] >= 5:
        return False, "Daily trade limit reached (5 max)"
    
    # Consecutive losses cooldown
    cl = portfolio_state["consecutive_losses"]
    if cl >= 4:
        return False, "COOLDOWN — 4+ consecutive losses (6hr + reassessment)"
    elif cl >= 3:
        return False, "COOLDOWN — 3 consecutive losses (2hr pause)"
    elif cl >= 2:
        return False, "COOLDOWN — 2 consecutive losses (30min pause)"
    
    # Exposure check
    position_size = opp.get("position_size_pct", 1)
    new_exposure = portfolio_state["total_exposure"] + position_size
    if new_exposure > 50:
        return False, f"MAX_EXPOSURE — Would exceed 50% ({new_exposure:.0f}%)"
    
    # Liquidity check
    liq = opp.get("liquidity", 0)
    if liq < 25000:
        return False, f"LIQUIDITY_TOO_LOW — ${liq:,.0f} < $25K minimum"
    
    # Volatility check
    atr = opp.get("atr_proxy", 0)
    if atr > 25:
        return False, f"VOLATILITY_TOO_HIGH — ATR {atr:.1f}% > 25% max"
    
    return True, "PASS"

def build_signal(opp):
    """Build standardized institutional signal format"""
    
    symbol = opp.get("symbol", "???")
    price = opp.get("price", 0)
    entry = opp["entry_zone"]["primary"]
    stop = opp["stop_loss"]
    stop_dist = opp.get("stop_distance_pct", 5)
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
        dna_data  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/dna_output.json", {})
        for dna in dna_data.get("classifications", []):
            if dna.get("symbol") == symbol:
                dna_type = dna.get("dna_type", "UNKNOWN")
                dna_conf = dna.get("confidence", 0)
                break
    except:
        pass
    
    # Regime-based position adjustment
    regime = "UNKNOWN"
    try:
        reg_data  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/regime_output.json", {})
        regime = reg_data.get("overall", "UNKNOWN")
    except:
        pass
    
    # In ranging/choppy markets, reduce position size
    if regime in ["RANGING", "CHOPPY"]:
        position = max(position - 2, 1)  # Reduce by 2%, min 1%
    elif regime in ["PANIC", "HIGH_VOLATILITY"]:
        position = max(position - 3, 1)  # Reduce by 3%, min 1%
    
def build_signal(opp):
    """Build clean, human-readable signal with profit potential"""
    symbol = opp["symbol"]
    price = opp["price"]
    
    # Format price cleanly
    def fmt_price(p):
        if p == 0:
            return "$0"
        elif p < 0.000001:
            return f"${p:.12f}".rstrip('0').rstrip('.')
        elif p < 0.0001:
            return f"${p:.10f}".rstrip('0').rstrip('.')
        elif p < 0.001:
            return f"${p:.8f}".rstrip('0').rstrip('.')
        elif p < 0.01:
            return f"${p:.6f}".rstrip('0').rstrip('.')
        elif p < 1:
            return f"${p:.4f}".rstrip('0').rstrip('.')
        elif p < 1000:
            return f"${p:.2f}"
        else:
            return f"${p:,.2f}"
    
    # Format big numbers
    def fmt_big(n):
        if n >= 1_000_000:
            return f"${n/1_000_000:.2f}M"
        elif n >= 1_000:
            return f"${n/1_000:.1f}K"
        else:
            return f"${n:,.0f}"
    
    entry = opp["entry_zone"]["primary"]
    stop = opp["stop_loss"]
    tp1 = opp["take_profits"]["tp1_2x_risk"]
    tp2 = opp["take_profits"]["tp2_3x_risk"]
    tp3 = opp["take_profits"]["tp3_4x_risk"]
    
    liq = opp["liquidity"]
    vol = opp["volume_24h"]
    conf = opp["confidence"]
    rr = opp["risk_reward_ratio"]
    risk = opp["risk_level"]
    
    # Profit metrics (new!)
    profit_pot = opp.get("profit_potential", 0)
    exec_prob = opp.get("execution_probability", 0)
    expected_ret = opp.get("expected_return_pct", 0)
    tier = opp.get("tier", "TIER_3")
    
    # Tier emoji
    if tier == "TIER_1":
        tier_emoji = "🔥"
        tier_name = "EXCEPTIONAL"
    elif tier == "TIER_2":
        tier_emoji = "✨"
        tier_name = "STRONG"
    else:
        tier_emoji = "⭐"
        tier_name = "MODERATE"
    
    # Direction
    direction = "LONG" if opp.get("price", 0) > 0 else "SHORT"
    dir_emoji = "🟢" if direction == "LONG" else "🔴"
    
    # Signal ID
    signal_id = f"{symbol}_{datetime.now().strftime('%H%M%S')}"
    
    msg = f"""═══════════════════════════════════════
{tier_emoji} {symbol} — {tier_name} OPPORTUNITY
{dir_emoji} Direction: {direction}

📊 Price: {fmt_price(price)}
💧 Liquidity: {fmt_big(liq)} | 📈 Vol24h: {fmt_big(vol)}

🎯 PROFIT POTENTIAL: {profit_pot}/100
🎲 Execution Prob: {exec_prob}%
💰 Expected Return: +{expected_ret}%

📈 RISK/REWARD: 1:{rr}
🎲 Confidence: {conf}/100
⚠️  Risk Level: {risk}

📍 ENTRY ZONE:    {fmt_price(entry)}
🛑 STOP LOSS:     {fmt_price(stop)} ({-opp['stop_distance_pct']:.1f}%)
🎯 TP1 (2x):      {fmt_price(tp1)}
🚀 TP2 (3x):      {fmt_price(tp2)}
🌕 TP3 (4x):      {fmt_price(tp3)}

💰 POSITION SIZE: {opp['position_size_pct']}% of portfolio

═══════════════════════════════════════
Reply: CONFIRM {symbol} | MODIFY {symbol} | REJECT {symbol}
═══════════════════════════════════════"""
    
    return msg, signal_id

def orchestrate():
    """Main orchestration — returns ALL signals, not just high-confidence"""
    
    # Load dynamic risk output
    try:
        risk  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/dynamic_risk_output.json", {})
    except:
        return None, "No dynamic risk data available"
    
    approved = risk.get("approved", [])
    if not approved:
        return None, "No opportunities detected under current market conditions."
    
    # Build ALL signals (no filtering)
    all_signals = []
    seen_symbols = set()
    
    for opp in approved:
        symbol = opp.get("symbol", "???")
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        
        signal, signal_id = build_signal(opp)
        all_signals.append((signal, signal_id, opp))
    
    if not all_signals:
        return None, "No signals available after deduplication."
    
    return all_signals, f"{len(all_signals)} signal(s) detected"

def main():
    print("[MASTER CONTROLLER v4.0] Institutional execution framework")
    print("[MASTER CONTROLLER v4.0] MANUAL mode — User confirmation required")
    print("[MASTER CONTROLLER v4.0] Capital protection ACTIVE")
    
    # Send startup message
    tg_send("""🛡️🤖 SWARM v4.0 — INSTITUTIONAL EXECUTION 🤖🛡️

*Capital Protection Protocol:*
• Max loss per trade: 1-2%
• Max daily drawdown: 5% (cooldown)
• Emergency shutdown: 8%
• Max daily trades: 5
• Consecutive loss cooldown: ACTIVE
• Exposure limit: 50% max

*Execution Mode:* MANUAL (user confirmation required)

*Discipline:*
Quality > Quantity
No trade > Bad trade
Survive first, profit second

_Status: ALL SYSTEMS OPERATIONAL_""")
    
    while True:
        try:
            signals, status = orchestrate()
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Orchestration: {status}")
            
            if signals:
                # Check auto mode
                auto_mode = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/auto_mode.json", {"enabled": False})
                is_auto = auto_mode.get("enabled", False)
                
                # Separate signal types
                approved_signals = [(sig, sid, opp) for sig, sid, opp in signals if opp.get("confidence", 0) >= 60 and opp.get("risk_reward_ratio", 0) >= 2]
                low_conf_signals = [(sig, sid, opp) for sig, sid, opp in signals if opp.get("confidence", 0) < 60 or opp.get("risk_reward_ratio", 0) < 2]
                capital_blocked = []
                
                # Check capital protection for approved signals
                for sig, sid, opp in approved_signals[:]:  # iterate copy
                    can_trade, reason = check_capital_protection(opp)
                    if not can_trade:
                        capital_blocked.append((sig, sid, opp, reason))
                        approved_signals.remove((sig, sid, opp))
                
                # Send ALL signals to Telegram
                if approved_signals:
                    tg_send(f"✅ *{len(approved_signals)} APPROVED SIGNAL(S)*")
                    time.sleep(1)
                    for signal, signal_id, opp in approved_signals:
                        tg_send(signal)
                        print(f"  📤 APPROVED: {signal_id}")
                        time.sleep(2)
                
                if low_conf_signals:
                    tg_send(f"⚠️ *{len(low_conf_signals)} LOW CONFIDENCE SIGNAL(S)*")
                    time.sleep(1)
                    for signal, signal_id, opp in low_conf_signals:
                        msg = f"⚠️ {opp['symbol']} — LOW CONFIDENCE\n• Price: ${opp['price']:.8f}\n• Confidence: {opp['confidence']}/100\n• R:R: 1:{opp['risk_reward_ratio']}\n• Status: MONITOR ONLY"
                        tg_send(msg)
                        print(f"  📤 LOW CONF: {signal_id}")
                        time.sleep(2)
                
                if capital_blocked:
                    tg_send(f"🛡️ *{len(capital_blocked)} BLOCKED BY CAPITAL PROTECTION*")
                    for sig, sid, opp, reason in capital_blocked:
                        tg_send(f"🛡️ {opp['symbol']} — BLOCKED\n• Reason: {reason}\n• Status: CAPITAL PROTECTION")
                        time.sleep(1)
                
                # Auto-confirm approved if in auto mode
                if is_auto and approved_signals:
                    print(f"  🤖 AUTO MODE: Auto-confirming {len(approved_signals)} approved signals")
                    confirmed = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/confirmed_trades.json", {"confirmed": []})
                    for signal, signal_id, opp in approved_signals:
                        confirmed["confirmed"].append(opp)
                        print(f"  ✅ AUTO-CONFIRMED: {opp['symbol']}")
                    safe_write_json("/root/.openclaw/workspace/agents/tmp_state/confirmed_trades.json", confirmed)
                    
                    tg_send(f"🤖 *AUTO MODE* — {len(approved_signals)} trade(s) auto-executed")
            else:
                print(f"  ⏸️  {status}")
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()
