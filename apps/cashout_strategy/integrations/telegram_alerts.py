#!/usr/bin/env python3
"""
Telegram Alert System for Cashout Strategy
===========================================
Sends real-time alerts to Telegram when:
- New opportunities detected
- Golden Hour window activated
- OSINT intelligence found
- Cashout recommended
- Opportunity expired
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List
import aiohttp

logger = logging.getLogger("TelegramAlerts")


class TelegramAlerter:
    """
    Telegram Alert System
    =====================
    Sends formatted alerts to a Telegram chat
    """
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac"
        self.chat_id = chat_id or "158923136"
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_alert_time: Dict[str, datetime] = {}
        self._cooldown_minutes = 5  # Don't spam same alert
        
    async def _init_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def _send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram"""
        await self._init_session()
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        try:
            async with self.session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return True
                else:
                    error = await response.text()
                    logger.error(f"Telegram API error: {response.status} - {error}")
                    return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
    
    def _check_cooldown(self, alert_key: str) -> bool:
        """Check if enough time has passed since last alert"""
        now = datetime.now()
        if alert_key in self._last_alert_time:
            elapsed = (now - self._last_alert_time[alert_key]).total_seconds() / 60
            if elapsed < self._cooldown_minutes:
                return False
        self._last_alert_time[alert_key] = now
        return True
    
    async def alert_new_opportunity(self, opp: dict) -> bool:
        """Alert when new opportunity detected"""
        alert_key = f"opp_{opp['match_id']}"
        if not self._check_cooldown(alert_key):
            return False
        
        text = f"""🎯 <b>NEW OPPORTUNITY DETECTED</b>

⚽ <b>{opp['match_name']}</b>
🏆 {opp['league']}
⏰ Kickoff: {opp['kickoff']}

📉 Pinnacle Drop: <b>{opp['pinnacle_drop_pct']:.1f}%</b>
📊 Pinnacle: {opp['pinnacle_current']:.2f}
📈 Stoiximan: {opp['stoiximan_odds']:.2f}
💰 Value Edge: <b>+{opp['value_edge']:.2f}%</b>
🎯 Confidence: {opp['confidence']}/100

{'🔥 <b>GOLDEN HOUR ACTIVE!</b>' if opp['golden_hour'] else '⏳ Golden Hour: Not yet'}

📝 {opp['market']} - {opp['selection']}
"""
        return await self._send_message(text)
    
    async def alert_golden_hour(self, opp: dict) -> bool:
        """Alert when Golden Hour window is active"""
        alert_key = f"golden_{opp['match_id']}"
        if not self._check_cooldown(alert_key):
            return False
        
        text = f"""🔥🔥🔥 <b>GOLDEN HOUR ALERT!</b> 🔥🔥🔥

⚽ <b>{opp['match_name']}</b>
⏰ Kickoff: {opp['kickoff']}

💰 Value Edge: <b>+{opp['value_edge']:.2f}%</b>
🎯 Confidence: {opp['confidence']}/100

⚡ <b>CASHOUT NOW!</b>
60-90 minutes before kickoff is the optimal window.

📝 {opp['market']} - {opp['selection']}

⏳ Time remaining: {self._time_remaining(opp['kickoff'])}
"""
        return await self._send_message(text)
    
    async def alert_cashout_recommended(self, opp: dict) -> bool:
        """Alert when cashout is recommended"""
        alert_key = f"cashout_{opp['match_id']}"
        if not self._check_cooldown(alert_key):
            return False
        
        text = f"""💰 <b>CASHOUT RECOMMENDED</b>

⚽ <b>{opp['match_name']}</b>

📈 Expected Profit: <b>1-4%</b>
💰 Value Edge: +{opp['value_edge']:.2f}%
🎯 Confidence: {opp['confidence']}/100

✅ <b>Action:</b> Go to Stoiximan → My Bets → Cashout

⚠️ <b>Warning:</b> Cashout is mathematically -EV. 
Only use when you have positive edge from dropping odds.
"""
        return await self._send_message(text)
    
    async def alert_opportunity_expired(self, opp: dict) -> bool:
        """Alert when opportunity expires (kickoff passed)"""
        text = f"""⏰ <b>OPPORTUNITY EXPIRED</b>

⚽ {opp['match_name']}
⏰ Kickoff: {opp['kickoff']}

❌ Match started. No more pre-match cashout possible.

📊 Stats: {opp['pinnacle_drop_pct']:.1f}% drop | +{opp['value_edge']:.2f}% edge
"""
        return await self._send_message(text)
    
    async def alert_osint(self, match_name: str, report: dict) -> bool:
        """Alert with OSINT intelligence"""
        alert_key = f"osint_{match_name}_{report['type']}"
        if not self._check_cooldown(alert_key):
            return False
        
        type_emoji = {
            "injury": "🤕",
            "form": "📊",
            "sentiment": "🗣️",
            "odds_movement": "📈"
        }
        
        emoji = type_emoji.get(report['type'], "🔍")
        
        text = f"""{emoji} <b>OSINT: {report['type'].upper()}</b>

⚽ {match_name}
📡 Source: {report['source']}
🎯 Confidence: {report['confidence']}/100

{report['summary']}
"""
        return await self._send_message(text)
    
    async def alert_daily_summary(self, stats: dict) -> bool:
        """Daily summary alert"""
        text = f"""📊 <b>DAILY SUMMARY</b>

📅 {datetime.now().strftime('%Y-%m-%d')}

🔍 Opportunities Found: {stats['total_opportunities']}
✅ Executed: {stats['executed']}
💰 Avg Profit: {stats['avg_profit_pct']:.2f}%
📊 Win Rate: {stats['win_rate']:.1f}%

{'🔥 Great day!' if stats['total_opportunities'] > 5 else '⚡ Keep scanning!'}
"""
        return await self._send_message(text)
    
    def _time_remaining(self, kickoff_str) -> str:
        """Calculate time remaining until kickoff"""
        try:
            if isinstance(kickoff_str, str):
                kickoff = datetime.fromisoformat(kickoff_str.replace('Z', '+00:00'))
            else:
                kickoff = kickoff_str
            
            now = datetime.now()
            if kickoff.tzinfo and not now.tzinfo:
                now = now.replace(tzinfo=kickoff.tzinfo)
            
            diff = kickoff - now
            hours = int(diff.total_seconds() // 3600)
            minutes = int((diff.total_seconds() % 3600) // 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "Unknown"
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None


# Simple test
if __name__ == "__main__":
    async def test():
        alerter = TelegramAlerter()
        
        demo_opp = {
            "match_id": "match_001",
            "match_name": "Olympiacos vs PAOK",
            "league": "Super League Greece",
            "kickoff": (datetime.now() + timedelta(hours=1, minutes=30)).isoformat(),
            "market": "1X2",
            "selection": "Home",
            "pinnacle_open": 2.45,
            "pinnacle_current": 2.10,
            "pinnacle_drop_pct": 14.3,
            "stoiximan_odds": 2.25,
            "value_edge": 7.14,
            "confidence": 100,
            "golden_hour": True
        }
        
        print("Testing Telegram alerts...")
        result = await alerter.alert_new_opportunity(demo_opp)
        print(f"Alert sent: {result}")
        
        await alerter.close()
    
    asyncio.run(test())
