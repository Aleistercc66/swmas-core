#!/usr/bin/env python3
"""
📨 AGENT V2: TELEGRAM BOT — Interactive trading assistant
Replaces poll_telegram.py. Event-driven, async, confirmation handling.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from core import (
    settings, get_logger,
    PortfolioManager, PositionStateManager, RiskStateManager,
    emit_alert,
    ALERTS_SENT, ERRORS_TOTAL,
)

logger = get_logger("telegram_bot")

class AsyncTelegramBot:
    """Production-grade Telegram bot with confirmation handling."""
    
    def __init__(self):
        self.token = settings.telegram.bot_token
        self.chat_id = settings.telegram.chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.running = False
        self.last_update_id = 0
        self.executor_ref = None  # Set externally
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send message to configured chat."""
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                )
                response.raise_for_status()
                ALERTS_SENT.labels(type="text").inc()
                return True
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            ERRORS_TOTAL.labels(agent="telegram_bot", type="send").inc()
            return False
    
    async def send_signal_alert(self, risk, scanner_output) -> bool:
        """Send formatted trading signal."""
        if not risk or not scanner_output:
            return False
        
        tier_emoji = "🟢" if risk.tier == "TIER_1" else "🟡" if risk.tier == "TIER_2" else "🟠"
        
        msg = f"""{tier_emoji} <b>TRADING SIGNAL — {risk.tier}</b>

<b>Token:</b> {risk.symbol}
<b>Price:</b> ${risk.metadata.get('entry_price', 0):.8f}
<b>24h Change:</b> {risk.metadata.get('change_24h', 0):+.1f}%

<b>📊 Risk Assessment:</b>
• Composite Score: {risk.composite_score:.1f}/100
• Confidence: {risk.confidence:.1f}%
• Volatility: {risk.volatility_regime}

<b>🎯 Levels:</b>
• Entry: ${risk.entry_price:.8f}
• Stop: ${risk.stop_loss_price:.8f} ({risk.stop_distance_pct:.1f}%)
• TP1: ${risk.take_profit_1:.8f} (RR {risk.risk_reward_ratio:.1f})
• TP2: ${risk.take_profit_2:.8f} (RR {risk.risk_reward_ratio:.1f})
• TP3: ${risk.take_profit_3:.8f} (RR {risk.risk_reward_ratio:.1f})

<b>📈 Metrics:</b>
• Liquidity Tier: {risk.liquidity_tier}
• 24h Volume: N/A
• ATR Proxy: {risk.atr_proxy:.1f}%
• Position Size: {risk.position_size_pct:.1f}%

<i>{"Awaiting confirmation..." if risk.tier == "TIER_1" else "Auto-execution enabled"}</i>
"""
        
        await emit_alert(
            symbol=risk.symbol,
            alert_type="signal",
            title=f"{risk.tier} Signal: {risk.symbol}",
            body=msg,
            correlation_id=str(risk.id),
        )
        
        return await self.send_message(msg)
    
    async def send_portfolio_update(self) -> bool:
        """Send portfolio status."""
        portfolio = await PortfolioManager.get_summary()
        
        positions_text = ""
        for pos in portfolio.get("open_positions", []):
            pnl_emoji = "🟢" if pos.get("pnl_pct", 0) >= 0 else "🔴"
            positions_text += f"\n{pnl_emoji} {pos['symbol']}: ${pos['current_price']:.8f} | PnL {pos['pnl_pct']:+.1f}%"
        
        if not positions_text:
            positions_text = "\nNo open positions"
        
        msg = f"""📊 <b>PORTFOLIO UPDATE</b>

<b>Balance:</b> ${portfolio['balance']:,.2f}
<b>Total PnL:</b> ${portfolio['total_pnl']:+.2f}
<b>Win Rate:</b> {portfolio['win_rate']:.1f}%
<b>Trades Today:</b> {portfolio['daily_trades']}
<b>Open Positions:</b> {portfolio['open_positions_count']}

<b>📈 Positions:</b>{positions_text}

<i>Updated: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC</i>
"""
        
        return await self.send_message(msg)
    
    async def poll_messages(self):
        """Poll for user commands."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/getUpdates",
                    params={
                        "offset": self.last_update_id + 1,
                        "limit": 10,
                    },
                    timeout=10,
                )
                
                data = response.json()
                if not data.get("ok"):
                    return
                
                for update in data.get("result", []):
                    self.last_update_id = update["update_id"]
                    
                    message = update.get("message", {})
                    text = message.get("text", "").strip().upper()
                    chat_id = str(message.get("chat", {}).get("id", ""))
                    
                    # Only respond to configured chat
                    if chat_id != self.chat_id:
                        continue
                    
                    # Commands
                    if text == "/PORTFOLIO":
                        await self.send_portfolio_update()
                    
                    elif text == "/POSITIONS":
                        positions = await PositionStateManager.get_open_positions()
                        if positions:
                            msg = "📋 <b>OPEN POSITIONS</b>\n\n"
                            for p in positions:
                                msg += f"#{p.id} {p.symbol}: ${p.current_price:.8f} | PnL {p.current_pnl_pct:+.1f}%\n"
                            await self.send_message(msg)
                        else:
                            await self.send_message("No open positions")
                    
                    elif text == "/CONFIRM":
                        await self.send_message("Send /CONFIRM \u003cID\u003e to confirm a TIER_1 trade")
                    
                    elif text.startswith("/CONFIRM "):
                        parts = text.split()
                        if len(parts) >= 2:
                            risk_id = int(parts[1])
                            if self.executor_ref:
                                position = await self.executor_ref.confirm_pending(risk_id)
                                if position:
                                    await self.send_message(
                                        f"✅ Confirmed! Position #{position.id} opened: {position.symbol}"
                                    )
                                else:
                                    await self.send_message("❌ Confirmation failed — signal expired or invalid")
                            else:
                                await self.send_message("Executor not connected")
                    
                    elif text == "/STATUS":
                        await self.send_portfolio_update()
                    
                    elif text == "/HELP":
                        help_msg = """🤖 <b>TRADING BOT COMMANDS</b>

/portfolio — Portfolio status
/positions — Open positions list
/confirm \u003cID\u003e — Confirm TIER_1 trade
/status — System status
/help — This message

<i>Auto-execution: TIER_2+ | Manual confirm: TIER_1</i>
"""
                        await self.send_message(help_msg)
                    
        except Exception as e:
            logger.warning(f"Message poll error: {e}")
    
    async def run(self):
        """Main loop."""
        logger.info("═══════════════════════════════════════")
        logger.info("📨 ASYNC TELEGRAM BOT V2 STARTED")
        logger.info(f"Chat: {self.chat_id}")
        logger.info("═══════════════════════════════════════")
        
        # Send startup message
        await self.send_message(
            "🚀 <b>Crypto Trading Swarm V2 Online</b>\n\n"
            "Scanner → Validator → Risk → Executor → Monitor\n"
            "All agents running with atomic transactions.\n\n"
            "Send /help for commands"
        )
        
        self.running = True
        
        while self.running:
            try:
                await self.poll_messages()
                await asyncio.sleep(2)  # 2s poll interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Bot loop error: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        self.running = False

async def main():
    bot = AsyncTelegramBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Telegram bot stopped")
