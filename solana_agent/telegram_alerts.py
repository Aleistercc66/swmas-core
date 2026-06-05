#!/usr/bin/env python3
"""
Telegram Alert System - Ειδοποιήσεις για ευκαιρίες
Στέλνει alerts στο Telegram σε πραγματικό χρόνο.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class AlertConfig:
    """Configuration για alerts."""
    bot_token: str
    chat_id: str
    
    # Alert thresholds
    min_opportunity_score: float = 60
    min_target_return: float = 15
    max_alerts_per_hour: int = 10
    
    # Cooldown
    alert_cooldown_seconds: float = 300  # 5 min between alerts for same token
    
    # Formatting
    use_emojis: bool = True
    show_technical_details: bool = True


class TelegramAlerter:
    """
    Alerter που στέλνει ειδοποιήσεις μέσω Telegram bot.
    """
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.last_alert_time: Dict[str, float] = {}  # token -> last alert time
        self.alerts_sent_this_hour: int = 0
        self.hour_start: float = time.time()
        
        # Telegram API
        self.api_base = f"https://api.telegram.org/bot{config.bot_token}"
    
    def _can_alert(self, token_address: str) -> bool:
        """Check αν μπορούμε να στείλουμε alert για αυτό το token."""
        
        # Check hourly limit
        if time.time() - self.hour_start >= 3600:
            self.alerts_sent_this_hour = 0
            self.hour_start = time.time()
        
        if self.alerts_sent_this_hour >= self.config.max_alerts_per_hour:
            return False
        
        # Check cooldown
        last_alert = self.last_alert_time.get(token_address, 0)
        if time.time() - last_alert < self.config.alert_cooldown_seconds:
            return False
        
        return True
    
    async def send_opportunity_alert(self, session: aiohttp.ClientSession,
                                      setup: Any) -> bool:
        """Στείλε alert για ευκαιρία."""
        
        token_address = setup.token_address
        
        if not self._can_alert(token_address):
            return False
        
        # Build message
        message = self._build_opportunity_message(setup)
        
        # Send
        try:
            payload = {
                "chat_id": self.config.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
            
            async with session.post(
                f"{self.api_base}/sendMessage",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    self.last_alert_time[token_address] = time.time()
                    self.alerts_sent_this_hour += 1
                    print(f"📨 Alert sent: {setup.symbol}")
                    return True
                else:
                    print(f"❌ Alert failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Alert error: {e}")
            return False
    
    def _build_opportunity_message(self, setup: Any) -> str:
        """Φτιάξε το alert message."""
        
        emoji = "🚀" if setup.target_return >= 25 else "⚡" if setup.target_return >= 20 else "📈"
        urgency = "🔥 URGENT" if getattr(setup, 'urgency', '') == "urgent" else ""
        
        message = f"""
{emoji} **SOLANA OPPORTUNITY: {setup.symbol}** {emoji} {urgency}

📊 **Setup:** {setup.catalyst.upper() if hasattr(setup, 'catalyst') else 'MOMENTUM'}
🎯 **Target:** +{setup.target_return:.1f}%
⏱️ **Timeframe:** {setup.timeframe if hasattr(setup, 'timeframe') else '2-6h'}
🔥 **Confidence:** {setup.opportunity_score:.0f}/100
⚖️ **Risk Score:** {setup.risk_score:.0f}/100

💰 **Entry Strategy:** {setup.entry_strategy if hasattr(setup, 'entry_strategy') else 'Immediate'}
   Price: ${setup.entry_price:.6f}

🎯 **Profit Targets:**
   🥇 TP1 (+{setup.tp1:.1f}%)
   🥈 TP2 (+{setup.tp2:.1f}%)
   🥉 TP3 (+{setup.tp3:.1f}%)

🛑 **Stop Loss:** {setup.stop_loss:.1f}%
⚖️ **Risk:Reward:** 1:{setup.risk_reward:.1f}
📏 **Position Size:** {setup.position_size_pct:.1f}% of portfolio

📍 **Contract:** `{setup.token_address}`

⏰ **Valid until:** {time.strftime('%H:%M', time.localtime(setup.expires_at)) if hasattr(setup, 'expires_at') and setup.expires_at else 'Next scan'}

💡 *Always DYOR. This is not financial advice.*
"""
        return message.strip()
    
    async def send_portfolio_update(self, session: aiohttp.ClientSession,
                                     portfolio: Dict):
        """Στείλε portfolio update."""
        
        positions = portfolio.get("positions", [])
        total_pnl = portfolio.get("unrealized_pnl_pct", 0)
        
        emoji = "🟢" if total_pnl >= 0 else "🔴"
        
        message = f"""
📊 **PORTFOLIO UPDATE** {emoji}

💰 **Total PnL:** {total_pnl:+.1f}%
📈 **Daily PnL:** {portfolio.get('daily_pnl_sol', 0):+.3f} SOL
💼 **Positions Open:** {len(positions)}

"""
        
        for pos in positions:
            pnl_emoji = "🟢" if pos.get("pnl_pct", 0) >= 0 else "🔴"
            message += f"""
{pnl_emoji} **{pos.get('symbol', 'Unknown')}**
   Entry: ${pos.get('entry', 0):.6f}
   Current: ${pos.get('current', 0):.6f}
   PnL: {pos.get('pnl_pct', 0):+.1f}%
"""
        
        try:
            payload = {
                "chat_id": self.config.chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }
            
            async with session.post(
                f"{self.api_base}/sendMessage",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"❌ Portfolio update error: {e}")
            return False
    
    async def send_trade_notification(self, session: aiohttp.ClientSession,
                                       trade: Dict):
        """Στείλε notification για executed trade."""
        
        pnl_pct = trade.get("pnl_pct", 0)
        emoji = "✅" if pnl_pct > 0 else "❌"
        reason = trade.get("reason", "")
        
        message = f"""
{emoji} **TRADE CLOSED: {trade.get('symbol', 'Unknown')}** {emoji}

📊 **Result:** {pnl_pct:+.1f}%
💰 **PnL:** {trade.get('pnl_sol', 0):+.3f} SOL
📝 **Reason:** {reason}

Entry: ${trade.get('entry_price', 0):.6f}
Exit: ${trade.get('exit_price', 0):.6f}
"""
        
        try:
            payload = {
                "chat_id": self.config.chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }
            
            async with session.post(
                f"{self.api_base}/sendMessage",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"❌ Trade notification error: {e}")
            return False
    
    async def send_risk_alert(self, session: aiohttp.ClientSession,
                              risk_msg: str):
        """Στείλε risk alert."""
        
        message = f"""
🚫 **RISK ALERT** 🚫

{risk_msg}

Trading halted until further notice.
"""
        
        try:
            payload = {
                "chat_id": self.config.chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }
            
            async with session.post(
                f"{self.api_base}/sendMessage",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"❌ Risk alert error: {e}")
            return False
    
    async def send_daily_summary(self, session: aiohttp.ClientSession,
                                  stats: Dict):
        """Στείλε daily summary."""
        
        pnl = stats.get("daily_pnl_pct", 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        
        message = f"""
📅 **DAILY SUMMARY** {emoji}

📊 **PnL:** {pnl:+.1f}%
📈 **Trades:** {stats.get("trades", 0)}
✅ **Wins:** {stats.get("wins", 0)}
❌ **Losses:** {stats.get("losses", 0)}
📈 **Win Rate:** {stats.get("win_rate", 0):.1%}

{'🎯 Daily target reached!' if pnl >= 15 else ''}
{'⚠️ Daily loss limit hit!' if pnl <= -5 else ''}
"""
        
        try:
            payload = {
                "chat_id": self.config.chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }
            
            async with session.post(
                f"{self.api_base}/sendMessage",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"❌ Summary error: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    config = AlertConfig(
        bot_token="YOUR_BOT_TOKEN",
        chat_id="YOUR_CHAT_ID",
    )
    
    alerter = TelegramAlerter(config)
    print("📨 Telegram Alerter initialized")
    print(f"   Chat ID: {config.chat_id}")
    print(f"   Min score: {config.min_opportunity_score}")
    print(f"   Max alerts/hour: {config.max_alerts_per_hour}")
