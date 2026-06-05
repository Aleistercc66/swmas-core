#!/usr/bin/env python3
"""
Opportunity Scanner - Εντοπισμός 15-30% ημερήσιων ευκαιριών
Συνδυάζει real-time data + ιστορικά patterns για να βρίσκει τα καλύτερα setups.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from learning_engine import SolanaKnowledgeBase
from historian import SolanaHistorian


@dataclass
class TradeSetup:
    """Πλήρες trade setup με entry, exit, risk management."""
    token_address: str
    symbol: str
    
    # Entry
    entry_price: float = 0.0
    entry_strategy: str = ""  # immediate, wait_pullback, breakout
    entry_confidence: float = 0.0
    
    # Targets
    target_return: float = 0.0  # 15-30%
    tp1: float = 0.0  # 40% of target
    tp2: float = 0.0  # 70% of target
    tp3: float = 0.0  # 100% of target
    
    # Risk
    stop_loss: float = 0.0  # -10% to -15%
    risk_reward: float = 0.0
    position_size_pct: float = 0.0  # % of portfolio
    
    # Context
    catalyst: str = ""  # momentum, volume_spike, new_launch, social_hype
    timeframe: str = "2-6h"  # Expected hold time
    urgency: str = "normal"  # urgent, normal, can_wait
    
    # Scores
    opportunity_score: float = 0.0
    risk_score: float = 0.0
    historical_similarity_score: float = 0.0
    
    # Metadata
    detected_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # When setup becomes invalid
    
    def to_alert_message(self) -> str:
        """Convert to Telegram alert message."""
        emoji = "🚀" if self.target_return >= 25 else "⚡" if self.target_return >= 15 else "📈"
        
        return f"""
{emoji} **SOLANA OPPORTUNITY: {self.symbol}** {emoji}

📊 **Setup:** {self.catalyst.upper()}
🎯 **Target:** +{self.target_return:.1f}%
⏱️ **Timeframe:** {self.timeframe}
🔥 **Confidence:** {self.opportunity_score:.0f}/100

💰 **Entry:** {self.entry_strategy}
   Price: ${self.entry_price:.6f}

🎯 **Targets:**
   TP1 (+{self.tp1:.1f}%) | TP2 (+{self.tp2:.1f}%) | TP3 (+{self.tp3:.1f}%)

🛑 **Stop Loss:** {self.stop_loss:.1f}%
⚖️ **R:R:** 1:{self.risk_reward:.1f}

📍 **Token:** `{self.token_address}`

⏰ **Valid until:** {datetime.fromtimestamp(self.expires_at).strftime('%H:%M') if self.expires_at else 'Unknown'}
"""


class OpportunityScanner:
    """
    Scanner που ψάχνει για 15-30% ημερήσιες ευκαιρίες.
    Συνδυάζει πολλαπλά signals για maximum accuracy.
    """
    
    def __init__(self, knowledge_base: SolanaKnowledgeBase, historian: SolanaHistorian):
        self.kb = knowledge_base
        self.historian = historian
        self.active_setups: List[TradeSetup] = []
        self.executed_setups: List[TradeSetup] = []
        self.rejected_setups: List[TradeSetup] = []
        
        # Scanning intervals
        self.scan_interval = 300  # 5 minutes
        self.opportunity_ttl = 3600  # 1 hour validity
        
        # Filters
        self.min_liquidity = 10000  # $10K
        self.max_risk_score = 75
        self.min_opportunity_score = 55
        
        # Strategy weights
        self.weights = {
            "momentum": 0.25,
            "volume": 0.20,
            "historical": 0.20,
            "market_cycle": 0.15,
            "timing": 0.10,
            "social": 0.10,
        }
    
    async def scan_for_opportunities(self) -> List[TradeSetup]:
        """Full scan for opportunities."""
        print(f"🔍 Scanning for 15-30% opportunities...")
        
        opportunities = []
        
        # 1. Get hot tokens from knowledge base
        hot_tokens = self.kb.get_hot_opportunities(
            min_score=self.min_opportunity_score,
            max_risk=self.max_risk_score
        )
        
        print(f"📊 Found {len(hot_tokens)} hot tokens")
        
        for token_data in hot_tokens[:10]:  # Analyze top 10
            setup = self._analyze_token_for_setup(token_data)
            if setup and setup.target_return >= 15:
                opportunities.append(setup)
                print(f"✅ Opportunity found: {setup.symbol} | +{setup.target_return:.1f}% | Score: {setup.opportunity_score:.0f}")
        
        # 2. Check for new Pump.fun launches
        # This is done in the learning engine, but we can specifically look for them
        
        # 3. Check for momentum breakouts
        momentum_opps = await self._scan_momentum_breakouts()
        opportunities.extend(momentum_opps)
        
        # Sort by score
        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        # Update active setups
        self.active_setups = [s for s in opportunities if s.expires_at > time.time()]
        
        print(f"🎯 Total opportunities: {len(opportunities)}")
        
        return opportunities
    
    def _analyze_token_for_setup(self, token_data: Dict) -> Optional[TradeSetup]:
        """Ανάλυση token για trade setup."""
        
        address = token_data.get("address", "")
        symbol = token_data.get("symbol", "UNKNOWN")
        price = token_data.get("price", 0)
        changes = token_data.get("changes", {})
        liquidity = token_data.get("liquidity", 0)
        volume_24h = token_data.get("volume_24h", 0)
        tags = token_data.get("tags", [])
        
        if price <= 0 or liquidity < self.min_liquidity:
            return None
        
        # Calculate momentum score
        m5 = changes.get("m5", 0)
        h1 = changes.get("h1", 0)
        h6 = changes.get("h6", 0)
        h24 = changes.get("h24", 0)
        
        momentum_score = self._calculate_momentum_score(m5, h1, h6, h24)
        
        # Calculate volume score
        volume_score = self._calculate_volume_score(volume_24h, liquidity)
        
        # Get historical context
        historical_score = 50.0
        moon_probability = 0.0
        
        if address in self.historian.token_profiles:
            profile = self.historian.token_profiles[address]
            historical_score = profile.max_return_from_launch / 100 if profile.max_return_from_launch > 0 else 50
            moon_probability = self.historian.calculate_moon_probability({
                "category": self._get_category_from_tags(tags),
                "launch_timestamp": time.time(),
            })
        else:
            # New token — use category prediction
            moon_probability = self.historian.calculate_moon_probability({
                "category": self._get_category_from_tags(tags),
                "launch_timestamp": time.time(),
            })
        
        # Market cycle score
        cycle_score = 50.0
        active_cycle = None
        for cycle in self.historian.market_cycles:
            if cycle.is_active():
                active_cycle = cycle
                break
        
        if active_cycle:
            if active_cycle.cycle_type == "bull":
                cycle_score = 80.0
            elif active_cycle.cycle_type == "bear":
                cycle_score = 30.0
        
        # Combined score
        opportunity_score = (
            momentum_score * self.weights["momentum"] +
            volume_score * self.weights["volume"] +
            historical_score * self.weights["historical"] +
            cycle_score * self.weights["market_cycle"] +
            50.0 * self.weights["timing"] +
            50.0 * self.weights["social"]
        )
        
        # Determine target return based on setup quality
        target_return = self._calculate_target_return(momentum_score, volume_score, moon_probability)
        
        if target_return < 15:
            return None
        
        # Build setup
        setup = TradeSetup(
            token_address=address,
            symbol=symbol,
            entry_price=price,
            entry_strategy=self._determine_entry_strategy(h1),
            entry_confidence=min(100, opportunity_score),
            target_return=target_return,
            tp1=target_return * 0.4,
            tp2=target_return * 0.7,
            tp3=target_return,
            stop_loss=-10.0,
            risk_reward=target_return / 10.0,
            position_size_pct=self._calculate_position_size(opportunity_score),
            catalyst=self._determine_catalyst(m5, h1, h6, volume_score),
            timeframe=self._estimate_timeframe(h1, h24),
            urgency="urgent" if momentum_score > 80 else "normal",
            opportunity_score=opportunity_score,
            risk_score=token_data.get("risk", 50),
            historical_similarity_score=historical_score,
            expires_at=time.time() + self.opportunity_ttl,
        )
        
        return setup
    
    def _calculate_momentum_score(self, m5: float, h1: float, h6: float, h24: float) -> float:
        """Υπολογισμός momentum score (0-100)."""
        score = 0.0
        
        # Recent momentum (most important)
        if m5 > 10:
            score += 25
        elif m5 > 5:
            score += 15
        elif m5 > 0:
            score += 5
        
        # 1h momentum
        if h1 > 20:
            score += 25
        elif h1 > 10:
            score += 20
        elif h1 > 5:
            score += 10
        
        # 6h momentum (sustained)
        if h6 > 50:
            score += 20
        elif h6 > 20:
            score += 15
        elif h6 > 10:
            score += 5
        
        # 24h context
        if h24 > 100:
            score += 15
        elif h24 > 50:
            score += 10
        elif h24 > 20:
            score += 5
        
        # Consistency bonus
        if h1 > 0 and h6 > h1 and h24 > h6:
            score += 10  # Consistent uptrend across timeframes
        
        return min(100, score)
    
    def _calculate_volume_score(self, volume_24h: float, liquidity: float) -> float:
        """Υπολογισμός volume score (0-100)."""
        if liquidity <= 0:
            return 0.0
        
        ratio = volume_24h / liquidity
        
        if ratio > 10:
            return 100
        elif ratio > 5:
            return 80
        elif ratio > 2:
            return 60
        elif ratio > 1:
            return 40
        elif ratio > 0.5:
            return 20
        else:
            return 10
    
    def _calculate_target_return(self, momentum_score: float, volume_score: float, 
                                  moon_probability: float) -> float:
        """Υπολογισμός ρεαλιστικού target return."""
        
        base = 10.0
        
        # Momentum contribution
        if momentum_score > 80:
            base += 15
        elif momentum_score > 60:
            base += 10
        elif momentum_score > 40:
            base += 5
        
        # Volume contribution
        if volume_score > 80:
            base += 10
        elif volume_score > 60:
            base += 5
        
        # Historical probability
        if moon_probability > 50:
            base += 10
        elif moon_probability > 30:
            base += 5
        
        # Cap at 30% for realistic daily targets
        return min(30, base)
    
    def _determine_entry_strategy(self, h1: float) -> str:
        """Καθορισμός entry strategy."""
        if h1 > 30:
            return "wait_pullback_5_10pct"
        elif h1 > 15:
            return "immediate_or_small_dip"
        elif h1 > 5:
            return "immediate"
        else:
            return "breakout_wait"
    
    def _calculate_position_size(self, opportunity_score: float) -> float:
        """Υπολογισμός position size (% of portfolio)."""
        # Higher confidence = larger position
        if opportunity_score > 80:
            return 10.0  # 10% of portfolio
        elif opportunity_score > 70:
            return 7.0
        elif opportunity_score > 60:
            return 5.0
        else:
            return 3.0
    
    def _determine_catalyst(self, m5: float, h1: float, h6: float, volume_score: float) -> str:
        """Καθορισμός catalyst type."""
        if m5 > 20 and h1 > 30:
            return "explosive_momentum"
        elif volume_score > 80:
            return "volume_breakout"
        elif h6 > 50 and h1 < 20:
            return "sustained_momentum"
        elif m5 > 10 and h1 > 10:
            return "early_momentum"
        else:
            return "momentum_continuation"
    
    def _estimate_timeframe(self, h1: float, h24: float) -> str:
        """Εκτίμηση χρόνου για target."""
        if h1 > 50:
            return "1-3h"
        elif h1 > 20:
            return "2-6h"
        elif h24 > 100:
            return "6-12h"
        else:
            return "12-24h"
    
    def _get_category_from_tags(self, tags: List[str]) -> str:
        """Extract category from tags."""
        if "meme" in tags or any(t in ["doge_theme", "cat_theme", "frog_theme"] for t in tags):
            return "meme"
        elif any(t in tags for t in ["defi", "dex", "yield"]):
            return "defi"
        elif any(t in tags for t in ["gaming", "game", "nft"]):
            return "gaming"
        else:
            return "unknown"
    
    async def _scan_momentum_breakouts(self) -> List[TradeSetup]:
        """Scan specifically for momentum breakout patterns."""
        breakouts = []
        
        # This would scan for specific breakout patterns
        # For now, using the main scanner results
        
        return breakouts
    
    def get_best_opportunity(self) -> Optional[TradeSetup]:
        """Get the highest-scoring current opportunity."""
        valid = [s for s in self.active_setups if s.expires_at > time.time()]
        if valid:
            return max(valid, key=lambda x: x.opportunity_score)
        return None
    
    def mark_setup_executed(self, setup: TradeSetup):
        """Mark a setup as executed."""
        setup.executed_at = time.time()
        self.executed_setups.append(setup)
        if setup in self.active_setups:
            self.active_setups.remove(setup)
    
    def update_setup_result(self, setup: TradeSetup, success: bool, actual_return: float):
        """Update setup with actual result for learning."""
        setup.actual_return = actual_return
        setup.success = success
        
        # Learn from result
        self.kb.learn_from_trade_result(
            setup.token_address,
            success,
            actual_return,
            setup.catalyst
        )
    
    async def continuous_scanning(self):
        """Continuous scanning loop."""
        print("🔍 Starting continuous opportunity scanning...")
        
        while True:
            try:
                opportunities = await self.scan_for_opportunities()
                
                # Log results
                if opportunities:
                    best = opportunities[0]
                    print(f"\n🎯 BEST OPPORTUNITY: {best.symbol}")
                    print(f"   Target: +{best.target_return:.1f}%")
                    print(f"   Score: {best.opportunity_score:.0f}/100")
                    print(f"   Strategy: {best.entry_strategy}")
                
                # Clean expired
                self.active_setups = [s for s in self.active_setups if s.expires_at > time.time()]
                
            except Exception as e:
                print(f"❌ Scan error: {e}")
            
            await asyncio.sleep(self.scan_interval)


if __name__ == "__main__":
    kb = SolanaKnowledgeBase()
    historian = SolanaHistorian()
    scanner = OpportunityScanner(kb, historian)
    
    try:
        asyncio.run(scanner.continuous_scanning())
    except KeyboardInterrupt:
        print("\n👋 Scanner stopped")
