"""
Blockchain Master Data Analyzer
On-chain analysis, whale tracking, and market intelligence
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

@dataclass
class TokenMetrics:
    symbol: str
    address: str
    price: float
    market_cap: float
    liquidity: float
    volume_24h: float
    volume_7d: float
    holders: int
    holder_growth_24h: float
    top_holder_concentration: float  # % held by top 10
    smart_money_inflows: float
    smart_money_outflows: float
    whale_transactions_24h: int
    developer_activity: float
    social_sentiment: float
    contract_risk_score: float  # 0-100
    
@dataclass
class WhaleMovement:
    timestamp: datetime
    token_address: str
    from_address: str
    to_address: str
    amount: float
    amount_usd: float
    tx_hash: str
    movement_type: str  # 'accumulate', 'distribute', 'transfer'

class BlockchainAnalyzer:
    """Master on-chain analysis engine"""
    
    def __init__(self):
        self.solana_rpc = "https://api.mainnet-beta.solana.com"
        self.helius_api = None  # Will be set from env
        self.birdeye_api = "https://public-api.birdeye.so"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Data storage
        self.token_cache: Dict[str, TokenMetrics] = {}
        self.whale_movements: List[WhaleMovement] = []
        self.smart_money_wallets: set = set()
        self.known_whale_wallets: set = set()
        
        # Analysis state
        self.last_scan = None
        self.scan_interval = 300  # 5 minutes
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def analyze_token(self, token_address: str) -> TokenMetrics:
        """Deep on-chain token analysis"""
        
        # Fetch from multiple sources for accuracy
        birdeye_data = await self._fetch_birdeye(token_address)
        helius_data = await self._fetch_helius(token_address)
        
        # Calculate holder concentration
        holders = await self._get_token_holders(token_address)
        top_holders = await self._get_top_holders(token_address, 10)
        total_supply = sum(h['amount'] for h in holders)
        top_10_amount = sum(h['amount'] for h in top_holders)
        concentration = (top_10_amount / total_supply * 100) if total_supply > 0 else 100
        
        # Smart money tracking
        smart_in, smart_out = await self._analyze_smart_money_flows(token_address)
        
        # Whale transactions
        whale_txs = await self._count_whale_transactions(token_address, 24)
        
        # Contract risk analysis
        risk_score = await self._analyze_contract_risk(token_address)
        
        metrics = TokenMetrics(
            symbol=birdeye_data.get('symbol', 'UNKNOWN'),
            address=token_address,
            price=birdeye_data.get('price', 0),
            market_cap=birdeye_data.get('marketCap', 0),
            liquidity=birdeye_data.get('liquidity', 0),
            volume_24h=birdeye_data.get('v24hUSD', 0),
            volume_7d=birdeye_data.get('v7dUSD', 0),
            holders=len(holders),
            holder_growth_24h=await self._calculate_holder_growth(token_address),
            top_holder_concentration=concentration,
            smart_money_inflows=smart_in,
            smart_money_outflows=smart_out,
            whale_transactions_24h=whale_txs,
            developer_activity=await self._check_developer_activity(token_address),
            social_sentiment=await self._get_social_sentiment(token_address),
            contract_risk_score=risk_score
        )
        
        self.token_cache[token_address] = metrics
        return metrics
    
    async def _fetch_birdeye(self, token_address: str) -> Dict:
        """Fetch token data from Birdeye"""
        try:
            headers = {"X-API-KEY": "public"}  # Replace with actual API key
            url = f"{self.birdeye_api}/public/v1/token/meta?address={token_address}"
            
            async with self.session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('data', {})
                return {}
        except Exception as e:
            print(f"Birdeye error: {e}")
            return {}
    
    async def _fetch_helius(self, token_address: str) -> Dict:
        """Fetch token data from Helius"""
        try:
            if not self.helius_api:
                return {}
                
            headers = {"Authorization": f"Bearer {self.helius_api}"}
            url = f"https://mainnet.helius-rpc.com/?api-key={self.helius_api}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAsset",
                "params": {"id": token_address}
            }
            
            async with self.session.post(url, json=payload, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('result', {})
                return {}
        except Exception as e:
            print(f"Helius error: {e}")
            return {}
    
    async def _get_token_holders(self, token_address: str) -> List[Dict]:
        """Get all token holders"""
        try:
            url = f"{self.birdeye_api}/public/v1/token/holders?address={token_address}"
            headers = {"X-API-KEY": "public"}
            
            async with self.session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('data', {}).get('items', [])
                return []
        except:
            return []
    
    async def _get_top_holders(self, token_address: str, n: int) -> List[Dict]:
        """Get top N token holders"""
        holders = await self._get_token_holders(token_address)
        return sorted(holders, key=lambda x: x.get('amount', 0), reverse=True)[:n]
    
    async def _analyze_smart_money_flows(self, token_address: str) -> tuple:
        """Analyze smart money inflows/outflows"""
        inflows = 0
        outflows = 0
        
        # Fetch recent large transactions
        transactions = await self._get_recent_transactions(token_address, hours=24)
        
        for tx in transactions:
            if tx['from_address'] in self.smart_money_wallets:
                outflows += tx['amount_usd']
            if tx['to_address'] in self.smart_money_wallets:
                inflows += tx['amount_usd']
        
        return inflows, outflows
    
    async def _get_recent_transactions(self, token_address: str, hours: int) -> List[Dict]:
        """Get recent transactions for a token"""
        try:
            # Use Helius or Solscan for transaction history
            url = f"https://public-api.solscan.io/token/transactions"
            params = {
                "address": token_address,
                "limit": 100,
                "offset": 0
            }
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('data', [])
                return []
        except:
            return []
    
    async def _count_whale_transactions(self, token_address: str, hours: int) -> int:
        """Count whale transactions in last N hours"""
        transactions = await self._get_recent_transactions(token_address, hours)
        whale_threshold = 50000  # $50k
        
        count = 0
        for tx in transactions:
            if tx.get('amount_usd', 0) >= whale_threshold:
                count += 1
                
                # Add to whale movements
                movement = WhaleMovement(
                    timestamp=datetime.now(),
                    token_address=token_address,
                    from_address=tx.get('from', ''),
                    to_address=tx.get('to', ''),
                    amount=tx.get('amount', 0),
                    amount_usd=tx.get('amount_usd', 0),
                    tx_hash=tx.get('tx_hash', ''),
                    movement_type=self._classify_movement(tx)
                )
                self.whale_movements.append(movement)
        
        return count
    
    def _classify_movement(self, tx: Dict) -> str:
        """Classify whale movement type"""
        if tx.get('to', '') in self.known_whale_wallets:
            return 'accumulate'
        elif tx.get('from', '') in self.known_whale_wallets:
            return 'distribute'
        return 'transfer'
    
    async def _calculate_holder_growth(self, token_address: str) -> float:
        """Calculate 24h holder growth rate"""
        try:
            current = await self._get_token_holders(token_address)
            # Would need historical data for accurate calculation
            # For now, estimate from transaction velocity
            return 0.0  # Placeholder
        except:
            return 0.0
    
    async def _check_developer_activity(self, token_address: str) -> float:
        """Check developer activity score"""
        try:
            # Check if contract is verified, recent updates, etc.
            url = f"https://api.solscan.io/account/{token_address}"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Score based on various factors
                    score = 50  # Base score
                    
                    # Add points for verified contract
                    if data.get('verified', False):
                        score += 20
                    
                    # Add points for recent activity
                    last_activity = data.get('lastActivity', 0)
                    if last_activity and (datetime.now().timestamp() - last_activity) < 86400:
                        score += 15
                    
                    return min(score, 100)
                return 0
        except:
            return 0
    
    async def _get_social_sentiment(self, token_address: str) -> float:
        """Get social sentiment score (-100 to 100)"""
        # Would integrate with social media APIs
        # For now, placeholder
        return 0.0
    
    async def _analyze_contract_risk(self, token_address: str) -> float:
        """Analyze contract risk score (0-100, lower is better)"""
        try:
            # Check for common risk factors
            risk_score = 0
            
            # 1. Mint authority check
            mint_info = await self._get_mint_info(token_address)
            if mint_info.get('mintAuthority'):
                risk_score += 20  # Can mint more tokens
            
            # 2. Freeze authority check
            if mint_info.get('freezeAuthority'):
                risk_score += 15  # Can freeze accounts
            
            # 3. LP token check
            if await self._has_lp_tokens_burned(token_address):
                risk_score -= 10  # LP burned is good
            
            # 4. Contract verification
            if not await self._is_contract_verified(token_address):
                risk_score += 25
            
            # 5. Known scam patterns
            if await self._check_scam_patterns(token_address):
                risk_score += 50
            
            return max(0, min(100, risk_score))
        except:
            return 50  # Unknown risk
    
    async def _get_mint_info(self, token_address: str) -> Dict:
        """Get token mint information"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    token_address,
                    {"encoding": "jsonParsed"}
                ]
            }
            
            async with self.session.post(self.solana_rpc, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('result', {}).get('value', {}).get('data', {}).get('parsed', {}).get('info', {})
                return {}
        except:
            return {}
    
    async def _has_lp_tokens_burned(self, token_address: str) -> bool:
        """Check if LP tokens have been burned"""
        # This requires checking LP accounts
        # Placeholder - would need specific DEX integration
        return False
    
    async def _is_contract_verified(self, token_address: str) -> bool:
        """Check if contract is verified on Solscan"""
        try:
            url = f"https://api.solscan.io/account/{token_address}"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('verified', False)
                return False
        except:
            return False
    
    async def _check_scam_patterns(self, token_address: str) -> bool:
        """Check for known scam patterns"""
        # Would check against known scam database
        # Check for honeypot, rugpull patterns, etc.
        return False
    
    async def scan_opportunities(self) -> List[Dict]:
        """Scan for high-potential opportunities"""
        opportunities = []
        
        # Get trending tokens from multiple sources
        trending = await self._get_trending_tokens()
        
        for token in trending:
            address = token.get('address')
            if not address:
                continue
            
            metrics = await self.analyze_token(address)
            
            # Score the opportunity
            score = self._calculate_opportunity_score(metrics)
            
            if score >= 70:  # High potential threshold
                opportunities.append({
                    'token': metrics,
                    'score': score,
                    'signals': self._generate_signals(metrics),
                    'risk_level': self._assess_risk_level(metrics)
                })
        
        # Sort by score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        return opportunities[:10]  # Top 10
    
    async def _get_trending_tokens(self) -> List[Dict]:
        """Get trending tokens from multiple sources"""
        trending = []
        
        # Birdeye trending
        try:
            url = f"{self.birdeye_api}/public/v1/token/list?sort_by=v24hChangePercent&sort_type=desc&offset=0&limit=50"
            headers = {"X-API-KEY": "public"}
            
            async with self.session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    trending.extend(data.get('data', {}).get('items', []))
        except:
            pass
        
        return trending
    
    def _calculate_opportunity_score(self, metrics: TokenMetrics) -> float:
        """Calculate opportunity score (0-100)"""
        score = 50  # Base score
        
        # Volume momentum
        if metrics.volume_24h > metrics.volume_7d / 7:
            score += 15
        
        # Holder growth
        if metrics.holder_growth_24h > 10:
            score += 10
        
        # Smart money flowing in
        if metrics.smart_money_inflows > metrics.smart_money_outflows:
            score += 15
        
        # Whale activity
        if metrics.whale_transactions_24h > 5:
            score += 10
        
        # Low risk
        if metrics.contract_risk_score < 30:
            score += 10
        
        # Liquidity check
        if metrics.liquidity > 100000:  # $100k+
            score += 10
        
        # Not too concentrated
        if metrics.top_holder_concentration < 50:
            score += 5
        
        return min(100, score)
    
    def _generate_signals(self, metrics: TokenMetrics) -> List[str]:
        """Generate trading signals"""
        signals = []
        
        if metrics.smart_money_inflows > metrics.smart_money_outflows * 2:
            signals.append("🐋 Smart money accumulating")
        
        if metrics.whale_transactions_24h > 10:
            signals.append("🐋 High whale activity")
        
        if metrics.holder_growth_24h > 20:
            signals.append("📈 Rapid holder growth")
        
        if metrics.volume_24h > metrics.liquidity * 2:
            signals.append("🔥 Volume exceeding liquidity")
        
        if metrics.contract_risk_score < 20:
            signals.append("✅ Low contract risk")
        
        return signals
    
    def _assess_risk_level(self, metrics: TokenMetrics) -> str:
        """Assess risk level"""
        risk_factors = [
            metrics.contract_risk_score > 50,
            metrics.top_holder_concentration > 70,
            metrics.liquidity < 50000,
            metrics.smart_money_outflows > metrics.smart_money_inflows * 2
        ]
        
        risk_count = sum(risk_factors)
        
        if risk_count >= 3:
            return "🔴 HIGH"
        elif risk_count >= 2:
            return "🟡 MEDIUM"
        elif risk_count >= 1:
            return "🟢 LOW-MEDIUM"
        else:
            return "🟢 LOW"
    
    async def track_whale_wallets(self, wallets: List[str]):
        """Track specific whale/smart money wallets"""
        self.known_whale_wallets.update(wallets)
        self.smart_money_wallets.update(wallets)
    
    async def get_market_summary(self) -> Dict:
        """Get overall market summary"""
        # Analyze market-wide metrics
        summary = {
            'timestamp': datetime.now(),
            'total_liquidity_analyzed': sum(t.liquidity for t in self.token_cache.values()),
            'total_volume_24h': sum(t.volume_24h for t in self.token_cache.values()),
            'tokens_analyzed': len(self.token_cache),
            'high_opportunities': len([t for t in self.token_cache.values() 
                                      if self._calculate_opportunity_score(t) >= 70]),
            'avg_risk_score': np.mean([t.contract_risk_score for t in self.token_cache.values()]) if self.token_cache else 0,
            'whale_activity_24h': len(self.whale_movements),
            'smart_money_net_flow': sum(t.smart_money_inflows - t.smart_money_outflows 
                                       for t in self.token_cache.values())
        }
        
        return summary


class PatternRecognizer:
    """Recognize trading patterns from on-chain data"""
    
    def __init__(self):
        self.patterns = {
            'accumulation': self._detect_accumulation,
            'distribution': self._detect_distribution,
            'pump_pattern': self._detect_pump_pattern,
            'rugpull_warning': self._detect_rugpull_warning,
            'smart_money_front_run': self._detect_smart_money_front_run
        }
    
    def _detect_accumulation(self, data: List[Dict]) -> bool:
        """Detect whale accumulation pattern"""
        # Large wallets adding positions over time
        if len(data) < 5:
            return False
        
        buy_pressure = sum(1 for d in data if d.get('type') == 'buy' and d.get('amount_usd', 0) > 10000)
        return buy_pressure >= 3
    
    def _detect_distribution(self, data: List[Dict]) -> bool:
        """Detect whale distribution (selling) pattern"""
        sell_pressure = sum(1 for d in data if d.get('type') == 'sell' and d.get('amount_usd', 0) > 10000)
        return sell_pressure >= 3
    
    def _detect_pump_pattern(self, data: List[Dict]) -> bool:
        """Detect pump pattern"""
        # Rapid price increase + volume spike + social mentions
        price_change = data[-1].get('price', 0) / data[0].get('price', 1) - 1 if data else 0
        volume_spike = data[-1].get('volume', 0) > sum(d.get('volume', 0) for d in data[:-1]) / len(data[:-1]) * 3 if len(data) > 1 else False
        
        return price_change > 0.5 and volume_spike  # 50% price increase + 3x volume
    
    def _detect_rugpull_warning(self, data: List[Dict]) -> bool:
        """Detect rugpull warning signs"""
        warnings = [
            any(d.get('lp_removal', False) for d in data),  # LP removal
            any(d.get('mint', False) for d in data),  # Unexpected minting
            len([d for d in data if d.get('sell', False)]) > len(data) * 0.7  # Mostly sells
        ]
        return sum(warnings) >= 2
    
    def _detect_smart_money_front_run(self, data: List[Dict]) -> bool:
        """Detect if smart money is front-running"""
        # Smart money buying before price move
        smart_buys = [d for d in data if d.get('smart_money', False) and d.get('type') == 'buy']
        if len(smart_buys) >= 2:
            # Check if price moved up after
            last_smart_buy = smart_buys[-1]
            subsequent_price_change = data[-1].get('price', 0) / last_smart_buy.get('price', 1) - 1
            return subsequent_price_change > 0.1  # 10% move after smart buy
        return False
    
    def analyze(self, data: List[Dict]) -> Dict[str, bool]:
        """Run all pattern detection"""
        return {name: detector(data) for name, detector in self.patterns.items()}


# Usage example
async def main():
    async with BlockchainAnalyzer() as analyzer:
        # Track some known smart money wallets
        await analyzer.track_whale_wallets([
            "HJBVbY5Dj7m1yX4a1w6f5z7x8y9z",  # Example wallets
        ])
        
        # Analyze a token
        metrics = await analyzer.analyze_token("So11111111111111111111111111111111111111112")
        print(f"Token: {metrics.symbol}")
        print(f"Price: ${metrics.price:.4f}")
        print(f"Smart Money Inflows: ${metrics.smart_money_inflows:,.2f}")
        print(f"Risk Score: {metrics.contract_risk_score}/100")
        
        # Scan for opportunities
        opportunities = await analyzer.scan_opportunities()
        for opp in opportunities[:5]:
            print(f"\n{opp['token'].symbol}: Score {opp['score']}")
            for signal in opp['signals']:
                print(f"  {signal}")

if __name__ == "__main__":
    asyncio.run(main())
