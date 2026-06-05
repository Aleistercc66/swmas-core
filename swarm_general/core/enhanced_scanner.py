#!/usr/bin/env python3
"""
🔥 ENHANCED ACTIVE MARKET SCANNER
Σκανάρει συνεχώς για ευκαιρίες με αυστηρά κριτήρια.
Τρέχει κάθε 120 δευτερόλεπτα.
"""
import asyncio
import aiohttp
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('EnhancedScanner')

class EnhancedMarketScanner:
    """
    Ενεργό scanner που ψάχνει συνεχώς για crypto opportunities.
    """
    
    def __init__(self):
        self.session = None
        self.is_running = False
        self.opportunities_found = 0
        self.last_alert_time = 0
        
        # Load tuning from evolution engine config
        self._load_tuning()
        
        # Data storage
        self.price_history: Dict[str, List[float]] = {}
        self.token_stats: Dict[str, Dict] = {}
        self.hot_tokens: List[Dict] = []
        
    def _load_tuning(self):
        """Φορτώνει tuning config από evolution engine"""
        import os
        
        # Default values
        self.scan_interval = 120
        self.min_liquidity = 50000
        self.min_volume_24h = 100000
        self.min_momentum = 10
        self.min_buy_ratio = 1.5
        self.max_mcap = 10000000
        
        # Try to load from evolution tuning
        tuning_file = '/root/.openclaw/workspace/swarm_general/data/scanner_tuning.json'
        if os.path.exists(tuning_file):
            try:
                with open(tuning_file, 'r') as f:
                    tuning = json.load(f)
                
                self.scan_interval = tuning.get('scan_interval', self.scan_interval)
                self.min_liquidity = tuning.get('min_liquidity', self.min_liquidity)
                self.min_volume_24h = tuning.get('min_volume_24h', self.min_volume_24h)
                
                logger.info(f"📁 Loaded tuning: interval={self.scan_interval}s, liq=${self.min_liquidity:,}")
            except Exception as e:
                logger.warning(f"Could not load tuning: {e}")
        else:
            logger.info("📁 No tuning file found, using defaults")
        
        logger.info(f"📊 Scan interval: {self.scan_interval}s")
        logger.info(f"💰 Min liquidity: ${self.min_liquidity:,}")
        logger.info(f"📈 Min volume: ${self.min_volume_24h:,}")
        
    async def start(self):
        """Ξεκινάει το active scanning"""
        self.is_running = True
        self.session = aiohttp.ClientSession()
        
        logger.info("🔥 ENHANCED MARKET SCANNER STARTED")
        logger.info(f"📊 Scan interval: {self.scan_interval}s")
        logger.info(f"💰 Min liquidity: ${self.min_liquidity:,}")
        logger.info(f"📈 Min volume: ${self.min_volume_24h:,}")
        logger.info(f"🚀 Min momentum: {self.min_momentum}%")
        
        # Main scanning loop
        while self.is_running:
            try:
                await self._scan_cycle()
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Scan cycle error: {e}")
                await asyncio.sleep(10)
    
    async def _scan_cycle(self):
        """Ένας πλήρης scan κύκλος"""
        logger.info("🔍 Starting scan cycle...")
        start_time = time.time()
        
        # 1. Φέρε latest pairs
        pairs = await self._fetch_latest_pairs()
        
        # 2. Φέρε trending tokens
        trending = await self._fetch_trending()
        
        # 3. Φέρε boosted tokens
        boosted = await self._fetch_boosted()
        
        # 4. Ανάλυσε όλα μαζί
        all_tokens = pairs + trending + boosted
        opportunities = self._analyze_opportunities(all_tokens)
        
        # 5. Φίλτραρε με αυστηρά κριτήρια
        filtered = self._apply_strict_filters(opportunities)
        
        # 6. Score και rank
        scored = self._score_opportunities(filtered)
        
        # 7. Ενημέρωσε history
        self._update_history(scored)
        
        # 8. Στείλε alerts για top opportunities
        await self._send_alerts(scored[:5])  # Top 5
        
        elapsed = time.time() - start_time
        logger.info(
            f"✅ Scan complete in {elapsed:.1f}s | "
            f"Scanned: {len(all_tokens)} | Opportunities: {len(scored)} | "
            f"Hot: {len(self.hot_tokens)}"
        )
    
    async def _fetch_latest_pairs(self) -> List[Dict]:
        """Φέρε τα πιο πρόσφατα pairs"""
        tokens = []
        
        try:
            # DexScreener latest token profiles
            async with self.session.get(
                "https://api.dexscreener.com/token-profiles/latest/v1",
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    for token in data[:50]:  # Top 50
                        tokens.append({
                            'address': token.get('tokenAddress', ''),
                            'chain': token.get('chainId', ''),
                            'name': self._extract_name(token.get('description', '')),
                            'description': token.get('description', '')[:200],
                            'links': token.get('links', []),
                            'source': 'latest_profiles',
                            'timestamp': time.time()
                        })
        except Exception as e:
            logger.error(f"Error fetching latest: {e}")
        
        return tokens
    
    async def _fetch_trending(self) -> List[Dict]:
        """Φέρε trending tokens"""
        tokens = []
        
        try:
            async with self.session.get(
                "https://api.dexscreener.com/token-boosts/top/v1",
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    for token in data[:30]:
                        tokens.append({
                            'address': token.get('tokenAddress', ''),
                            'chain': token.get('chainId', ''),
                            'name': self._extract_name(token.get('description', '')),
                            'description': token.get('description', '')[:200],
                            'boost_amount': token.get('totalAmount', 0),
                            'links': token.get('links', []),
                            'source': 'boosted',
                            'timestamp': time.time()
                        })
        except Exception as e:
            logger.error(f"Error fetching trending: {e}")
        
        return tokens
    
    async def _fetch_boosted(self) -> List[Dict]:
        """Φέρε boosted tokens με details"""
        tokens = []
        
        try:
            # Fetch specific pair data for more metrics
            for chain in ['solana', 'ethereum', 'bsc']:
                try:
                    async with self.session.get(
                        f"https://api.dexscreener.com/latest/dex/search?q={chain}",
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            for pair in data.get('pairs', [])[:20]:
                                tokens.append({
                                    'address': pair.get('baseToken', {}).get('address', ''),
                                    'chain': pair.get('chainId', ''),
                                    'name': pair.get('baseToken', {}).get('name', 'Unknown'),
                                    'symbol': pair.get('baseToken', {}).get('symbol', ''),
                                    'price': pair.get('priceUsd', 0),
                                    'liquidity': pair.get('liquidity', {}).get('usd', 0),
                                    'volume_24h': pair.get('volume', {}).get('h24', 0),
                                    'price_change_24h': pair.get('priceChange', {}).get('h24', 0),
                                    'buys': pair.get('txns', {}).get('h24', {}).get('buys', 0),
                                    'sells': pair.get('txns', {}).get('h24', {}).get('sells', 0),
                                    'source': 'pair_data',
                                    'timestamp': time.time()
                                })
                except Exception as e:
                    logger.error(f"Error fetching {chain}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in boosted fetch: {e}")
        
        return tokens
    
    def _analyze_opportunities(self, tokens: List[Dict]) -> List[Dict]:
        """Ανάλυσε tokens για ευκαιρίες"""
        opportunities = []
        
        for token in tokens:
            # Υπολόγισε momentum score
            price_change = token.get('price_change_24h', 0)
            volume = token.get('volume_24h', 0)
            liquidity = token.get('liquidity', 0)
            buys = token.get('buys', 0)
            sells = token.get('sells', 1)  # Avoid div by zero
            
            # Buy/Sell ratio
            buy_ratio = buys / sells if sells > 0 else 0
            
            # Volume/Liquidity ratio (activity indicator)
            vol_liq_ratio = volume / liquidity if liquidity > 0 else 0
            
            # Calculate composite score
            score = 0
            
            # Price momentum (0-40 points)
            if price_change > 50:
                score += 40
            elif price_change > 20:
                score += 30
            elif price_change > 10:
                score += 20
            elif price_change > 0:
                score += 10
            
            # Volume activity (0-30 points)
            if vol_liq_ratio > 5:
                score += 30
            elif vol_liq_ratio > 2:
                score += 20
            elif vol_liq_ratio > 1:
                score += 10
            
            # Buy pressure (0-30 points)
            if buy_ratio > 3:
                score += 30
            elif buy_ratio > 2:
                score += 20
            elif buy_ratio > 1.5:
                score += 10
            
            token['score'] = score
            token['buy_ratio'] = buy_ratio
            token['vol_liq_ratio'] = vol_liq_ratio
            
            if score > 0:
                opportunities.append(token)
        
        return opportunities
    
    def _apply_strict_filters(self, opportunities: List[Dict]) -> List[Dict]:
        """Εφάρμοσε αυστηρά κριτήρια φιλτραρίσματος"""
        filtered = []
        
        for opp in opportunities:
            # Check minimum liquidity
            if opp.get('liquidity', 0) < self.min_liquidity:
                continue
            
            # Check minimum volume
            if opp.get('volume_24h', 0) < self.min_volume_24h:
                continue
            
            # Check momentum
            if opp.get('price_change_24h', 0) < self.min_momentum:
                continue
            
            # Check buy ratio
            if opp.get('buy_ratio', 0) < self.min_buy_ratio:
                continue
            
            # Check market cap (avoid too big)
            if opp.get('liquidity', 0) > self.max_mcap:
                continue
            
            # Check if not already alerted recently
            addr = opp.get('address', '')
            if addr in self.token_stats:
                last_alert = self.token_stats[addr].get('last_alert', 0)
                if time.time() - last_alert < 3600:  # 1 hour cooldown
                    continue
            
            filtered.append(opp)
        
        return filtered
    
    def _score_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """Score και rank ευκαιρίες"""
        # Sort by score descending
        scored = sorted(opportunities, key=lambda x: x.get('score', 0), reverse=True)
        
        # Add tier
        for opp in scored:
            score = opp.get('score', 0)
            if score >= 80:
                opp['tier'] = 'S'
                opp['emoji'] = '🔥🔥🔥'
            elif score >= 60:
                opp['tier'] = 'A'
                opp['emoji'] = '🔥🔥'
            elif score >= 40:
                opp['tier'] = 'B'
                opp['emoji'] = '🔥'
            else:
                opp['tier'] = 'C'
                opp['emoji'] = '⚡'
        
        return scored
    
    def _update_history(self, opportunities: List[Dict]):
        """Ενημέρωσε price history και hot tokens"""
        self.hot_tokens = opportunities[:10]  # Keep top 10
        
        for opp in opportunities[:5]:
            addr = opp.get('address', '')
            if addr:
                self.token_stats[addr] = {
                    'last_seen': time.time(),
                    'last_alert': time.time(),
                    'score': opp.get('score', 0),
                    'tier': opp.get('tier', 'C')
                }
    
    async def _send_alerts(self, opportunities: List[Dict]):
        """Στείλε alerts για top opportunities"""
        for opp in opportunities:
            # Log alert
            logger.info(
                f"🚨 ALERT: {opp.get('emoji', '')} {opp.get('name', 'Unknown')} | "
                f"Score: {opp.get('score', 0)} | Tier: {opp.get('tier', 'C')} | "
                f"Price Change: {opp.get('price_change_24h', 0):.1f}% | "
                f"Liquidity: ${opp.get('liquidity', 0):,.0f}"
            )
            
            # Write to file for other systems to read
            self._log_opportunity(opp)
    
    def _log_opportunity(self, opp: Dict):
        """Καταγραφή ευκαιρίας σε file"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'token': opp.get('name', 'Unknown'),
                'address': opp.get('address', ''),
                'chain': opp.get('chain', ''),
                'score': opp.get('score', 0),
                'tier': opp.get('tier', 'C'),
                'price_change_24h': opp.get('price_change_24h', 0),
                'liquidity': opp.get('liquidity', 0),
                'volume_24h': opp.get('volume_24h', 0),
                'buy_ratio': opp.get('buy_ratio', 0)
            }
            
            with open('/root/.openclaw/workspace/swarm_general/data/scanner_alerts.jsonl', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging opportunity: {e}")
    
    def _extract_name(self, description: str) -> str:
        """Εξαγωγή ονόματος από description"""
        if not description:
            return 'Unknown'
        
        # Try to find $TOKEN format
        import re
        match = re.search(r'\$([A-Za-z0-9]+)', description)
        if match:
            return match.group(1)
        
        # Return first word capitalized
        words = description.split()
        if words:
            return words[0][:20]
        
        return 'Unknown'
    
    async def stop(self):
        """Σταματάει το scanner"""
        self.is_running = False
        if self.session:
            await self.session.close()
        logger.info("🛑 Scanner stopped")
    
    def get_stats(self) -> Dict:
        """Επιστροφή στατιστικών"""
        return {
            'is_running': self.is_running,
            'scan_interval': self.scan_interval,
            'opportunities_found': self.opportunities_found,
            'hot_tokens_count': len(self.hot_tokens),
            'filters': {
                'min_liquidity': self.min_liquidity,
                'min_volume': self.min_volume_24h,
                'min_momentum': self.min_momentum,
                'min_buy_ratio': self.min_buy_ratio
            }
        }


async def main():
    """Main entry point"""
    scanner = EnhancedMarketScanner()
    
    try:
        await scanner.start()
    except KeyboardInterrupt:
        await scanner.stop()

if __name__ == '__main__':
    asyncio.run(main())
