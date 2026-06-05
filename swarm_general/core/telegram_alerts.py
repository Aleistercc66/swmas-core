#!/usr/bin/env python3
"""
📱 TELEGRAM ALERT SENDER
Διαβάζει alerts από profit engine και στέλνει στο Telegram.
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('TelegramAlert')

# Telegram Bot Config
BOT_TOKEN = "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac"
USER_ID = "158923136"  # Gerasimos user ID

class TelegramAlertSender:
    """Στέλνει trading alerts στο Telegram"""
    
    def __init__(self):
        self.swarm_dir = Path('/root/.openclaw/workspace/swarm_general')
        self.data_dir = self.swarm_dir / 'data'
        self.last_alert_file = self.data_dir / 'latest_alert.json'
        self.sent_alerts_file = self.data_dir / 'sent_alerts.jsonl'
        
        self.last_sent_id = None
        self.alerts_sent = 0
        
        logger.info("📱 Telegram Alert Sender initialized")
    
    async def start(self):
        """Ξεκινάει το alert sender loop"""
        logger.info("🚀 Starting Telegram Alert Sender...")
        
        while True:
            try:
                await self._check_and_send()
                await asyncio.sleep(15)  # Check every 15 seconds
            except Exception as e:
                logger.error(f"Alert sender error: {e}")
                await asyncio.sleep(5)
    
    async def _check_and_send(self):
        """Ελέγχει για νέα alerts και τα στέλνει"""
        if not self.last_alert_file.exists():
            return
        
        try:
            with open(self.last_alert_file, 'r') as f:
                alert = json.load(f)
            
            # Check if already sent
            alert_id = alert.get('timestamp', '') + alert.get('token', '')
            if alert_id == self.last_sent_id:
                return
            
            # Send to Telegram
            await self._send_telegram_alert(alert)
            
            # Mark as sent
            self.last_sent_id = alert_id
            self.alerts_sent += 1
            
            # Log sent alert
            with open(self.sent_alerts_file, 'a') as f:
                f.write(json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'alert': alert,
                    'status': 'sent'
                }) + '\n')
            
            logger.info(f"✅ Telegram alert sent for {alert.get('token', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error checking/sending alert: {e}")
    
    async def _send_telegram_alert(self, alert: dict):
        """Στέλνει alert στο Telegram μέσω HTTP API"""
        import aiohttp
        
        # 🚫 HARD BLOCK: Only crypto/DexScreener alerts allowed
        message = alert.get('message', self._format_message(alert))
        BLOCKED_KEYWORDS = ['polymarket', 'prediction', 'fifa', 'world cup', 'nba', 'nfl', 'sports', 'election', 'vote', 'political']
        msg_lower = message.lower()
        for kw in BLOCKED_KEYWORDS:
            if kw in msg_lower:
                logger.warning(f"🚫 BLOCKED alert containing '{kw}' — Polymarket/prediction alerts are DISABLED")
                return
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': USER_ID,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('ok'):
                            logger.info("📤 Alert delivered to Telegram")
                        else:
                            logger.error(f"Telegram error: {result}")
                    else:
                        logger.error(f"HTTP error: {response.status}")
        except Exception as e:
            logger.error(f"Error sending to Telegram: {e}")
    
    def _format_message(self, alert: dict) -> str:
        """Format message for Telegram"""
        token = alert.get('token', 'Unknown')
        ai_score = alert.get('ai_score', 0)
        profit = alert.get('profit_potential', 0)
        risk = alert.get('risk_score', 0)
        confidence = alert.get('confidence', '')
        address = alert.get('address', '')
        
        return f"""
💰 **SWARM PROFIT ALERT**

🏷️ Token: `{token}`
🔗 Address: `{address[:20]}...`
📊 AI Score: {ai_score}/100
📈 Profit Potential: +{profit}%
⚠️ Risk Score: {risk}/100
🎯 Confidence: {confidence}

📍 Entry: {alert.get('entry', 0)}
🛑 Stop Loss: {alert.get('stop_loss', 0)}
✅ TP1: {alert.get('take_profit_1', 0)}
✅ TP2: {alert.get('take_profit_2', 0)}
✅ TP3: {alert.get('take_profit_3', 0)}

💵 Position Size: ${alert.get('position_size', 0)}
🔗 Chain: {alert.get('chain', 'unknown')}
📡 Source: {alert.get('source', 'unknown')}

🔥 **{confidence} signal detected!**
        """.strip()


async def main():
    sender = TelegramAlertSender()
    try:
        await sender.start()
    except KeyboardInterrupt:
        logger.info("🛑 Telegram Alert Sender stopped")

if __name__ == '__main__':
    asyncio.run(main())
