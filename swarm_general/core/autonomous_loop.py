"""
🔄 AUTONOMOUS LOOP
Self-directed operations for the General Purpose Swarm
Proactive tasks, learning, and evolution
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any

logger = logging.getLogger('AutonomousLoop')

class AutonomousLoop:
    """Autonomous operation loop for the swarm"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.running = False
        self.loop_count = 0
        self.last_proactive_check = None
        
        # Autonomous task templates
        self.proactive_tasks = [
            {
                'type': 'research',
                'description': 'Check latest trends in AI and technology',
                'interval_hours': 6,
                'priority': 'low'
            },
            {
                'type': 'monitor',
                'description': 'Health check on all swarm components',
                'interval_hours': 1,
                'priority': 'normal'
            },
            {
                'type': 'learn',
                'description': 'Review completed tasks for patterns',
                'interval_hours': 12,
                'priority': 'low'
            },
            {
                'type': 'analysis',
                'description': 'Analyze swarm performance metrics',
                'interval_hours': 4,
                'priority': 'normal'
            },
            {
                'type': 'automation',
                'description': 'Clean up temporary files and logs',
                'interval_hours': 24,
                'priority': 'low'
            },
            {
                'type': 'content',
                'description': 'Generate daily summary report',
                'interval_hours': 24,
                'priority': 'normal'
            },
            {
                'type': 'research',
                'description': 'Discover new APIs and tools',
                'interval_hours': 48,
                'priority': 'low'
            },
            {
                'type': 'monitor',
                'description': 'Check external service availability',
                'interval_hours': 2,
                'priority': 'high'
            }
        ]
        
        logger.info("🔄 Autonomous Loop initialized")
    
    async def run(self):
        """Main autonomous loop"""
        self.running = True
        logger.info("🚀 Autonomous Loop started")
        
        while self.running:
            try:
                self.loop_count += 1
                
                # Run proactive checks
                await self._run_proactive_checks()
                
                # Run maintenance
                await self._run_maintenance()
                
                # Run learning
                await self._run_learning()
                
                # Sleep for 5 minutes between cycles
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"❌ Error in autonomous loop: {e}")
                await asyncio.sleep(300)
    
    async def _run_proactive_checks(self):
        """Run proactive task checks"""
        now = datetime.now()
        
        for task_template in self.proactive_tasks:
            # Check if it's time to run this task
            last_run = self._get_last_run(task_template['description'])
            
            if last_run is None or (now - last_run).total_seconds() >= task_template['interval_hours'] * 3600:
                # Create and queue task
                task = {
                    'id': f"auto_{int(now.timestamp())}_{random.randint(1000, 9999)}",
                    'type': task_template['type'],
                    'description': task_template['description'],
                    'context': {'source': 'autonomous', 'proactive': True},
                    'priority': task_template['priority']
                }
                
                logger.info(f"🤖 Autonomous task: {task['description']}")
                
                # Queue for execution (don't await, let it run in background)
                asyncio.create_task(self.orchestrator.process_task(task))
                
                # Record last run
                self._set_last_run(task_template['description'], now)
    
    def _get_last_run(self, description: str) -> datetime:
        """Get last run time for a proactive task"""
        # Check in orchestrator memory
        key = f"autonomous_last_run_{description}"
        stored = self.orchestrator.memory.get(key)
        
        if stored:
            return datetime.fromisoformat(stored)
        return None
    
    def _set_last_run(self, description: str, timestamp: datetime):
        """Set last run time for a proactive task"""
        key = f"autonomous_last_run_{description}"
        self.orchestrator.memory[key] = timestamp.isoformat()
    
    async def _run_maintenance(self):
        """Run maintenance tasks"""
        # Run every 10 loops
        if self.loop_count % 10 == 0:
            logger.info("🔧 Running maintenance...")
            
            # Cleanup context engine
            self.orchestrator.context_engine.cleanup()
            
            # Health check on agents
            await self.orchestrator.agent_factory.health_check()
            
            # Log stats
            status = self.orchestrator.get_status()
            logger.info(f"📊 Swarm stats: {status}")
    
    async def _run_learning(self):
        """Run learning tasks"""
        # Run every 50 loops
        if self.loop_count % 50 == 0:
            logger.info("🧠 Running learning cycle...")
            
            # Analyze completed tasks for patterns
            completed = self.orchestrator.completed_tasks
            if len(completed) > 10:
                # Look for patterns
                patterns = self._find_patterns(completed)
                
                if patterns:
                    logger.info(f"🔍 Found patterns: {patterns}")
                    
                    # Store insights
                    self.orchestrator.context_engine.remember(
                        f"pattern_{datetime.now().isoformat()}",
                        patterns,
                        'learning'
                    )
    
    def _find_patterns(self, tasks: List[Dict]) -> Dict:
        """Find patterns in completed tasks"""
        from collections import Counter
        
        # Agent type distribution
        agent_types = Counter([t.get('agent') for t in tasks if t.get('agent')])
        
        # Success rate by agent
        success_by_agent = {}
        for t in tasks:
            agent = t.get('agent')
            if agent:
                if agent not in success_by_agent:
                    success_by_agent[agent] = {'success': 0, 'fail': 0}
                
                if t.get('status') == 'completed':
                    success_by_agent[agent]['success'] += 1
                else:
                    success_by_agent[agent]['fail'] += 1
        
        # Calculate success rates
        for agent, counts in success_by_agent.items():
            total = counts['success'] + counts['fail']
            counts['rate'] = counts['success'] / total if total > 0 else 0
        
        return {
            'agent_distribution': dict(agent_types),
            'success_rates': success_by_agent,
            'total_tasks': len(tasks),
            'analyzed_at': datetime.now().isoformat()
        }
    
    def get_stats(self) -> Dict:
        """Get autonomous loop statistics"""
        return {
            'loop_count': self.loop_count,
            'running': self.running,
            'proactive_tasks_configured': len(self.proactive_tasks),
            'last_check': self.last_proactive_check.isoformat() if self.last_proactive_check else None
        }
    
    async def stop(self):
        """Stop the autonomous loop"""
        self.running = False
        logger.info("🛑 Autonomous Loop stopped")
