import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import requests


@dataclass
class TokenKnowledge:
    """Γνώση για ένα συγκεκριμένο token."""
    address: str
    symbol: str
    name: str
    discovered_at: float = field(default_factory=time.time)
    price_history: List[Dict] = field(default_factory=list)
    volume_profile: Dict[str, float] = field(default_factory=dict)
    holder_count: int = 0
    liquidity_sources: List[str] = field(default_factory=list)
    social_signals: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0
    opportunity_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "address": self.address,
            "symbol": self.symbol,
            "name": self.name,
            "discovered_at": self.discovered_at,
            "price_history": self.price_history[-50:],  # Keep last 50
            "volume_profile": self.volume_profile,
            "holder_count": self.holder_count,
            "liquidity_sources": self.liquidity_sources,
            "social_signals": self.social_signals,
            "risk_score": self.risk_score,
            "opportunity_score": self.opportunity_score,
            "tags": self.tags,
        }


@dataclass
class StrategyPattern:
    """Pattern που μαθαίνει από επιτυχημένα trades."""
    name: str
    conditions: List[Dict]
    success_rate: float = 0.0
    avg_return: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    created_at: float = field(default_factory=time.time)
    last_used: Optional[float] = None
    
    def update_stats(self, won: bool, return_pct: float):
        self.total_trades += 1
        if won:
            self.winning_trades += 1
        # Update rolling average
        self.avg_return = (self.avg_return * (self.total_trades - 1) + return_pct) / self.total_trades
        self.success_rate = self.winning_trades / self.total_trades
        self.last_used = time.time()


class SolanaKnowledgeBase:
    """
    Βάση γνώσης για το Solana ecosystem.
    Μαθαίνει από DexScreener, Jupiter, Pump.fun, Raydium, Orca κλπ.
    """
    
    def __init__(self, storage_path: str = "solana_knowledge.json"):
        self.storage_path = storage_path
        self.tokens: Dict[str, TokenKnowledge] = {}
        self.patterns: List[StrategyPattern] = []
        self.market_conditions: Dict[str, Any] = {}
        self.hot_tokens: List[str] = []
        self.blacklisted_tokens: set = set()
        self.successful_strategies: List[Dict] = []
        
        # Solana-specific knowledge
        self.known_dexes = {
            "jupiter": "https://api.jup.ag/swap/v1",
            "raydium": "https://api.raydium.io/v2",
            "orca": "https://api.orca.so",
            "meteora": "https://api.meteora.ag",
        }
        
        self.known_launchpads = {
            "pump_fun": "https://pump.fun",
            "dexlab": "https://www.dexlab.space",
            "solanium": "https://www.solanium.io",
        }
        
        self.meme_categories = {
            "doge_theme": ["doge", "shib", "bonk", "floki"],
            "cat_theme": ["cat", "kitty", "meow", "popcat"],
            "frog_theme": ["pepe", "frog", "ribbit"],
            "ai_theme": ["ai", "gpt", "neural", "bot"],
            "political": ["trump", "maga", "biden", "elon"],
        }
        
        self.load_knowledge()
    
    def load_knowledge(self):
        """Φόρτωση αποθηκευμένης γνώσης."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                for addr, token_data in data.get("tokens", {}).items():
                    self.tokens[addr] = TokenKnowledge(**token_data)
                self.patterns = [StrategyPattern(**p) for p in data.get("patterns", [])]
                self.successful_strategies = data.get("successful_strategies", [])
                self.blacklisted_tokens = set(data.get("blacklisted", []))
                print(f"📚 Loaded {len(self.tokens)} tokens, {len(self.patterns)} patterns")
        except FileNotFoundError:
            print("📚 New knowledge base created")
    
    def save_knowledge(self):
        """Αποθήκευση γνώσης."""
        data = {
            "tokens": {addr: t.to_dict() for addr, t in self.tokens.items()},
            "patterns": [self._pattern_to_dict(p) for p in self.patterns],
            "successful_strategies": self.successful_strategies,
            "blacklisted": list(self.blacklisted_tokens),
            "saved_at": time.time(),
        }
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _pattern_to_dict(self, p: StrategyPattern) -> Dict:
        return {
            "name": p.name,
            "conditions": p.conditions,
            "success_rate": p.success_rate,
            "avg_return": p.avg_return,
            "total_trades": p.total_trades,
            "winning_trades": p.winning_trades,
            "created_at": p.created_at,
            "last_used": p.last_used,
        }
    
    async def learn_from_dexscreener(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Μάθηση από DexScreener API."""
        opportunities = []
        
        try:
            # Get trending Solana tokens
            async with session.get(
                "https://api.dexscreener.com/token-boosts/top/v1",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    boosts = data if isinstance(data, list) else data.get("boosts", [])
                    
                    for boost in boosts[:20]:
                        token_address = boost.get("tokenAddress", "")
                        chain = boost.get("chainId", "")
                        
                        if chain == "solana" and token_address:
                            # Get detailed pair data
                            pair_data = await self._fetch_pair_data(session, token_address)
                            if pair_data:
                                await self._process_token_data(token_address, pair_data)
                                
                                # Check if it's an opportunity
                                opp = self._evaluate_opportunity(token_address, pair_data)
                                if opp:
                                    opportunities.append(opp)
        except Exception as e:
            print(f"❌ DexScreener learning error: {e}")
        
        return opportunities
    
    async def _fetch_pair_data(self, session: aiohttp.ClientSession, token_address: str) -> Optional[Dict]:
        """Fetch detailed pair data for a token."""
        try:
            async with session.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_address}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        # Get best pair (highest liquidity)
                        best_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
                        return best_pair
        except Exception as e:
            print(f"❌ Pair data error for {token_address}: {e}")
        return None
    
    async def _process_token_data(self, address: str, pair_data: Dict):
        """Process and store token data."""
        base_token = pair_data.get("baseToken", {})
        symbol = base_token.get("symbol", "UNKNOWN")
        name = base_token.get("name", symbol)
        
        if address not in self.tokens:
            self.tokens[address] = TokenKnowledge(
                address=address,
                symbol=symbol,
                name=name,
            )
        
        token = self.tokens[address]
        
        # Update price history
        price = float(pair_data.get("priceUsd", 0) or 0)
        volume_24h = float(pair_data.get("volume", {}).get("h24", 0) or 0)
        liquidity = float(pair_data.get("liquidity", {}).get("usd", 0) or 0)
        price_change = {
            "m5": float(pair_data.get("priceChange", {}).get("m5", 0) or 0),
            "h1": float(pair_data.get("priceChange", {}).get("h1", 0) or 0),
            "h6": float(pair_data.get("priceChange", {}).get("h6", 0) or 0),
            "h24": float(pair_data.get("priceChange", {}).get("h24", 0) or 0),
        }
        
        token.price_history.append({
            "timestamp": time.time(),
            "price": price,
            "volume_24h": volume_24h,
            "liquidity": liquidity,
            "changes": price_change,
        })
        
        # Keep only last 100 entries
        if len(token.price_history) > 100:
            token.price_history = token.price_history[-100:]
        
        # Update volume profile
        token.volume_profile = {
            "m5": float(pair_data.get("volume", {}).get("m5", 0) or 0),
            "h1": float(pair_data.get("volume", {}).get("h1", 0) or 0),
            "h6": float(pair_data.get("volume", {}).get("h6", 0) or 0),
            "h24": volume_24h,
        }
        
        # Update liquidity sources
        dex_id = pair_data.get("dexId", "")
        if dex_id and dex_id not in token.liquidity_sources:
            token.liquidity_sources.append(dex_id)
        
        # Calculate risk score
        token.risk_score = self._calculate_risk(token, pair_data)
        
        # Tag token
        token.tags = self._tag_token(symbol, name, pair_data)
        
        # Update opportunity score
        token.opportunity_score = self._calculate_opportunity_score(token)
    
    def _calculate_risk(self, token: TokenKnowledge, pair_data: Dict) -> float:
        """Calculate risk score (0-100, lower is better)."""
        risk = 50.0  # Base risk
        
        # Liquidity risk
        liquidity = float(pair_data.get("liquidity", {}).get("usd", 0) or 0)
        if liquidity < 10000:
            risk += 30
        elif liquidity < 50000:
            risk += 15
        elif liquidity > 200000:
            risk -= 10
        
        # Volume risk
        volume_24h = float(pair_data.get("volume", {}).get("h24", 0) or 0)
        if volume_24h < 5000:
            risk += 20
        elif volume_24h > 100000:
            risk -= 10
        
        # Price stability
        changes = pair_data.get("priceChange", {})
        h24_change = abs(float(changes.get("h24", 0) or 0))
        if h24_change > 1000:  # >1000% change
            risk += 20
        elif h24_change > 500:
            risk += 10
        
        # Holder count (if available)
        if token.holder_count > 0:
            if token.holder_count < 100:
                risk += 15
            elif token.holder_count > 1000:
                risk -= 10
        
        # Age factor
        age_hours = (time.time() - token.discovered_at) / 3600
        if age_hours < 1:
            risk += 15  # Very new
        elif age_hours > 24:
            risk -= 5  # Survived a day
        
        return max(0, min(100, risk))
    
    def _tag_token(self, symbol: str, name: str, pair_data: Dict) -> List[str]:
        """Tag token with categories."""
        tags = []
        text = f"{symbol} {name}".lower()
        
        # Meme categories
        for category, keywords in self.meme_categories.items():
            if any(kw in text for kw in keywords):
                tags.append(category)
        
        # Market cap category
        market_cap = float(pair_data.get("marketCap", 0) or 0)
        if market_cap > 0:
            if market_cap < 100000:
                tags.append("micro_cap")
            elif market_cap < 1000000:
                tags.append("small_cap")
            elif market_cap < 10000000:
                tags.append("mid_cap")
            else:
                tags.append("large_cap")
        
        # Volume category
        volume_24h = float(pair_data.get("volume", {}).get("h24", 0) or 0)
        if volume_24h > 500000:
            tags.append("high_volume")
        elif volume_24h > 50000:
            tags.append("medium_volume")
        
        # Momentum
        changes = pair_data.get("priceChange", {})
        h24 = float(changes.get("h24", 0) or 0)
        if h24 > 50:
            tags.append("strong_momentum")
        elif h24 > 20:
            tags.append("momentum")
        elif h24 < -50:
            tags.append("crashing")
        
        return tags
    
    def _calculate_opportunity_score(self, token: TokenKnowledge) -> float:
        """Calculate opportunity score (0-100)."""
        score = 50.0
        
        # Momentum bonus
        if token.price_history:
            latest = token.price_history[-1]
            changes = latest.get("changes", {})
            
            # Multi-timeframe momentum
            if changes.get("m5", 0) > 5:
                score += 10
            if changes.get("h1", 0) > 10:
                score += 15
            if changes.get("h6", 0) > 20:
                score += 20
            if changes.get("h24", 0) > 50:
                score += 25
            
            # Volume/liquidity ratio
            volume = latest.get("volume_24h", 0)
            liquidity = latest.get("liquidity", 1)
            if liquidity > 0:
                ratio = volume / liquidity
                if ratio > 5:
                    score += 15
                elif ratio > 2:
                    score += 10
            
            # Price action consistency
            if len(token.price_history) >= 3:
                recent = token.price_history[-3:]
                prices = [p["price"] for p in recent]
                if prices[0] < prices[1] < prices[2]:
                    score += 10  # Consistent uptrend
        
        # Risk penalty
        score -= (token.risk_score * 0.3)
        
        # Tag bonuses
        if "strong_momentum" in token.tags:
            score += 10
        if "high_volume" in token.tags:
            score += 5
        if "micro_cap" in token.tags:
            score += 5  # Higher upside potential
        
        return max(0, min(100, score))
    
    def _evaluate_opportunity(self, address: str, pair_data: Dict) -> Optional[Dict]:
        """Evaluate if this is a 15-30% opportunity."""
        token = self.tokens.get(address)
        if not token:
            return None
        
        if token.opportunity_score < 60:
            return None
        
        if token.risk_score > 70:
            return None  # Too risky
        
        changes = pair_data.get("priceChange", {})
        h24 = float(changes.get("h24", 0) or 0)
        h6 = float(changes.get("h6", 0) or 0)
        h1 = float(changes.get("h1", 0) or 0)
        m5 = float(changes.get("m5", 0) or 0)
        
        # Look for 15-30% daily potential
        potential = 0
        
        # Case 1: Already moving with momentum
        if h1 > 10 and h6 > 15:
            potential = min(h24 * 0.5, 30)  # Conservative estimate
        
        # Case 2: Early breakout
        elif m5 > 5 and h1 > 8 and h6 < 20:
            potential = 20  # Early stage
        
        # Case 3: High volume + low market cap
        volume = float(pair_data.get("volume", {}).get("h24", 0) or 0)
        market_cap = float(pair_data.get("marketCap", 0) or 0)
        if market_cap > 0 and volume / market_cap > 0.5 and market_cap < 1000000:
            potential = 25  # Micro cap with volume
        
        if potential >= 15:
            return {
                "token": token,
                "address": address,
                "symbol": token.symbol,
                "potential_return": potential,
                "entry_strategy": self._determine_entry_strategy(token, pair_data),
                "exit_strategy": self._determine_exit_strategy(potential),
                "risk_score": token.risk_score,
                "opportunity_score": token.opportunity_score,
                "timestamp": time.time(),
            }
        
        return None
    
    def _determine_entry_strategy(self, token: TokenKnowledge, pair_data: Dict) -> Dict:
        """Determine best entry strategy."""
        changes = pair_data.get("priceChange", {})
        h1 = float(changes.get("h1", 0) or 0)
        
        if h1 > 20:
            return {
                "type": "wait_pullback",
                "reason": "Already up >20% in 1h, wait for pullback",
                "target_entry": "5-10% pullback from current",
            }
        elif h1 > 10:
            return {
                "type": "immediate",
                "reason": "Strong momentum, enter now",
                "target_entry": "Current price",
            }
        else:
            return {
                "type": "breakout",
                "reason": "Wait for breakout confirmation",
                "target_entry": "Above recent high",
            }
    
    def _determine_exit_strategy(self, potential: float) -> Dict:
        """Determine exit targets."""
        return {
            "tp1": potential * 0.4,  # Take 40% at first target
            "tp2": potential * 0.7,  # Take 30% at second target
            "tp3": potential,  # Let 30% run
            "stop_loss": -10,  # Tight stop
            "trailing_stop": True,
            "time_limit": "2-4 hours",  # Quick trades
        }
    
    async def learn_from_jupiter(self, session: aiohttp.ClientSession):
        """Learn from Jupiter aggregator data."""
        try:
            # Get trending tokens
            async with session.get(
                "https://station.jup.ag/docs/token-list-api",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Process trending tokens
                    print(f"🪐 Learned from Jupiter: {len(data)} tokens")
        except Exception as e:
            print(f"❌ Jupiter learning error: {e}")
    
    async def learn_from_pumpfun(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Learn from Pump.fun launches."""
        new_launches = []
        
        try:
            # Pump.fun has a public API for recent launches
            async with session.get(
                "https://frontend-api.pump.fun/coins/for-you",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    coins = data if isinstance(data, list) else []
                    
                    for coin in coins[:10]:
                        address = coin.get("mint", "")
                        if address and address not in self.tokens:
                            # New launch!
                            token = TokenKnowledge(
                                address=address,
                                symbol=coin.get("symbol", "UNKNOWN"),
                                name=coin.get("name", ""),
                                tags=["pump_fun", "new_launch"],
                            )
                            self.tokens[address] = token
                            new_launches.append({
                                "address": address,
                                "symbol": token.symbol,
                                "market_cap": coin.get("market_cap", 0),
                                "usd_market_cap": coin.get("usd_market_cap", 0),
                            })
                    
                    print(f"🚀 Learned {len(new_launches)} new Pump.fun launches")
        except Exception as e:
            print(f"❌ Pump.fun learning error: {e}")
        
        return new_launches
    
    async def continuous_learning_loop(self, interval: int = 300):
        """Continuous learning loop."""
        print("🧠 Starting continuous learning loop...")
        
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    print(f"\n📚 Learning cycle at {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Learn from multiple sources
                    dex_opps = await self.learn_from_dexscreener(session)
                    pump_launches = await self.learn_from_pumpfun(session)
                    # await self.learn_from_jupiter(session)
                    
                    # Save knowledge
                    self.save_knowledge()
                    
                    # Update hot tokens
                    self.hot_tokens = sorted(
                        self.tokens.keys(),
                        key=lambda x: self.tokens[x].opportunity_score,
                        reverse=True
                    )[:20]
                    
                    print(f"✅ Knowledge saved: {len(self.tokens)} tokens, {len(dex_opps)} opportunities")
                    
                except Exception as e:
                    print(f"❌ Learning loop error: {e}")
                
                await asyncio.sleep(interval)
    
    def get_hot_opportunities(self, min_score: float = 60, max_risk: float = 70) -> List[Dict]:
        """Get current hot opportunities."""
        opportunities = []
        
        for addr in self.hot_tokens:
            token = self.tokens[addr]
            if token.opportunity_score >= min_score and token.risk_score <= max_risk:
                if token.price_history:
                    latest = token.price_history[-1]
                    opportunities.append({
                        "address": addr,
                        "symbol": token.symbol,
                        "score": token.opportunity_score,
                        "risk": token.risk_score,
                        "price": latest.get("price", 0),
                        "volume_24h": latest.get("volume_24h", 0),
                        "liquidity": latest.get("liquidity", 0),
                        "changes": latest.get("changes", {}),
                        "tags": token.tags,
                    })
        
        return sorted(opportunities, key=lambda x: x["score"], reverse=True)
    
    def learn_from_trade_result(self, token_address: str, success: bool, return_pct: float, strategy: str):
        """Learn from trade outcomes to improve patterns."""
        # Find or create pattern for this strategy
        pattern = None
        for p in self.patterns:
            if p.name == strategy:
                pattern = p
                break
        
        if not pattern:
            pattern = StrategyPattern(
                name=strategy,
                conditions=[],
            )
            self.patterns.append(pattern)
        
        pattern.update_stats(success, return_pct)
        
        # Record successful strategy
        if success and return_pct >= 15:
            self.successful_strategies.append({
                "token": token_address,
                "return": return_pct,
                "strategy": strategy,
                "timestamp": time.time(),
            })
        
        self.save_knowledge()


if __name__ == "__main__":
    kb = SolanaKnowledgeBase()
    try:
        asyncio.run(kb.continuous_learning_loop(interval=60))
    except KeyboardInterrupt:
        print("\n👋 Learning stopped")
        kb.save_knowledge()
