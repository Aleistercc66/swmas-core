#!/usr/bin/env python3
"""📱 Telegram Event Handler — listens for trade events, sends alerts."""
import asyncio
import sys
sys.path.insert(0, "/root/.openclaw/workspace/agents")

from core import get_logger, get_settings, get_event_bus, EventType, SwarmEvent
from core.events import TradeDecision, AlertEvent

logger = get_logger("telegram_handler")


class TelegramEventHandler:
    """Listens for POSITION_OPENED and ALERT events, formats messages."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bus = None
        self.running = False
        self.tasks = []
    
    async def __aenter__(self):
        self.bus = await get_event_bus()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self.bus:
            await self.bus.disconnect()
    
    def _format_trade_message(self, decision: dict) -> str:
        """Format a trade decision for Telegram."""
        symbol = decision.get("symbol", "UNKNOWN")
        tier = decision.get("tier", "TIER_3")
        entry = decision.get("entry_price", 0)
        stop = decision.get("stop_loss", 0)
        tps = decision.get("take_profits", [])
        confidence = decision.get("confidence", 0)
        rr = decision.get("risk_reward", 0)
        size = decision.get("position_size_usd", 0)
        portfolio_heat = decision.get("portfolio_heat_pct", 0)
        
        tps_str = " / ".join([f"${tp:.8f}" for tp in tps]) if tps else "N/A"
        
        return f"""
🟢 <b>NEW SIGNAL APPROVED</b>

<b>Token:</b> {symbol} | <b>Tier:</b> {tier}
<b>Confidence:</b> {confidence:.1f}% | <b>R/R:</b> {rr:.1f}

<b>📊 Levels:</b>
• Entry: ${entry:.8f}
• Stop: ${stop:.8f}
• TPs: {tps_str}

<b>💰 Size:</b> ${size:.2f}
<b>🔥 Portfolio Heat:</b> {portfolio_heat:.1f}%

<i>Time: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}</i>
"""
    
    def _format_alert_message(self, alert: dict) -> str:
        """Format an alert message."""
        alert_type = alert.get("alert_type", "INFO")
        symbol = alert.get("symbol", "")
        message = alert.get("message", "")
        data = alert.get("data", {})
        
        emoji = {"SIGNAL": "🟢", "STOP_HIT": "🔴", "TAKE_PROFIT": "🎯", 
                "ERROR": "⚠️", "INFO": "ℹ️", "CIRCUIT_BREAKER": "🛑"}.get(alert_type, "ℹ️")
        
        return f"""
{emoji} <b>{alert_type}</b>

<b>{symbol}</b>
{message}

<i>{__import__('datetime').datetime.now().strftime('%H:%M:%S')}</i>
"""
    
    async def handle_trade_approved(self, event: SwarmEvent):
        """Handle approved trades."""
        try:
            logger.info(f"Formatting trade alert for {event.data.get('symbol', '?')}")
            message = self._format_trade_message(event.data)
            
            # Here you would send to Telegram bot
            # For now, log the formatted message
            logger.info(f"TELEGRAM MESSAGE:\n{message}")
            
            # TODO: Integrate with actual Telegram bot
            # if self.settings.telegram_bot_token:
            #     await send_telegram_message(self.settings.telegram_chat_id, message)
            
        except Exception as e:
            logger.error(f"Telegram handler error: {e}")
    
    async def handle_alert(self, event: SwarmEvent):
        """Handle general alerts."""
        try:
            message = self._format_alert_message(event.data)
            logger.info(f"ALERT MESSAGE:\n{message}")
        except Exception as e:
            logger.error(f"Alert handler error: {e}")
    
    async def run(self):
        """Run Telegram handler."""
        logger.info("═══════════════════════════════════════")
        logger.info("📱 TELEGRAM EVENT HANDLER STARTED")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        # Subscribe to trade approvals
        task1 = await self.bus.subscribe(
            event_type=EventType.POSITION_OPENED,
            consumer_name="telegram_trades",
            handler=self.handle_trade_approved,
        )
        self.tasks.append(task1)
        
        # Subscribe to alerts
        task2 = await self.bus.subscribe(
            event_type=EventType.ALERT,
            consumer_name="telegram_alerts",
            handler=self.handle_alert,
        )
        self.tasks.append(task2)
        
        logger.info("Listening for trade approvals and alerts...")
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Telegram handler stopped")


async def main():
    async with TelegramEventHandler() as handler:
        await handler.run()


if __name__ == "__main__":
    asyncio.run(main())
