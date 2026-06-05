#!/usr/bin/env python3
"""
🌐 MULTI-CHAIN SCANNER
Σκανάρει Solana, Ethereum, BSC, Arbitrum ταυτόχρονα.
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('MultiChainScanner')

class MultiChainScanner:
    """
    Multi-chain scanner για παράλληλο scanning.
    """
    
    CHAINS = {
        'solana': {
            'name': 'Solana',
            'dexscreener_chain': 'solana',
            'priority': 1
        },
        'ethereum': {
            'name': 'Ethereum',
            'dexscreener_chain': 'ethereum',
            'priority': 2
        },
        'bsc': {
            'name': 'BNB Chain',
            'dexscreener_chain': 'bsc',
            'priority': 3
        },
        'arbitrum': {
            'name': 'Arbitrum',
            'dexscreener_chain': 'arbitrum',
            'priority': 4
        }
    }
    
    def __init__(self):
        self.session = None
        self.results: Dict[str, List[Dict]] = {}
        self.is_running = False
        
    async def start(self):
        """Ξεκινάει multi-chain scanning"""
        self.is_running = True
        self.session = aiohttp.ClientSession()
        
        logger.info("🌐 Multi-Chain Scanner started")
        logger.info(f"🔗 Chains: {', '.join(self.CHAINS.keys())}")
        
        while self.is_running:
            # Scan all chains in parallel
            tasks = [
                self._scan_chain(chain_id, config)
                for chain_id, config in self.CHAINS.items()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for chain_id, result in zip(self.CHAINS.keys(), results):
                if isinstance(result, list):
                    self.results[chain_id] = result
                    logger.info(f"✅ {chain_id}: {len(result)} tokens found")
                else:
                    logger.error(f"❌ {chain_id}: {result}")
            
            # Merge results
            all_tokens = self._merge_results()
            logger.info(f"🌐 Total: {len(all_tokens)} tokens across all chains")
            
            await asyncio.sleep(180)  # Every 3 minutes
    
    async def _scan_chain(self, chain_id: str, config: Dict) -> List[Dict]:
        """Σκανάρει συγκεκριμένο chain"""
        tokens = []
        chain_name = config['name']
        
        try:
            # Fetch top pairs for chain
            url = f"https://api.dexscreener.com/latest/dex/search?q={chain_id}"
            
            async with self.session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    for pair in pairs[:50]:  # Top 50
                        token = {
                            'address': pair.get('baseToken', {}).get('address', ''),
                            'symbol': pair.get('baseToken', {}).get('symbol', ''),
                            'name': pair.get('baseToken', {}).get('name', ''),
                            'chain': chain_id,
                            'chain_name': chain_name,
                            'price_usd': pair.get('priceUsd', 0),
                            'liquidity': pair.get('liquidity', {}).get('usd', 0),
                            'volume_24h': pair.get('volume', {}).get('h24', 0),
                            'price_change': pair.get('priceChange', {}).get('h24', 0),
                            'fdv': pair.get('fdv', 0),
                            'market_cap': pair.get('marketCap', 0),
                            'pair_url': pair.get('url', '')
                        }
                        tokens.append(token)
                        
        except Exception as e:
            logger.error(f"Error scanning {chain_id}: {e}")
            
        return tokens
    
    def _merge_results(self) -> List[Dict]:
        """Συνδυάζει results από όλα τα chains"""
        all_tokens = []
        
        for chain_id, tokens in self.results.items():
            for token in tokens:
                token['chain_priority'] = self.CHAINS[chain_id]['priority']
                all_tokens.append(token)
        
        # Sort by volume
        all_tokens.sort(key=lambda x: x.get('volume_24h', 0), reverse=True)
        
        return all_tokens
    
    def get_top_opportunities(self, min_volume: float = 100000) -> List[Dict]:
        """Get top opportunities across all chains"""
        all_tokens = self._merge_results()
        
        # Filter
        filtered = [
            t for t in all_tokens
            if t.get('volume_24h', 0) >= min_volume
            and t.get('liquidity', 0) > 50000
        ]
        
        # Score
        for token in filtered:
            score = 0
            
            # Volume score
            vol = token.get('volume_24h', 0)
            if vol > 1000000:
                score += 40
            elif vol > 500000:
                score += 30
            elif vol > 100000:
                score += 20
            
            # Price change score
            change = token.get('price_change', 0)
            if change > 50:
                score += 40
            elif change > 20:
                score += 30
            elif change > 10:
                score += 20
            
            # Liquidity score
            liq = token.get('liquidity', 0)
            if liq > 500000:
                score += 20
            elif liq > 100000:
                score += 10
            
            token['opportunity_score'] = score
        
        # Sort by score
        filtered.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
        
        return filtered[:20]
    
    async def stop(self):
        """Stop scanner"""
        self.is_running = False
        if self.session:
            await self.session.close()
        logger.info("🛑 Multi-Chain Scanner stopped")


async def main():
    """Main entry"""
    scanner = MultiChainScanner()
    
    try:
        await scanner.start()
    except KeyboardInterrupt:
        await scanner.stop()

if __name__ == '__main__':
    asyncio.run(main())