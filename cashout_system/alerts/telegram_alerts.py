#!/usr/bin/env python3
"""
Telegram Cash-Out Alerts
Sends smart alerts when cash-out becomes profitable
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cashout_alerts")


class TelegramCashOutAlerts:
    """Telegram alerts for cash-out opportunities"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.alert_history: List[Dict] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def send_alert(self, message: str, priority: str = "normal") -> bool:
        """Send Telegram alert"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Add emoji based on priority
            emoji = {"high": "🔥", "normal": "⚡", "low": "ℹ️"}.get(priority, "⚡")
            
            full_message = f"{emoji} **CASH-OUT ALERT** {emoji}\n\n{message}"
            
            payload = {
                "chat_id": self.chat_id,
                "text": full_message,
                "parse_mode": "Markdown",
                "disable_notification": priority == "low"
            }
            
            async with self.session.post(
                f"{self.base_url}/sendMessage",
                json=payload
            ) as response:
                if response.status == 200:
                    logger.info("Alert sent successfully")
                    self.alert_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "message": message,
                        "priority": priority
                    })
                    return True
                else:
                    logger.error(f"Failed to send alert: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
    async def send_cash_out_opportunity(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        current_score: str,
        original_odds: float,
        current_odds: float,
        stake: float,
        cash_out_value: float,
        roi: float,
        recommendation: str,
        bookmaker: str = "Stoiximan"
    ):
        """Send formatted cash-out opportunity alert"""
        
        priority = "high" if roi > 50 else "normal" if roi > 20 else "low"
        
        message = f"""
💰 **PROFIT OPPORTUNITY** 💰

🏠 **{home_team}** vs **{away_team}**
📊 Score: {current_score}
🏢 Bookmaker: {bookmaker}

📈 **ODDS**
Original: {original_odds:.2f} → Current: {current_odds:.2f}

💵 **CASH-OUT**
Stake: €{stake:.2f}
Value: €{cash_out_value:.2f}
**ROI: {roi:+.1f}%** 🎯

📋 **ACTION**
{recommendation}

⚡ Match ID: `{match_id}`
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_alert(message, priority)
    
    async def send_price_drift_alert(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        drift_pct: float,
        current_odds: float,
        recommendation: str
    ):
        """Alert when price drifts significantly"""
        
        priority = "high" if abs(drift_pct) > 20 else "normal"
        
        direction = "📉" if drift_pct < 0 else "📈"
        
        message = f"""
{direction} **PRICE DRIFT ALERT** {direction}

⚽ {home_team} vs {away_team}

📊 Drift: {drift_pct:+.1f}%
Current Odds: {current_odds:.2f}

📋 {recommendation}

⚡ Match ID: `{match_id}`
"""
        
        await self.send_alert(message, priority)
    
    async def send_optimal_cash_out_alert(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        current_score: str,
        cash_out_value: float,
        stake: float,
        roi: float,
        confidence: float
    ):
        """Alert when cash-out is optimal"""
        
        message = f"""
🔥 **OPTIMAL CASH-OUT DETECTED** 🔥

🏠 **{home_team}** vs **{away_team}**
📊 Score: {current_score}

💰 **CASH-OUT NOW!**
Value: €{cash_out_value:.2f}
Stake: €{stake:.2f}
ROI: {roi:+.1f}%
Confidence: {confidence:.0f}%

✅ **RECOMMENDATION**
🟢 **CASH OUT NOW!** 🟢
This is an optimal cash-out opportunity!

⚡ Match ID: `{match_id}`
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        
        await self.send_alert(message, "high")
    
    async def send_daily_summary(self, opportunities: List[Dict]):
        """Send daily summary of opportunities"""
        
        if not opportunities:
            message = "📊 No cash-out opportunities today. Keep watching! 👀"
        else:
            message = "📊 **DAILY CASH-OUT SUMMARY** 📊\n\n"
            
            for i, opp in enumerate(opportunities[:10], 1):
                emoji = "🟢" if opp.get('roi', 0) > 20 else "🟡" if opp.get('roi', 0) > 0 else "🔴"
                message += f"{emoji} {opp['home']} vs {opp['away']}: {opp['roi']:+.1f}%\n"
            
            message += f"\nTotal: {len(opportunities)} opportunities"
        
        await self.send_alert(message, "normal")
    
    def get_alert_history(self) -> List[Dict]:
        """Get alert history"""
        return self.alert_history


class DesktopNotifier:
    """Desktop notifications with sound"""
    
    def __init__(self):
        self.enabled = True
        
    def notify(self, title: str, message: str, sound: bool = True):
        """Send desktop notification"""
        try:
            # Try using notify2 (Linux)
            import notify2
            notify2.init("CashOut System")
            n = notify2.Notification(title, message)
            n.show()
            
            if sound:
                self._play_sound()
                
        except ImportError:
            # Fallback to plyer
            try:
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message,
                    app_name="CashOut System",
                    timeout=10
                )
                if sound:
                    self._play_sound()
            except Exception as e:
                logger.warning(f"Desktop notification failed: {e}")
    
    def _play_sound(self):
        """Play alert sound"""
        try:
            import os
            # Try different sound methods
            os.system('paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null &')
        except:
            pass
    
    def notify_cash_out_opportunity(self, home: str, away: str, roi: float):
        """Notify about cash-out opportunity"""
        self.notify(
            "💰 Cash-Out Opportunity!",
            f"{home} vs {away}: {roi:+.1f}% ROI",
            sound=True
        )
    
    def notify_optimal_cash_out(self, home: str, away: str, value: float):
        """Notify about optimal cash-out"""
        self.notify(
            "🔥 OPTIMAL CASH-OUT!",
            f"{home} vs {away}: €{value:.2f} available!",
            sound=True
        )


# Example usage
async def main():
    """Test alerts"""
    # Use the user's bot
    bot_token = "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac"
    chat_id = "158923136"  # G:A.C's chat ID
    
    async with TelegramCashOutAlerts(bot_token, chat_id) as alerts:
        await alerts.send_cash_out_opportunity(
            match_id="12345",
            home_team="Olympiacos",
            away_team="PAOK",
            current_score="2-1",
            original_odds=2.50,
            current_odds=1.80,
            stake=100.0,
            cash_out_value=135.0,
            roi=35.0,
            recommendation="🟢 GOOD CASH-OUT - Solid profit available",
            bookmaker="Stoiximan"
        )
        
        print("Test alert sent!")


if __name__ == "__main__":
    asyncio.run(main())