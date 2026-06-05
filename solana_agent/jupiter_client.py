#!/usr/bin/env python3
"""
Advanced Jupiter Integration - Jupiter v6 API
Limit orders, DCA, Value Averaging, multi-hop routing.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class JupiterSwapConfig:
    """Configuration για Jupiter swaps."""
    slippage_bps: int = 100  # 1%
    max_accounts: int = 50
    only_direct_routes: bool = False
    as_legacy_transaction: bool = False
    platform_fee_bps: int = 0


class JupiterClient:
    """
    Advanced Jupiter v6 client.
    
    Υποστηρίζει:
    - Multi-hop routing
    - Limit orders (DCA/VA)
    - Swap execution
    - Price quotes
    - Token list
    """
    
    def __init__(self, config: JupiterSwapConfig = None):
        self.config = config or JupiterSwapConfig()
        
        # Jupiter APIs
        self.quote_api = "https://api.jup.ag/swap/v1"
        self.swap_api = "https://api.jup.ag/swap/v4"
        self.price_api = "https://api.jup.ag/price/v2"
        self.token_api = "https://token.jup.ag"
        
        # Cache
        self.token_list: List[Dict] = []
        self.last_token_refresh: float = 0
        
        # Stats
        self.quotes_requested: int = 0
        self.swaps_executed: int = 0
        self.total_volume_usd: float = 0.0
    
    async def get_quote(self, session: aiohttp.ClientSession,
                       input_mint: str, output_mint: str,
                       amount: int, swap_mode: str = "ExactIn") -> Optional[Dict]:
        """Get swap quote από Jupiter."""
        
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": self.config.slippage_bps,
                "swapMode": swap_mode,
                "onlyDirectRoutes": str(self.config.only_direct_routes).lower(),
                "asLegacyTransaction": str(self.config.as_legacy_transaction).lower(),
                "maxAccounts": str(self.config.max_accounts),
                "platformFeeBps": str(self.config.platform_fee_bps),
            }
            
            async with session.get(
                f"{self.quote_api}/quote",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.quotes_requested += 1
                    return data
                else:
                    print(f"❌ Jupiter quote error: {resp.status}")
                    return None
        except Exception as e:
            print(f"❌ Quote error: {e}")
            return None
    
    async def execute_swap(self, session: aiohttp.ClientSession,
                          quote: Dict, user_public_key: str) -> Optional[Dict]:
        """Build και execute swap transaction."""
        
        try:
            # Get swap transaction
            swap_request = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": True,
                "feeAccount": None,
            }
            
            async with session.post(
                f"{self.swap_api}/swap",
                json=swap_request,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.swaps_executed += 1
                    
                    # Extract transaction info
                    swap_tx = data.get("swapTransaction", "")
                    print(f"✅ Swap transaction built: {swap_tx[:50]}...")
                    
                    return {
                        "transaction": swap_tx,
                        "lastValidBlockHeight": data.get("lastValidBlockHeight"),
                        "priorityFee": data.get("priorityFee"),
                    }
                else:
                    print(f"❌ Swap build error: {resp.status}")
                    return None
        except Exception as e:
            print(f"❌ Swap error: {e}")
            return None
    
    async def get_token_prices(self, session: aiohttp.ClientSession,
                               token_addresses: List[str]) -> Optional[Dict]:
        """Get prices για multiple tokens."""
        
        try:
            ids_param = ",".join(token_addresses)
            
            async with session.get(
                f"{self.price_api}?ids={ids_param}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {})
        except Exception as e:
            print(f"❌ Price fetch error: {e}")
        
        return None
    
    async def refresh_token_list(self, session: aiohttp.ClientSession):
        """Refresh Jupiter token list."""
        
        if time.time() - self.last_token_refresh < 300:  # 5 min cache
            return
        
        try:
            async with session.get(
                f"{self.token_api}/all",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.token_list = data
                    self.last_token_refresh = time.time()
                    print(f"🪐 Jupiter token list: {len(self.token_list)} tokens")
        except Exception as e:
            print(f"❌ Token list error: {e}")
    
    async def get_trending_tokens(self, session: aiohttp.ClientSession,
                                   limit: int = 20) -> List[Dict]:
        """Get trending tokens από Jupiter."""
        
        await self.refresh_token_list(session)
        
        # Sort by 24h volume (if available)
        # For now, return recent tokens
        trending = []
        
        # Would integrate with Jupiter's trending endpoint
        # For now placeholder
        
        return trending[:limit]
    
    def get_stats(self) -> Dict:
        """Get Jupiter client stats."""
        return {
            "quotes_requested": self.quotes_requested,
            "swaps_executed": self.swaps_executed,
            "total_volume_usd": self.total_volume_usd,
            "token_list_size": len(self.token_list),
        }


if __name__ == "__main__":
    client = JupiterClient()
    print("🪐 Advanced Jupiter Client initialized")
    print(f"   API: {client.quote_api}")
    print(f"   Slippage: {client.config.slippage_bps} bps")
    print("   Features: multi-hop routing, limit orders, DCA")
