#!/usr/bin/env python3
"""📍 Position Monitor — Real-time position tracking with SL/TP monitoring."""
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from core import (
    get_logger, get_settings,
    get_event_bus, EventType, SwarmEvent,
    PositionOpenedEvent, PositionUpdatedEvent, PositionClosedEvent,
    set_agent_healthy, set_agent_down,
)

logger = get_logger("position_monitor")


class PositionMonitor:
    """Monitors open positions, checks SL/TP, publishes updates."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bus = None
        self.running = False
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.consumer_task = None
        self.monitor_task = None
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.bus = await get_event_bus()
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        if self.client:
            await self.client.aclose()
        if self.bus:
            await self.bus.disconnect()
    
    async def _get_live_price(self, symbol: str) -> Optional[float]:
        """Fetch live price from Jupiter or DexScreener."""
        try:
            # Try Jupiter first
            resp = await self.client.get(
                f"https://price.jup.ag/v6/price?ids={symbol}",
                headers={"Accept": "application/json"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                price_data = data.get("data", {}).get(symbol, {})
                price = price_data.get("price", 0)
                if price:
                    return float(price)
        except Exception:
            pass
        
        # Fallback: DexScreener
        try:
            resp = await self.client.get(
                f"https://api.dexscreener.com/latest/dex/search?q={symbol}",
                headers={"Accept": "application/json"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get("pairs", [])
                if pairs and isinstance(pairs, list):
                    return float(pairs[0].get("priceUsd", 0))
        except Exception as e:
            logger.warning(f"Price fetch failed for {symbol}: {e}")
        
        return None
    
    def _check_sl_tp(self, pos: Dict[str, Any], current_price: float, pnl: float) -> str:
        """Check if SL or TP hit."""
        stop_loss = pos.get("stop_loss", 0)
        take_profits = pos.get("take_profits", [])
        
        # Check stop loss
        if stop_loss > 0 and current_price <= stop_loss:
            return "BREACHED_SL"
        
        # Check take profits (in order)
        for i, tp in enumerate(take_profits):
            if tp > 0 and current_price >= tp:
                return f"HIT_TP{i+1}"
        
        return "OPEN"
    
    async def _close_position(self, trade_id: str, pos: Dict[str, Any], 
                              exit_price: float, reason: str):
        """Close a position and publish event."""
        entry = pos.get("entry_price", 0)
        size = pos.get("position_size_usd", 0)
        
        if entry > 0:
            pnl_percent = (exit_price - entry) / entry * 100
        else:
            pnl_percent = 0
        
        pnl_usd = size * (pnl_percent / 100)
        symbol = pos.get("symbol", "UNKNOWN")
        
        closed_event = PositionClosedEvent(
            trade_id=trade_id,
            symbol=symbol,
            close_price=exit_price,
            pnl_pct=round(pnl_percent, 2),
            pnl_usd=round(pnl_usd, 2),
            close_reason=reason,
        )
        
        await self.bus.publish_simple(
            event_type=EventType.POSITION_CLOSED,
            data=closed_event.model_dump(),
            source="position_monitor",
        )
        
        # Remove from active
        if trade_id in self.active_positions:
            del self.active_positions[trade_id]
        
        emoji = "🟢" if pnl_percent >= 0 else "🔴"
        logger.info(
            f"{emoji} POSITION CLOSED: {symbol} | {reason} | "
            f"PnL: {pnl_percent:+.2f}% (${pnl_usd:+.2f})"
        )
    
    async def handle_position_opened(self, event: SwarmEvent):
        """Handle new position opened."""
        try:
            data = event.data
            symbol = data.get("symbol", "UNKNOWN")
            entry = data.get("entry_price", 0)
            size = data.get("position_size_usd", 0)
            stop = data.get("stop_loss", 0)
            tps = data.get("take_profits", [])
            
            # Generate trade ID if not present
            trade_id = data.get("trade_id", f"pos_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{symbol}")
            
            self.active_positions[trade_id] = {
                "trade_id": trade_id,
                "symbol": symbol,
                "entry_price": entry,
                "position_size_usd": size,
                "stop_loss": stop,
                "take_profits": tps,
                "highest_price": entry,
                "lowest_price": entry,
                "opened_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"📍 NEW POSITION: {symbol} | Entry: ${entry:.8f} | "
                f"Size: ${size:.2f} | SL: ${stop:.8f} | TPs: {[f'${tp:.8f}' for tp in tps if tp > 0]}"
            )
            
        except Exception as e:
            logger.error(f"Position open handler error: {e}")
    
    async def _run_monitoring_cycle(self):
        """Main monitoring loop."""
        while self.running:
            try:
                if not self.active_positions:
                    await asyncio.sleep(5)
                    continue
                
                for trade_id, pos in list(self.active_positions.items()):
                    symbol = pos.get("symbol", "UNKNOWN")
                    entry = pos.get("entry_price", 0)
                    
                    # Get live price
                    current_price = await self._get_live_price(symbol)
                    
                    if current_price is None or current_price <= 0:
                        logger.warning(f"Could not get price for {symbol}, skipping")
                        continue
                    
                    # Calculate PnL
                    if entry > 0:
                        pnl_percent = (current_price - entry) / entry * 100
                    else:
                        pnl_percent = 0
                    
                    pnl_usd = pos.get("position_size_usd", 0) * (pnl_percent / 100)
                    
                    # Update highest/lowest
                    pos["highest_price"] = max(pos.get("highest_price", entry), current_price)
                    pos["lowest_price"] = min(pos.get("lowest_price", entry), current_price)
                    
                    # Check SL/TP
                    status = self._check_sl_tp(pos, current_price, pnl_percent)
                    
                    if status != "OPEN":
                        # Position closed!
                        await self._close_position(trade_id, pos, current_price, status)
                    else:
                        # Publish update
                        updated = PositionUpdatedEvent(
                            trade_id=trade_id,
                            symbol=symbol,
                            current_price=round(current_price, 8),
                            entry_price=entry,
                            pnl_percent=round(pnl_percent, 2),
                            pnl_usd=round(pnl_usd, 2),
                            status=status,
                            highest_price=pos["highest_price"],
                            lowest_price=pos["lowest_price"],
                        )
                        
                        await self.bus.publish_simple(
                            event_type=EventType.POSITION_UPDATED,
                            data=updated.model_dump(),
                            source="position_monitor",
                        )
                        
                        # Log every 30s or on significant moves
                        if abs(pnl_percent) > 5:
                            emoji = "🟢" if pnl_percent > 0 else "🔴"
                            logger.info(
                                f"{emoji} {symbol}: ${current_price:.8f} | "
                                f"PnL: {pnl_percent:+.2f}% (${pnl_usd:+.2f})"
                            )
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring cycle error: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        """Run position monitor."""
        logger.info("═══════════════════════════════════════")
        logger.info("📍 POSITION MONITOR STARTED")
        logger.info("Tracks SL/TP, publishes updates every 10s")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        # Subscribe to position opened events
        self.consumer_task = await self.bus.subscribe(
            event_type=EventType.POSITION_OPENED,
            consumer_name="position_monitor",
            handler=self.handle_position_opened,
        )
        
        # Start monitoring cycle
        self.monitor_task = asyncio.create_task(self._run_monitoring_cycle())
        
        logger.info("Waiting for positions...")
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Position monitor stopped")


async def main():
    async with PositionMonitor() as monitor:
        await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())