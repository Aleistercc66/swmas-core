#!/usr/bin/env python3
"""
⚡ CIRCUIT BREAKER AGENT
Emergency shutdown system. Protects capital at all costs.
"""
import json
import time
import requests
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

# Telegram alerting
BOT_TOKEN = "8667434354:AAFLJ7QSSmNpyW94CdGVANzf9NuDqDJQFuc"
CHAT_ID = "158923136"

def tg_alert(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg},
            timeout=5,
        )
    except:
        pass

class CircuitBreaker:
    def __init__(self):
        self.state = "NORMAL"  # NORMAL | WARNING | COOLDOWN | EMERGENCY
        self.state_file = "/root/.openclaw/workspace/agents/logs/circuit_breaker.json"
        self.trigger_log = []
        self.cooldown_end = None
        self.load_state()
    
    def load_state(self):
        if Path(self.state_file).exists():
            with open(self.state_file, "r") as f:
                data = json.load(f)
                self.state = data.get("state", "NORMAL")
                self.cooldown_end = data.get("cooldown_end")
                self.trigger_log = data.get("triggers", [])
    
    def save_state(self):
        safe_write_json(self.state_file, {
                "state": self.state,
                "cooldown_end": self.cooldown_end,
                "triggers": self.trigger_log[-50:],  # Keep last 50
                "last_check": datetime.now().isoformat(),
            })
    
    def check_portfolio_drawdown(self):
        """Check daily drawdown levels"""
        try:
            portfolio  = safe_read_json("/root/.openclaw/workspace/agents/logs/portfolio_state.json", {})
            
            daily_pnl = portfolio.get("daily_pnl", 0)
            balance = portfolio.get("current_balance", 10000)
            daily_loss_pct = abs(daily_pnl) / balance * 100 if balance > 0 else 0
            
            if daily_loss_pct >= 8:
                return "EMERGENCY", f"Daily loss {daily_loss_pct:.1f}% > 8%"
            elif daily_loss_pct >= 5:
                return "COOLDOWN", f"Daily loss {daily_loss_pct:.1f}% > 5%"
            elif daily_loss_pct >= 3:
                return "WARNING", f"Daily loss {daily_loss_pct:.1f}% > 3%"
        except:
            pass
        return "NORMAL", None
    
    def check_btc_crash(self):
        """Check if BTC crashed > 10% in 1 hour"""
        try:
            regime  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/regime_output.json", {})
            btc_state = regime.get("btc_state", {})
            btc_chg1 = btc_state.get("change_1h", 0)
            if btc_chg1 < -10:
                return "EMERGENCY", f"BTC crashed {btc_chg1:.1f}% in 1 hour"
        except:
            pass
        return "NORMAL", None
    
    def check_volatility_spike(self):
        """Check for extreme volatility"""
        try:
            scanner  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/scanner_output.json", {})
            
            # Find max ATR across all pairs
            max_atr = 0
            for pair in scanner.get("pairs", []):
                chg24 = pair.get("change_24h", 0)
                atr = abs(chg24) / 24 if chg24 else 0
                max_atr = max(max_atr, atr)
            
            if max_atr > 40:  # 40% hourly volatility
                return "EMERGENCY", f"Extreme volatility detected: {max_atr:.1f}% hourly"
            elif max_atr > 25:
                return "COOLDOWN", f"High volatility: {max_atr:.1f}% hourly"
        except:
            pass
        return "NORMAL", None
    
    def check_api_health(self):
        """Check API responsiveness"""
        try:
            start = time.time()
            resp = requests.get("https://api.dexscreener.com/latest/dex/search?q=BTC", timeout=5)
            latency = (time.time() - start) * 1000
            
            if latency > 5000:  # > 5 seconds
                return "COOLDOWN", f"API latency {latency:.0f}ms > 5000ms"
            if resp.status_code != 200:
                return "COOLDOWN", f"API error {resp.status_code}"
        except:
            return "COOLDOWN", "API unreachable"
        return "NORMAL", None
    
    def check_consecutive_losses(self):
        """Check consecutive loss cascade"""
        try:
            portfolio  = safe_read_json("/root/.openclaw/workspace/agents/logs/portfolio_state.json", {})
            cl = portfolio.get("consecutive_losses", 0)
            if cl >= 4:
                return "COOLDOWN", f"4+ consecutive losses ({cl})"
            elif cl >= 3:
                return "WARNING", f"3 consecutive losses"
        except:
            pass
        return "NORMAL", None
    
    def run_checks(self):
        """Run all circuit breaker checks"""
        checks = [
            self.check_portfolio_drawdown,
            self.check_btc_crash,
            self.check_volatility_spike,
            self.check_api_health,
            self.check_consecutive_losses,
        ]
        
        worst_state = "NORMAL"
        worst_reason = None
        
        for check in checks:
            state, reason = check()
            if state == "EMERGENCY":
                worst_state = "EMERGENCY"
                worst_reason = reason
                break  # Emergency overrides everything
            elif state == "COOLDOWN" and worst_state != "EMERGENCY":
                worst_state = "COOLDOWN"
                worst_reason = reason
            elif state == "WARNING" and worst_state == "NORMAL":
                worst_state = "WARNING"
                worst_reason = reason
        
        return worst_state, worst_reason
    
    def update_state(self, new_state, reason):
        """Update circuit breaker state with alerting"""
        if new_state == self.state:
            return  # No change
        
        old_state = self.state
        self.state = new_state
        
        # Log trigger
        trigger = {
            "timestamp": datetime.now().isoformat(),
            "from_state": old_state,
            "to_state": new_state,
            "reason": reason,
        }
        self.trigger_log.append(trigger)
        
        # Set cooldown timer
        if new_state == "COOLDOWN":
            from datetime import timedelta
            self.cooldown_end = (datetime.now() + timedelta(hours=4)).isoformat()
        
        # Alert user
        emoji = "🚨" if new_state == "EMERGENCY" else "⚠️" if new_state == "COOLDOWN" else "⚡"
        msg = f"""{emoji} CIRCUIT BREAKER ACTIVATED {emoji}

State: {old_state} → {new_state}
Reason: {reason}

{"🛑 ALL EXECUTION STOPPED" if new_state in ["COOLDOWN", "EMERGENCY"] else "⚠️ Reduced activity"}

{"Manual reset required" if new_state == "EMERGENCY" else f"Auto-resume: {self.cooldown_end}" if new_state == "COOLDOWN" else "Auto-resume when conditions improve"}
"""
        tg_alert(msg)
        self.save_state()
        
        print(f"\n{emoji} CIRCUIT BREAKER: {old_state} → {new_state}")
        print(f"   Reason: {reason}")
    
    def can_execute(self):
        """Check if execution is allowed"""
        if self.state == "EMERGENCY":
            return False, "EMERGENCY mode — manual reset required"
        elif self.state == "COOLDOWN":
            if self.cooldown_end:
                from datetime import datetime as dt
                if dt.now() < dt.fromisoformat(self.cooldown_end):
                    return False, f"COOLDOWN until {self.cooldown_end}"
            # Cooldown expired
            self.state = "NORMAL"
            self.cooldown_end = None
            self.save_state()
            return True, "Cooldown expired — resuming"
        elif self.state == "WARNING":
            return True, "WARNING — reduced position sizes recommended"
        return True, "NORMAL"
    
    def get_state(self):
        return self.state, self.cooldown_end

def main():
    print("[CIRCUIT BREAKER] Capital protection system active")
    print("[CIRCUIT BREAKER] Monitoring: drawdown, BTC, volatility, API, losses")
    
    breaker = CircuitBreaker()
    
    while True:
        try:
            state, reason = breaker.run_checks()
            if state != breaker.state:
                breaker.update_state(state, reason)
            
            can_exec, msg = breaker.can_execute()
            status = "✅" if can_exec else "🛑"
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {status} Circuit: {breaker.state} | {msg}")
            
            # Auto-save every cycle
            breaker.save_state()
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
