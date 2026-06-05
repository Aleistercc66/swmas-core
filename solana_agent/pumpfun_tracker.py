#!/usr/bin/env python3
"""
Pump.fun Bonding Curve Tracker
Παρακολουθεί το bonding curve progress και προβλέπει graduation time.
Ξέρει πότε ένα token φεύγει από Pump.fun και πάει Raydium/PumpSwap.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class BondingCurveState:
    """Κατάσταση bonding curve."""
    token_address: str
    symbol: str
    
    # Curve progress
    market_cap: float = 0.0
    liquidity_sol: float = 0.0
    bonding_curve_progress: float = 0.0  # 0-100%
    
    # Graduation threshold
    graduation_market_cap: float = 13000  # ~$13K for Pump.fun
    
    # Metrics
    holder_count: int = 0
    buy_count: int = 0
    sell_count: int = 0
    volume_5min: float = 0.0
    
    # Prediction
    estimated_graduation_time: Optional[float] = None
    graduation_probability: float = 0.0
    
    # Status
    is_graduated: bool = False
    graduated_at: Optional[float] = None
    migrated_to: str = ""  # raydium / pumpswap / unknown
    
    last_update: float = field(default_factory=time.time)


class PumpFunTracker:
    """
    Tracker για Pump.fun bonding curves.
    Προβλέπει graduation και παρακολουθεί token lifecycle.
    """
    
    def __init__(self):
        self.curves: Dict[str, BondingCurveState] = {}
        self.graduated_tokens: List[str] = []
        self.pump_fun_api = "https://frontend-api.pump.fun"
        self.pump_portal_ws = "wss://pumpportal.fun/api/data"
        
        # Graduation thresholds
        self.graduation_threshold = 13000  # $13K market cap
        self.high_confidence_threshold = 10000  # $10K = 77% progress
        
        # Predictive model weights
        self.velocity_weight = 0.4
        self.volume_weight = 0.3
        self.holder_weight = 0.3
    
    async def fetch_curve_data(self, session: aiohttp.ClientSession,
                                token_address: str) -> Optional[BondingCurveState]:
        """Fetch bonding curve data από Pump.fun API."""
        try:
            async with session.get(
                f"{self.pump_fun_api}/coins/{token_address}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    curve = BondingCurveState(
                        token_address=token_address,
                        symbol=data.get("symbol", "UNKNOWN"),
                        market_cap=data.get("usd_market_cap", 0),
                        liquidity_sol=data.get("liquidity_sol", 0),
                        holder_count=data.get("holder_count", 0),
                        buy_count=data.get("buy_count", 0),
                        sell_count=data.get("sell_count", 0),
                    )
                    
                    # Calculate progress
                    if curve.market_cap > 0:
                        curve.bonding_curve_progress = min(100, 
                            (curve.market_cap / self.graduation_threshold) * 100)
                    
                    # Check if graduated
                    if data.get("is_graduated", False):
                        curve.is_graduated = True
                        curve.graduated_at = time.time()
                        curve.migrated_to = data.get("migrated_to", "pumpswap")
                    
                    return curve
                    
        except Exception as e:
            print(f"❌ Pump.fun fetch error: {e}")
        
        return None
    
    def predict_graduation(self, curve: BondingCurveState,
                          price_history: List[Dict]) -> Dict:
        """Πρόβλεψη graduation time."""
        
        if curve.is_graduated:
            return {"graduated": True, "time": curve.graduated_at}
        
        if curve.market_cap >= self.graduation_threshold:
            return {"graduated": True, "time": time.time()}
        
        if not price_history or len(price_history) < 2:
            return {"estimated_minutes": None, "confidence": 0}
        
        # Calculate velocity (market cap growth per minute)
        recent = price_history[-10:]  # Last 10 data points
        if len(recent) < 2:
            return {"estimated_minutes": None, "confidence": 0}
        
        first_mc = recent[0].get("market_cap", curve.market_cap)
        last_mc = recent[-1].get("market_cap", curve.market_cap)
        time_span_minutes = (recent[-1].get("timestamp", time.time()) - 
                            recent[0].get("timestamp", time.time())) / 60
        
        if time_span_minutes <= 0:
            return {"estimated_minutes": None, "confidence": 0}
        
        velocity = (last_mc - first_mc) / time_span_minutes  # $ per minute
        
        if velocity <= 0:
            return {"estimated_minutes": None, "confidence": 0, "stalled": True}
        
        remaining = self.graduation_threshold - curve.market_cap
        estimated_minutes = remaining / velocity
        
        # Confidence based on consistency
        if estimated_minutes < 5:
            confidence = 0.9
        elif estimated_minutes < 15:
            confidence = 0.7
        elif estimated_minutes < 30:
            confidence = 0.5
        else:
            confidence = 0.3
        
        # Adjust for holder velocity
        holder_factor = min(1.0, curve.holder_count / 100)
        confidence *= (0.5 + 0.5 * holder_factor)
        
        return {
            "estimated_minutes": estimated_minutes,
            "velocity_per_min": velocity,
            "confidence": confidence,
            "current_progress": curve.bonding_curve_progress,
        }
    
    def get_graduation_opportunity(self, curve: BondingCurveState) -> Optional[Dict]:
        """
        Δημιουργία opportunity από graduation prediction.
        Όταν ένα token πλησιάζει graduation, υπάρχει high probability momentum.
        """
        if curve.is_graduated:
            return None
        
        progress = curve.bonding_curve_progress
        
        if progress < 60:
            return None  # Too early
        
        # Calculate opportunity score based on progress
        if progress >= 90:
            urgency = "CRITICAL"
            score = 95
            target = 30  # 30% potential on graduation pump
        elif progress >= 80:
            urgency = "HIGH"
            score = 80
            target = 25
        elif progress >= 70:
            urgency = "MEDIUM"
            score = 65
            target = 20
        else:
            urgency = "LOW"
            score = 50
            target = 15
        
        return {
            "type": "graduation_proximity",
            "token": curve.symbol,
            "address": curve.token_address,
            "progress_pct": progress,
            "market_cap": curve.market_cap,
            "urgency": urgency,
            "opportunity_score": score,
            "target_return": target,
            "reason": f"Token at {progress:.1f}% of bonding curve. Graduation imminent!",
            "estimated_time_to_graduation": self.predict_graduation(curve, []),
        }
    
    async def monitor_all_curves(self, session: aiohttp.ClientSession,
                                token_addresses: List[str]) -> List[Dict]:
        """Monitor multiple curves και βρες opportunities."""
        opportunities = []
        
        for address in token_addresses:
            curve = await self.fetch_curve_data(session, address)
            if curve:
                self.curves[address] = curve
                
                # Check for graduation opportunity
                opp = self.get_graduation_opportunity(curve)
                if opp:
                    opportunities.append(opp)
                
                # Check if just graduated
                if curve.is_graduated and address not in self.graduated_tokens:
                    self.graduated_tokens.append(address)
                    print(f"🎓 GRADUATED: {curve.symbol} migrated to {curve.migrated_to}")
        
        return opportunities
    
    def get_pre_graduation_setups(self) -> List[Dict]:
        """Get all tokens close to graduation."""
        setups = []
        
        for curve in self.curves.values():
            if not curve.is_graduated and curve.bonding_curve_progress >= 70:
                setups.append({
                    "symbol": curve.symbol,
                    "address": curve.token_address,
                    "progress": curve.bonding_curve_progress,
                    "market_cap": curve.market_cap,
                    "holders": curve.holder_count,
                })
        
        return sorted(setups, key=lambda x: x["progress"], reverse=True)


if __name__ == "__main__":
    tracker = PumpFunTracker()
    print("🎯 Pump.fun Bonding Curve Tracker initialized")
    print(f"   Graduation threshold: ${tracker.graduation_threshold:,.0f}")
