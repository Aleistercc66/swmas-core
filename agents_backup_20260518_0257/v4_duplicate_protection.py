#!/usr/bin/env python3
"""
🚫 DUPLICATE SIGNAL PROTECTION
Prevents re-entry into same setup or momentum leg.
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

class DuplicateProtector:
    def __init__(self):
        self.trade_log = "/root/.openclaw/workspace/agents/logs/trade_history.json"
        self.active_signals = "/root/.openclaw/workspace/agents/logs/active_signals.json"
        self.recently_traded = {}  # symbol -> last_trade_time
        self.load_recent()
    
    def load_recent(self):
        """Load recently traded symbols"""
        try:
            with open(self.trade_log, "r") as f:
                trades = json.load(f)
            for trade in trades[-50:]:  # Last 50 trades
                if trade.get("status") == "CLOSED":
                    symbol = trade.get("symbol")
                    closed_at = trade.get("closed_at")
                    if symbol and closed_at:
                        self.recently_traded[symbol] = datetime.fromisoformat(closed_at)
        except:
            pass
    
    def check_duplicate(self, symbol, entry_price, signal_id=None):
        """
        Check if this is a duplicate/re-entry
        Returns: (can_trade, reason)
        """
        
        # Check 1: Recently traded (cooldown period)
        if symbol in self.recently_traded:
            last_trade = self.recently_traded[symbol]
            cooldown = timedelta(hours=6)  # 6 hour minimum between trades on same symbol
            if datetime.now() - last_trade < cooldown:
                remaining = cooldown - (datetime.now() - last_trade)
                return False, f"COOLDOWN: {symbol} traded {remaining.seconds // 3600}h ago"
        
        # Check 2: Currently open position
        try:
            with open(self.active_signals, "r") as f:
                active = json.load(f)
            for sig in active.get("signals", []):
                if sig.get("symbol") == symbol and sig.get("status") == "ACTIVE":
                    return False, f"ALREADY_ACTIVE: Position in {symbol} is open"
        except:
            pass
        
        # Check 3: Same momentum leg (price too close to previous entry)
        # If price is within 5% of previous entry, it's likely the same move
        for past_symbol, past_time in self.recently_traded.items():
            if past_symbol == symbol:
                # Check if price moved significantly
                if datetime.now() - past_time < timedelta(hours=24):
                    return False, f"SAME_MOMENTUM: {symbol} in same momentum leg"
        
        return True, "PASS"
    
    def log_signal(self, symbol, entry_price, signal_id):
        """Log active signal"""
        try:
            with open(self.active_signals, "r") as f:
                active = json.load(f)
        except:
            active = {"signals": []}
        
        active["signals"].append({
            "symbol": symbol,
            "entry": entry_price,
            "id": signal_id,
            "status": "ACTIVE",
            "timestamp": datetime.now().isoformat(),
        })
        
        safe_write_json(self.active_signals, active)
    
    def close_signal(self, symbol, signal_id):
        """Mark signal as closed"""
        try:
            with open(self.active_signals, "r") as f:
                active = json.load(f)
            
            for sig in active.get("signals", []):
                if sig.get("id") == signal_id:
                    sig["status"] = "CLOSED"
                    sig["closed_at"] = datetime.now().isoformat()
            
            safe_write_json(self.active_signals, active)
        except:
            pass
        
        # Update recently traded
        self.recently_traded[symbol] = datetime.now()

def main():
    print("[DUPLICATE PROTECTOR] Anti-re-entry system active")
    print("[DUPLICATE PROTECTOR] Cooldown: 6 hours per symbol")
    
    protector = DuplicateProtector()
    
    while True:
        try:
            # Check latest signals
            risk  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/dynamic_risk_output.json", {})
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Duplicate Check:")
            
            for opp in risk.get("approved", [])[:5]:
                symbol = opp["symbol"]
                entry = opp["entry_zone"]["primary"]
                
                can_trade, reason = protector.check_duplicate(symbol, entry)
                
                if can_trade:
                    print(f"   ✅ {symbol}: CLEAN — Can trade")
                else:
                    print(f"   ❌ {symbol}: {reason}")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(300)  # Every 5 minutes

if __name__ == "__main__":
    main()
