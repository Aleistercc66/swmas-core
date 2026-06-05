#!/usr/bin/env python3
"""
🎯 AGENT V2: SCANNER — Async, event-driven, database-persisted
Replaces v2_scanner.py. Uses httpx, SQLModel, Redis pub/sub.
"""
import asyncio
import httpx
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

from core import (
    settings, get_logger, init_db,
    ScannerStateManager, ScannerOutputCreate,
    emit_token_discovered,
    timed, count_exceptions, set_agent_healthy, set_agent_down,
    SCANNER_RUNS, SCAN_LATENCY, API_REQUEST_LATENCY, ERRORS_TOTAL,
)

logger = get_logger("scanner")

class AsyncScanner:
    """Production-grade async token scanner."""
    
    def __init__(self):
        self.client: httpx.AsyncClient | None = None
        self.running = False
        self.batch_counter = 0
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        return self
    
    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()
    
    @timed(SCAN_LATENCY)
    @count_exceptions(ERRORS_TOTAL, "scanner", "api")
    async def fetch_boosted_tokens(self) -> List[Dict]:
        """Fetch DexScreener boosted tokens."""
        url = "https://api.dexscreener.com/token-boosts/latest/v1"
        start = datetime.now(timezone.utc)
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            latency = (datetime.now(timezone.utc) - start).total_seconds()
            API_REQUEST_LATENCY.labels(api="dexscreener_boosted").observe(latency)
            
            tokens = []
            for item in data:
                token = item.get("tokenAddress", "")
                if token:
                    tokens.append({
                        "address": token,
                        "symbol": item.get("symbol", "???"),
                        "name": item.get("name", ""),
                    })
            
            logger.info(f"Boosted tokens: {len(tokens)}")
            return tokens
            
        except Exception as e:
            logger.error(f"Boosted fetch failed: {e}")
            return []
    
    @timed(SCAN_LATENCY)
    async def fetch_solana_pairs(self) -> List[Dict]:
        """Fetch trending Solana pairs from DexScreener via search."""
        # Use search endpoint with a broad query to get trending Solana pairs
        url = f"{settings.scanner.dexscreener_base_url}/search?q=solana"
        start = datetime.now(timezone.utc)
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            latency = (datetime.now(timezone.utc) - start).total_seconds()
            API_REQUEST_LATENCY.labels(api="dexscreener_search").observe(latency)
            
            pairs = data.get("pairs", [])
            # Filter to solana chain only
            solana_pairs = [p for p in pairs if p.get("chainId", "").lower() == "solana"]
            logger.info(f"Solana pairs fetched: {len(solana_pairs)} (from {len(pairs)} total)")
            return solana_pairs
            
        except Exception as e:
            logger.error(f"Pairs fetch failed: {e}")
            return []
    
    @timed(SCAN_LATENCY)
    async def fetch_jupiter_prices(self, token_ids: List[str]) -> Dict:
        """Fetch prices from Jupiter (free, no key)."""
        if not token_ids:
            return {}
        
        ids_param = ",".join(token_ids)
        url = f"{settings.scanner.jupiter_price_url}?ids={ids_param}"
        start = datetime.now(timezone.utc)
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            latency = (datetime.now(timezone.utc) - start).total_seconds()
            API_REQUEST_LATENCY.labels(api="jupiter_price").observe(latency)
            
            return data.get("data", {})
            
        except Exception as e:
            logger.error(f"Jupiter price fetch failed: {e}")
            return {}
    
    def enrich_pair(self, pair: Dict) -> ScannerOutputCreate:
        """Convert raw pair data to typed model."""
        price = float(pair.get("priceUsd", 0) or 0)
        liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
        vol24 = float(pair.get("volume", {}).get("h24", 0) or 0)
        
        chg5m = float(pair.get("priceChange", {}).get("m5", 0) or 0)
        chg1h = float(pair.get("priceChange", {}).get("h1", 0) or 0)
        chg6h = float(pair.get("priceChange", {}).get("h6", 0) or 0)
        chg24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)
        
        txns = pair.get("txns", {})
        buys24 = txns.get("h24", {}).get("buys", 0)
        sells24 = txns.get("h24", {}).get("sells", 0)
        
        # Momentum score
        momentum = (chg5m * 0.4) + (chg1h * 0.3) + (chg6h * 0.2) + (chg24h * 0.1)
        vol_liq = vol24 / liq if liq > 0 else 0
        
        base_token = pair.get("baseToken", {})
        
        return ScannerOutputCreate(
            symbol=base_token.get("symbol", "???"),
            name=base_token.get("name", ""),
            token_address=base_token.get("address", ""),
            chain="solana",
            price=price,
            liquidity=liq,
            volume_24h=vol24,
            change_5m=chg5m,
            change_1h=chg1h,
            change_6h=chg6h,
            change_24h=chg24h,
            buys_24h=buys24,
            sells_24h=sells24,
            dex_id=pair.get("dexId", "unknown"),
            pair_address=pair.get("pairAddress", ""),
            url=pair.get("url", ""),
            source="dexscreener",
            scan_batch_id=self.current_batch_id,
            momentum_score=round(momentum, 2),
            vol_liq_ratio=round(vol_liq, 2),
            is_hot=(vol_liq > 2.0 and momentum > 10),
        )
    
    async def run_scan_cycle(self):
        """One complete scan cycle."""
        self.batch_counter += 1
        self.current_batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"=== SCAN CYCLE #{self.batch_counter} | {self.current_batch_id} ===")
        
        try:
            # Fetch data in parallel
            pairs_task = self.fetch_solana_pairs()
            boosted_task = self.fetch_boosted_tokens()
            
            pairs, boosted = await asyncio.gather(pairs_task, boosted_task)
            
            # Enrich and filter
            quality_pairs = []
            for pair in pairs:
                try:
                    enriched = self.enrich_pair(pair)
                    
                    # Apply filters
                    if enriched.liquidity < settings.scanner.min_liquidity:
                        continue
                    if enriched.volume_24h < settings.scanner.min_volume_24h:
                        continue
                    
                    quality_pairs.append(enriched)
                    
                except Exception as e:
                    logger.warning(f"Pair enrichment failed: {e}")
                    continue
            
            logger.info(f"Quality pairs after filtering: {len(quality_pairs)}")
            
            # Persist to database + emit events
            saved = 0
            for enriched in quality_pairs:
                try:
                    # Save to DB
                    obj = await ScannerStateManager.create(enriched)
                    
                    # Emit event
                    await emit_token_discovered(
                        symbol=obj.symbol,
                        batch_id=self.current_batch_id,
                        payload=obj.model_dump(),
                    )
                    
                    saved += 1
                    
                except Exception as e:
                    logger.error(f"Failed to save {enriched.symbol}: {e}")
                    continue
            
            SCANNER_RUNS.labels(status="success").inc()
            logger.info(f"Scan complete: {saved}/{len(quality_pairs)} saved")
            
        except Exception as e:
            SCANNER_RUNS.labels(status="error").inc()
            logger.error(f"Scan cycle failed: {e}")
            set_agent_down("scanner")
    
    async def run(self):
        """Main loop."""
        logger.info("═══════════════════════════════════════")
        logger.info("🎯 ASYNC SCANNER V2 STARTED")
        logger.info("Database + Redis + Events")
        logger.info("═══════════════════════════════════════")
        
        # Init DB
        await init_db()
        
        self.running = True
        
        while self.running:
            try:
                await self.run_scan_cycle()
                set_agent_healthy("scanner")
                
                # Wait for next cycle
                await asyncio.sleep(settings.scanner.interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Scanner cancelled")
                break
            except Exception as e:
                logger.error(f"Scanner loop error: {e}")
                set_agent_down("scanner")
                await asyncio.sleep(10)
    
    def stop(self):
        self.running = False

async def main():
    async with AsyncScanner() as scanner:
        await scanner.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scanner stopped by user")
