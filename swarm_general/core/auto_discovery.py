#!/usr/bin/env python3
"""
🎯 AUTO-DISCOVERY ENGINE
Αυτόματο finding και analysis νέων ευκαιριών.
"""
import asyncio
import logging
import time
from typing import Dict, List, Any
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('AutoDiscovery')

class AutoDiscoveryEngine:
    """
    Αυτόματος engine που ψάχνει για signals χωρίς human input.
    """
    
    def __init__(self):
        self.is_running = False
        self.discovered_signals: List[Dict] = []
        self.sources = [
            'dexscreener_latest',
            'dexscreener_boosted',
            'twitter_trending',
            'telegram_groups',
            'pump_fun'
        ]
        self.scan_interval = 300  # 5 minutes
        
    async def start(self):
        """Ξεκινάει auto-discovery"""
        self.is_running = True
        
        logger.info("🎯 Auto-Discovery Engine started")
        logger.info(f"🔍 Sources: {', '.join(self.sources)}")
        logger.info(f"⏱️ Scan interval: {self.scan_interval}s")
        
        while self.is_running:
            try:
                await self._discovery_cycle()
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Discovery cycle error: {e}")
                await asyncio.sleep(60)
    
    async def _discovery_cycle(self):
        """Ένας discovery κύκλος"""
        logger.info("🔍 Starting discovery cycle...")
        
        # 1. Discover από DexScreener
        dex_signals = await self._discover_dexscreener()
        
        # 2. Discover από social
        social_signals = await self._discover_social()
        
        # 3. Merge και deduplicate
        all_signals = dex_signals + social_signals
        unique = self._deduplicate(all_signals)
        
        # 4. Score signals
        scored = self._score_signals(unique)
        
        # 5. Filter high-quality
        high_quality = [s for s in scored if s.get('score', 0) >= 60]
        
        # 6. Store
        self.discovered_signals.extend(high_quality)
        
        logger.info(
            f"🎯 Discovery: {len(all_signals)} raw | "
            f"{len(unique)} unique | "
            f"{len(high_quality)} high-quality"
        )
        
        # 7. Alert for top signals
        await self._alert_top_signals(high_quality[:5])
    
    async def _discover_dexscreener(self) -> List[Dict]:
        """Discover από DexScreener"""
        signals = []
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Latest profiles
                async with session.get(
                    "https://api.dexscreener.com/token-profiles/latest/v1",
                    timeout=10
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for token in data[:30]:
                            signals.append({
                                'type': 'new_token',
                                'source': 'dexscreener_latest',
                                'address': token.get('tokenAddress', ''),
                                'chain': token.get('chainId', ''),
                                'description': token.get('description', '')[:100],
                                'timestamp': time.time(),
                                'confidence': 50
                            })
                
                # Boosted tokens
                async with session.get(
                    "https://api.dexscreener.com/token-boosts/top/v1",
                    timeout=10
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for token in data[:20]:
                            signals.append({
                                'type': 'boosted',
                                'source': 'dexscreener_boosted',
                                'address': token.get('tokenAddress', ''),
                                'chain': token.get('chainId', ''),
                                'boost_amount': token.get('totalAmount', 0),
                                'timestamp': time.time(),
                                'confidence': 60
                            })
        except Exception as e:
            logger.error(f"DexScreener discovery error: {e}")
        
        return signals
    
    async def _discover_social(self) -> List[Dict]:
        """Discover από social signals"""
        signals = []
        
        # Simulated social discovery
        # Σε production: Twitter API, Telegram monitoring, etc.
        
        return signals
    
    def _deduplicate(self, signals: List[Dict]) -> List[Dict]:
        """Αφαιρεί duplicates"""
        seen = set()
        unique = []
        
        for signal in signals:
            addr = signal.get('address', '')
            if addr and addr not in seen:
                seen.add(addr)
                unique.append(signal)
        
        return unique
    
    def _score_signals(self, signals: List[Dict]) -> List[Dict]:
        """Score signals βάσει ποιότητας"""
        for signal in signals:
            score = signal.get('confidence', 0)
            
            # Boost για boosted tokens
            if signal.get('type') == 'boosted':
                boost = signal.get('boost_amount', 0)
                if boost > 100:
                    score += 30
                elif boost > 50:
                    score += 20
                elif boost > 10:
                    score += 10
            
            # Boost για νέα tokens με description
            if signal.get('description', ''):
                score += 10
            
            # Penalty για άγνωστο chain
            if signal.get('chain') not in ['solana', 'ethereum']:
                score -= 10
            
            signal['score'] = min(score, 100)
        
        return signals
    
    async def _alert_top_signals(self, signals: List[Dict]):
        """Ειδοποιεί για top signals"""
        for signal in signals:
            logger.info(
                f"🚨 AUTO-DISCOVERED: {signal.get('type', 'unknown')} | "
                f"Score: {signal.get('score', 0)} | "
                f"Address: {signal.get('address', 'unknown')[:20]}..."
            )
    
    def get_stats(self) -> Dict:
        """Get discovery stats"""
        return {
            'signals_discovered': len(self.discovered_signals),
            'sources': self.sources,
            'scan_interval': self.scan_interval,
            'is_running': self.is_running
        }
    
    async def stop(self):
        """Stop discovery"""
        self.is_running = False
        logger.info("🛑 Auto-Discovery stopped")


async def main():
    """Main entry"""
    engine = AutoDiscoveryEngine()
    
    try:
        await engine.start()
    except KeyboardInterrupt:
        await engine.stop()

if __name__ == '__main__':
    asyncio.run(main())
