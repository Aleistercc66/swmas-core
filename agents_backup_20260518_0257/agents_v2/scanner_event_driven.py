#!/usr/bin/env python3
"""🎯 Event-Driven Scanner — publishes TokenDiscoveredEvent to event bus."""
import asyncio
import httpx
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from core import (
    get_logger, init_db, get_settings,
    ScannerStateManager,
    get_event_bus, EventType,
    TokenDiscoveredEvent,
    set_agent_healthy, set_agent_down,
)

logger = get_logger("scanner")


class EventDrivenScanner:
    """Scanner that publishes events instead of DB-only storage."""
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.running = False
        self.batch_counter = 0
        self.bus = None
        self.settings = get_settings()
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))
        self.bus = await get_event_bus()
        await init_db()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def _get_boosted_tokens(self) -> List[Dict[str, Any]]:
        """Fetch boosted tokens from DexScreener."""
        try:
            resp = await self.client.get(
                "https://api.dexscreener.com/token-boosts/latest/v1",
                headers={"Accept": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Boosted fetch failed: {e}")
            return []
    
    async def _get_solana_pairs(self) -> List[Dict[str, Any]]:
        """Fetch Solana pairs."""
        try:
            resp = await self.client.get(
                "https://api.dexscreener.com/latest/dex/search?q=solana",
                headers={"Accept": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs", []) if isinstance(data, dict) else []
            # Filter Solana
            return [
                p for p in pairs
                if isinstance(p, dict) and p.get("chainId", "").lower() == "solana"
            ][:20]
        except Exception as e:
            logger.error(f"Solana fetch failed: {e}")
            return []
    
    def _enrich_pair(self, pair: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DexScreener pair to enriched dict."""
        volume = pair.get("volume", {})
        liquidity = pair.get("liquidity", {})
        price_change = pair.get("priceChange", {})
        txns = pair.get("txns", {})
        txns_24h = txns.get("h24", {}) if isinstance(txns, dict) else {}
        
        return {
            "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
            "name": pair.get("baseToken", {}).get("name", ""),
            "address": pair.get("baseToken", {}).get("address", ""),
            "price": float(pair.get("priceUsd", 0) or 0),
            "volume_24h": float(volume.get("h24", 0) or 0),
            "volume_6h": float(volume.get("h6", 0) or 0),
            "volume_1h": float(volume.get("h1", 0) or 0),
            "liquidity": float(liquidity.get("usd", 0) or 0),
            "fdv": float(pair.get("fdv", 0) or 0),
            "market_cap": float(pair.get("marketCap", 0) or 0),
            "price_change_24h": float(price_change.get("h24", 0) or 0),
            "price_change_6h": float(price_change.get("h6", 0) or 0),
            "price_change_1h": float(price_change.get("h1", 0) or 0),
            "price_change_5m": float(price_change.get("m5", 0) or 0),
            "buy_ratio": self._calc_buy_ratio(txns_24h),
            "buys_24h": int(txns_24h.get("buys", 0) or 0),
            "sells_24h": int(txns_24h.get("sells", 0) or 0),
            "dex_id": pair.get("dexId", ""),
            "pair_address": pair.get("pairAddress", ""),
            "url": pair.get("url", ""),
            "source": "dexscreener",
        }
    
    def _calc_buy_ratio(self, txns_24h: Dict) -> float:
        """Calculate buy/sell ratio."""
        buys = int(txns_24h.get("buys", 0) or 0)
        sells = int(txns_24h.get("sells", 0) or 0)
        if sells == 0:
            return float(buys) if buys > 0 else 0.0
        return round(buys / sells, 2)
    
    async def run_scan_cycle(self) -> Optional[str]:
        """Run one scan cycle and publish event."""
        self.batch_counter += 1
        batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"=== SCAN CYCLE #{self.batch_counter} | {batch_id} ===")
        
        # Fetch
        boosted = await self._get_boosted_tokens()
        solana_pairs = await self._get_solana_pairs()
        
        logger.info(f"Boosted tokens: {len(boosted)}")
        logger.info(f"Solana pairs fetched: {len(solana_pairs)}")
        
        # Enrich
        all_tokens = []
        for pair in solana_pairs[:20]:
            if isinstance(pair, dict):
                enriched = self._enrich_pair(pair)
                all_tokens.append(enriched)
        
        # Filter quality
        min_liq = self.settings.min_liquidity_usd
        min_vol = self.settings.min_volume_24h
        
        quality_pairs = [
            t for t in all_tokens
            if t.get("liquidity", 0) >= min_liq
            and t.get("volume_24h", 0) >= min_vol
        ]
        
        logger.info(f"Quality pairs after filtering: {len(quality_pairs)}")
        
        if not quality_pairs:
            logger.info("No quality pairs found")
            return None
        
        # Save to DB
        saved = 0
        for enriched in quality_pairs:
            try:
                from core.models import ScannerOutputCreate
                obj = ScannerOutputCreate(**enriched)
                await ScannerStateManager.create(obj)
                saved += 1
            except Exception as e:
                logger.error(f"Failed to save {enriched.get('symbol', '?')}: {e}")
        
        logger.info(f"Scan complete: {saved}/{len(quality_pairs)} saved")
        
        # Publish event
        event = TokenDiscoveredEvent(
            tokens=quality_pairs,
            batch_id=batch_id,
            timestamp=datetime.utcnow(),
        )
        
        if self.bus:
            msg_id = await self.bus.publish_simple(
                event_type=EventType.TOKENS_DISCOVERED,
                data=event.model_dump(),
                source="scanner",
                correlation_id=batch_id,
            )
            logger.info(f"Published event: {msg_id} ({len(quality_pairs)} tokens)")
        
        set_agent_healthy("scanner")
        return batch_id
    
    async def run(self):
        """Main loop."""
        logger.info("═══════════════════════════════════════")
        logger.info("🎯 EVENT-DRIVEN SCANNER V2 STARTED")
        logger.info("Publishes to Redis Event Bus")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        while self.running:
            try:
                await self.run_scan_cycle()
                await asyncio.sleep(self.settings.scan_interval_seconds)
            except asyncio.CancelledError:
                logger.info("Scanner cancelled")
                break
            except Exception as e:
                logger.error(f"Scan loop error: {e}")
                set_agent_down("scanner")
                await asyncio.sleep(5)
        
        if self.bus:
            await self.bus.disconnect()


async def main():
    """Entry point."""
    async with EventDrivenScanner() as scanner:
        await scanner.run()


if __name__ == "__main__":
    asyncio.run(main())
