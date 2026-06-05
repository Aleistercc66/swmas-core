#!/usr/bin/env python3
"""
📐 DYNAMIC POSITION SIZING ENGINE
Calculates position size based on volatility, confidence, regime, and exposure.
"""
import json
import time
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agents')
from file_lock import safe_read_json, safe_write_json

class PositionSizer:
    def __init__(self, portfolio_balance=10000.0):
        self.balance = portfolio_balance
        self.exposure_file = "/root/.openclaw/workspace/agents/logs/portfolio_state.json"
        self.load_exposure()
    
    def load_exposure(self):
        try:
            with open(self.exposure_file, "r") as f:
                state = json.load(f)
                self.current_exposure = state.get("total_exposure", 0)
        except:
            self.current_exposure = 0
    
    def calculate_size(self, signal, regime_data=None, circuit_state="NORMAL"):
        """
        Calculate position size based on:
        - Kelly criterion (simplified)
        - Volatility (ATR)
        - Confidence score
        - Market regime
        - Current portfolio exposure
        - Circuit breaker state
        """
        
        symbol = signal.get("symbol", "???")
        entry = signal["entry_zone"]["primary"]
        stop = signal["stop_loss"]
        atr = signal.get("atr_proxy", 1.0)
        confidence = signal.get("confidence", 60)
        rr = signal.get("risk_reward_ratio", 2.0)
        
        # Base risk percentage (Kelly simplified)
        # Kelly % = (Win% × AvgWin - Loss% × AvgLoss) / AvgWin
        # Simplified: Use confidence as win probability proxy
        win_prob = confidence / 100
        base_risk = win_prob * (rr / (rr + 1)) * 2  # Simplified Kelly
        
        # Clamp base risk
        base_risk = max(0.5, min(base_risk, 3.0))  # 0.5% to 3%
        
        # Volatility adjustment
        # High ATR = smaller position
        if atr > 10:
            vol_mult = 0.3
        elif atr > 5:
            vol_mult = 0.5
        elif atr > 2:
            vol_mult = 0.7
        else:
            vol_mult = 1.0
        
        # Confidence adjustment
        if confidence >= 80:
            conf_mult = 1.5
        elif confidence >= 70:
            conf_mult = 1.2
        elif confidence >= 60:
            conf_mult = 1.0
        else:
            conf_mult = 0.5
        
        # Regime adjustment
        regime_mult = 1.0
        if regime_data:
            regime = regime_data.get("overall", "UNKNOWN")
            if regime == "BULLISH_TREND":
                regime_mult = 1.2
            elif regime == "BEARISH_TREND":
                regime_mult = 0.3
            elif regime == "RANGING":
                regime_mult = 0.8
            elif regime in ["PANIC", "EUPHORIC", "HIGH_VOLATILITY"]:
                regime_mult = 0.4
        
        # Circuit breaker adjustment
        circuit_mult = 1.0
        if circuit_state == "WARNING":
            circuit_mult = 0.5
        elif circuit_state == "COOLDOWN":
            circuit_mult = 0.0  # No trades
        elif circuit_state == "EMERGENCY":
            circuit_mult = 0.0  # No trades
        
        # Exposure limit check
        max_exposure = 50  # 50% of portfolio max
        remaining_exposure = max_exposure - self.current_exposure
        if remaining_exposure <= 0:
            return 0, "MAX_EXPOSURE_REACHED"
        
        # Final calculation
        risk_pct = base_risk * vol_mult * conf_mult * regime_mult * circuit_mult
        risk_pct = min(risk_pct, remaining_exposure)  # Don't exceed max exposure
        risk_pct = max(risk_pct, 0.5)  # Minimum 0.5%
        
        # Position size in USD
        stop_distance = abs(entry - stop) / entry if entry > 0 else 0
        if stop_distance == 0:
            return 0, "INVALID_STOP"
        
        position_usd = (self.balance * (risk_pct / 100)) / stop_distance
        position_usd = min(position_usd, self.balance * (remaining_exposure / 100))
        
        return position_usd, {
            "risk_pct": round(risk_pct, 2),
            "base_risk": round(base_risk, 2),
            "vol_mult": vol_mult,
            "conf_mult": conf_mult,
            "regime_mult": regime_mult,
            "circuit_mult": circuit_mult,
            "stop_distance": round(stop_distance * 100, 1),
        }

def main():
    print("[POSITION SIZER] Dynamic sizing engine active")
    print("[POSITION SIZER] Factors: volatility, confidence, regime, exposure")
    
    sizer = PositionSizer()
    
    while True:
        try:
            # Load latest risk output
            risk  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/dynamic_risk_output.json", {})
            
            # Load regime
            regime_data = None
            try:
                regime_data  = safe_read_json("/root/.openclaw/workspace/agents/tmp_state/regime_output.json", {})
            except:
                pass
            
            # Load circuit breaker state
            circuit_state = "NORMAL"
            cb = safe_read_json("/root/.openclaw/workspace/agents/logs/circuit_breaker.json", {})
            circuit_state = cb.get("state", "NORMAL")
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Position Sizing:")
            print(f"   Balance: ${sizer.balance:.2f} | Exposure: {sizer.current_exposure:.1f}%")
            print(f"   Circuit: {circuit_state} | Regime: {regime_data.get('overall', 'UNKNOWN') if regime_data else 'UNKNOWN'}")
            
            for opp in risk.get("approved", [])[:3]:
                size, meta = sizer.calculate_size(opp, regime_data, circuit_state)
                if size > 0:
                    print(f"\n   🎯 {opp['symbol']}:")
                    print(f"      Size: ${size:.2f} USDT")
                    print(f"      Risk: {meta['risk_pct']}% (base: {meta['base_risk']}%)")
                    print(f"      Factors: vol×{meta['vol_mult']} conf×{meta['conf_mult']} regime×{meta['regime_mult']} circuit×{meta['circuit_mult']}")
                else:
                    print(f"   ❌ {opp['symbol']}: {meta}")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(900)  # Every 15 minutes

if __name__ == "__main__":
    main()
