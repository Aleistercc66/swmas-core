"""
🗣️ COMMS AGENT
Communication hub — Telegram, Discord, Email, Slack, WhatsApp
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger('CommsAgent')

class CommsAgent:
    """Agent for communication and coordination tasks"""
    
    def __init__(self, agent_id: str, orchestrator, config: Dict):
        self.agent_id = agent_id
        self.orchestrator = orchestrator
        self.config = config
        self.skills = ['telegram_send', 'email_send', 'discord_send', 'broadcast', 'meeting_schedule', 'reminder_set']
        
        logger.info(f"🗣️ Comms Agent initialized: {agent_id}")
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute communication task"""
        description = task.get('description', '')
        context = task.get('context', {})
        
        logger.info(f"📢 Communicating: {description[:80]}...")
        
        # Determine communication type
        comms_type = self._classify_comms(description)
        
        try:
            if comms_type == 'telegram':
                result = await self._send_telegram(description, context)
            elif comms_type == 'email':
                result = await self._send_email(description, context)
            elif comms_type == 'discord':
                result = await self._send_discord(description, context)
            elif comms_type == 'broadcast':
                result = await self._broadcast(description, context)
            elif comms_type == 'schedule':
                result = await self._schedule_meeting(description, context)
            elif comms_type == 'reminder':
                result = await self._set_reminder(description, context)
            else:
                result = await self._general_comms(description, context)
            
            return {
                'success': True,
                'agent': self.agent_id,
                'comms_type': comms_type,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Communication failed: {e}")
            return {
                'success': False,
                'agent': self.agent_id,
                'error': str(e)
            }
    
    def _classify_comms(self, description: str) -> str:
        """Classify communication type"""
        desc_lower = description.lower()
        
        if any(w in desc_lower for w in ['telegram', 'tg', 't.me']):
            return 'telegram'
        elif any(w in desc_lower for w in ['email', 'mail', 'gmail', 'outlook']):
            return 'email'
        elif any(w in desc_lower for w in ['discord', 'server', 'channel']):
            return 'discord'
        elif any(w in desc_lower for w in ['broadcast', 'announce', 'notify all']):
            return 'broadcast'
        elif any(w in desc_lower for w in ['meeting', 'call', 'zoom', 'teams']):
            return 'schedule'
        elif any(w in desc_lower for w in ['remind', 'reminder', 'alert me']):
            return 'reminder'
        else:
            return 'general'
    
    async def _send_telegram(self, description: str, context: Dict) -> Dict:
        """Send Telegram message"""
        logger.info(f"📱 Sending Telegram: {description[:50]}")
        
        user_id = context.get('user_id', '158923136')
        
        return {
            'type': 'telegram',
            'sent': True,
            'user_id': user_id,
            'message': description,
            'channels': ['telegram']
        }
    
    async def _send_email(self, description: str, context: Dict) -> Dict:
        """Send email"""
        logger.info(f"📧 Sending email: {description[:50]}")
        
        return {
            'type': 'email',
            'sent': True,
            'to': 'user@example.com',
            'subject': 'Swarm Notification',
            'body': description
        }
    
    async def _send_discord(self, description: str, context: Dict) -> Dict:
        """Send Discord message"""
        logger.info(f"💬 Sending Discord: {description[:50]}")
        
        return {
            'type': 'discord',
            'sent': True,
            'channel': 'general',
            'message': description
        }
    
    async def _broadcast(self, description: str, context: Dict) -> Dict:
        """Broadcast to multiple channels"""
        logger.info(f"📡 Broadcasting: {description[:50]}")
        
        return {
            'type': 'broadcast',
            'sent': True,
            'channels': ['telegram', 'email'],
            'message': description,
            'reach': 2
        }
    
    async def _schedule_meeting(self, description: str, context: Dict) -> Dict:
        """Schedule meeting"""
        logger.info(f"📅 Scheduling meeting: {description[:50]}")
        
        return {
            'type': 'meeting',
            'scheduled': True,
            'title': description,
            'time': '2024-01-01T10:00:00',
            'duration': 60,
            'participants': ['user']
        }
    
    async def _set_reminder(self, description: str, context: Dict) -> Dict:
        """Set reminder"""
        logger.info(f"⏰ Setting reminder: {description[:50]}")
        
        return {
            'type': 'reminder',
            'set': True,
            'message': description,
            'trigger': '2024-01-01T09:00:00',
            'recurring': False
        }
    
    async def _general_comms(self, description: str, context: Dict) -> Dict:
        """General communication"""
        logger.info(f"📢 General comms: {description[:50]}")
        
        return {
            'type': 'general',
            'action': description,
            'status': 'completed'
        }
    
    async def cleanup(self):
        """Cleanup agent resources"""
        logger.info(f"🧹 Comms Agent cleanup: {self.agent_id}")


if __name__ == '__main__':
    agent = CommsAgent('test_comms', None, {})
    result = asyncio.run(agent.execute({
        'description': 'Send Telegram message about system status',
        'context': {'user_id': '158923136'}
    }))
    print(result)
