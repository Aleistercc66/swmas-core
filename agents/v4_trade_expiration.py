#!/usr/bin/env python3
"""
⏰ TRADE EXPIRATION AGENT
Signals become invalid if not activated timely or structure breaks.
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

class TradeExpiration:
    def __init__(self):
        self.expiry_hours = 2  # Signal valid for 2 hours
        self.structure_break_threshold = 5  # 5% adverse move invalidates signal
        self.active_signals_file = "/root/.openclaw/workspace/agents/logs/active_signals.json"
    
    def check_expiration(self, signal):
        """Check if signal has expired"""
        symbol = signal.get("symbol", "???")
        entry = signal.get("entry_zone", {}).get("primary", 0)
        stop = signal.get("stop_loss", 0)
        created_at = signal.get("timestamp", datetime.now().isoformat())
        
        # Check 1: Time expiration
        signal_time = datetime.fromisoformat(created_at) if isinstance(created_at, str) else datetime.now()
        elapsed = datetime.now() - signal_time
        if elapsed > timedelta(hours=self.expiry_hours):
            return False, f"EXPIRED: Signal older than {self.expiry_hours} hours"
        
        # Check 2: Structure break (price moved against signal)
        current_price = self.get_current_price(symbol)
        if current_price > 0 and entry > 0:
            # For long signals
            adverse_move = (entry - current_price) / entry * 100
            if adverse_move > self.structure_break_threshold:
                return False, f"STRUCTURE_BREAK: Price dropped {adverse_move:.1f}% below entry"
            
            # For short signals (if we add them later)
            # adverse_move = (current_price - entry) / entry * 100
        
        # Check 3: Volatility spike after signal
        atr = signal.get("atr_proxy", 0)
        if atr > 25:  # Volatility exploded
            return False, f"VOLATILITY_EXPLOSION: ATR {atr:.1f}% > 25%"
        
        # Check 4: Liquidity collapse
        liq = signal.get("liquidity", 0)
        if liq < 20000:  # Liquidity dropped below $20K
            return False, f"LIQUIDITY_COLLAPSE: ${liq:,.0f} < $20K"
        
        # Check 5: Regime change
        try:
            regime  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/regime_output.json", {})
            current_regime = regime.get("overall", "UNKNOWN")
            if current_regime in ["PANIC", "EUPHORIC"]:
                return False, f"REGIME_CHANGE: Market now {current_regime}"
        except:
            pass
        
        # Time remaining
        remaining = timedelta(hours=self.expiry_hours) - elapsed
        return True, f"VALID: {remaining.seconds // 60} minutes remaining"
    
    def get_current_price(self, symbol):
        """Get current price from scanner"""
        try:
            scanner  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/scanner_output.json", {})
            for pair in scanner.get("pairs", []):
                if pair.get("symbol") == symbol:
                    return pair.get("price", 0)
        except:
            pass
        return 0
    
    def clean_expired_signals(self):
        """Remove expired signals from active list"""
        active = safe_read_json(self.active_signals_file, {"signals": []})
        
        valid_signals = []
        removed = 0
        
        for sig in active.get("signals", []):
            is_valid, reason = self.check_expiration(sig)
            if is_valid:
                valid_signals.append(sig)
            else:
                removed += 1
                sig["status"] = "EXPIRED"
                sig["expiry_reason"] = reason
                sig["expired_at"] = datetime.now().isoformat()
        
        active["signals"] = valid_signals
        
        safe_write_json(self.active_signals_file, active)
        
        if removed > 0:
            print(f"   Cleaned {removed} expired signals")

def main():
    print("[TRADE EXPIRATION] Signal timeout system active")
    print("[TRADE EXPIRATION] Signals expire after 2 hours or if structure breaks")
    
    expirer = TradeExpiration()
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking signal validity...")
            
            # Check latest risk output for new signals
            risk  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/dynamic_risk_output.json", {})
            
            for opp in risk.get("approved", [])[:3]:
                opp["timestamp"] = datetime.now().isoformat()
                is_valid, reason = expirer.check_expiration(opp)
                
                if is_valid:
                    print(f"   ✅ {opp['symbol']}: {reason}")
                else:
                    print(f"   ❌ {opp['symbol']}: {reason}")
            
            # Clean expired signals
            expirer.clean_expired_signals()
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(300)  # Every 5 minutes

if __name__ == "__main__":
    main()
