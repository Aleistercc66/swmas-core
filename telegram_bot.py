import asyncio
import aiohttp
import logging
import json
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class TelegramAlertBot:
    """
    Telegram Alert Bot for Revenue Engine
    
    Sends alerts for:
    - New earnings
    - Phase transitions
    - Risk warnings
    - Daily/weekly summaries
    - Error notifications
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize bot session"""
        self.session = aiohttp.ClientSession()
        
        # Test connection
        me = await self._api_call('getMe')
        if me and me.get('ok'):
            logger.info(f"🤖 Telegram Bot connected: @{me['result']['username']}")
        else:
            logger.warning("⚠️ Telegram bot connection failed")
            
    async def _api_call(self, method: str, payload: dict = None) -> dict:
        """Make Telegram API call"""
        if not self.session:
            return {}
            
        url = f"{self.base_url}/{method}"
        try:
            async with self.session.post(url, json=payload) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return {}
            
    async def send_message(self, text: str, parse_mode: str = 'HTML') -> bool:
        """Send message to chat"""
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        result = await self._api_call('sendMessage', payload)
        return result.get('ok', False)
        
    async def send_earnings_alert(self, amount: float, source: str, total: float):
        """Send earnings alert"""
        emoji = {'yield': '🌾', 'airdrop': '🎁', 'mev': '⚡', 'social': '📱'}.get(source, '💰')
        
        text = f"""
{emoji} <b>NEW EARNINGS!</b>

💰 Amount: <code>${amount:.4f}</code>
📊 Source: {source.upper()}
💵 Total: <code>${total:.4f}</code>
⏰ {datetime.now().strftime('%H:%M:%S')}

🚀 Keep it running!
"""
        await self.send_message(text)
        
    async def send_phase_transition(self, old_phase: int, new_phase: int, capital: float):
        """Send phase transition alert"""
        phase_names = {1: 'SURVIVAL', 2: 'GROWTH', 3: 'SCALE'}
        
        text = f"""
🎉🎉🎉 <b>PHASE UPGRADE!</b> 🎉🎉🎉

📈 {phase_names.get(old_phase, 'Unknown')} → {phase_names.get(new_phase, 'Unknown')}
💰 Capital: <code>${capital:.2f}</code>

🔥 New strategies unlocked!
"""
        await self.send_message(text)
        
    async def send_daily_summary(self, stats: dict):
        """Send daily summary"""
        text = f"""
📊 <b>DAILY REVENUE SUMMARY</b>
📅 {datetime.now().strftime('%Y-%m-%d')}

💰 Total Earned: <code>${stats.get('total_earned', 0):.2f}</code>
📈 Cycles: {stats.get('cycles', 0)}
🎯 Capital: <code>${stats.get('capital', 0):.2f}</code>
📊 Effective APR: {stats.get('apr', 0):.2f}%

🚀 Revenue Streams:
🌾 Yield: ${stats.get('yield_earnings', 0):.2f}
🎁 Airdrops: ${stats.get('airdrop_earnings', 0):.2f}
⚡ MEV: ${stats.get('mev_earnings', 0):.2f}
📱 Social: ${stats.get('social_earnings', 0):.2f}

💵 Monthly Proj: <code>${stats.get('monthly_projection', 0):.2f}</code>
💵 Yearly Proj: <code>${stats.get('yearly_projection', 0):.2f}</code>
"""
        await self.send_message(text)
        
    async def send_risk_alert(self, risk_type: str, details: str):
        """Send risk warning"""
        text = f"""
⚠️ <b>RISK ALERT!</b> ⚠️

🚨 Type: {risk_type}
📋 Details: {details}
⏰ {datetime.now().strftime('%H:%M:%S')}

🔴 Action required!
"""
        await self.send_message(text)
        
    async def send_error(self, error: str, component: str):
        """Send error notification"""
        text = f"""
❌ <b>ERROR ALERT!</b> ❌

🔧 Component: {component}
📝 Error: <code>{error[:200]}</code>
⏰ {datetime.now().strftime('%H:%M:%S')}

⚠️ Check logs immediately!
"""
        await self.send_message(text)
        
    async def send_startup(self, capital: float, wallet: str):
        """Send startup notification"""
        text = f"""
🚀🚀🚀 <b>AUTONOMOUS REVENUE ENGINE STARTED!</b> 🚀🚀🚀

💰 Capital: <code>${capital:.2f}</code>
🔑 Wallet: <code>{wallet[:20]}...</code>
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 Active Revenue Streams:
🌾 Yield Farming
🎁 Airdrop Farming
⚡ MEV Extraction
📱 Social Tasks

📊 Dashboard: http://localhost:8080
📁 Logs: /root/.openclaw/workspace/logs/

🔥 Let's print money!
"""
        await self.send_message(text)
        
    async def close(self):
        """Close bot session"""
        if self.session:
            await self.session.close()


# ─── MAIN ───
async def main():
    """Test Telegram bot"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("⚠️  Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        return
        
    bot = TelegramAlertBot(bot_token, chat_id)
    await bot.initialize()
    
    await bot.send_startup(409.99, 'wallet_0x...')
    await bot.send_earnings_alert(0.3585, 'yield', 1.0255)
    await bot.send_daily_summary({
        'total_earned': 1.0255,
        'cycles': 3,
        'capital': 409.99,
        'apr': 0.25,
        'yield_earnings': 0.0006,
        'airdrop_earnings': 0.925,
        'mev_earnings': 0.10,
        'social_earnings': 0.0,
        'monthly_projection': 113.59,
        'yearly_projection': 1363.10
    })
    
    await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
