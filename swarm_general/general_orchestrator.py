"""
🌐 GENERAL ORCHESTRATOR
Main entry point for the General Purpose Swarm System (GPSS)
Routes tasks, manages agents, coordinates execution
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'core'))
sys.path.insert(0, str(Path(__file__).parent / 'agents'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/root/.openclaw/workspace/swarm_general/logs/orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GeneralOrchestrator')

class GeneralOrchestrator:
    """Main orchestrator for the general purpose swarm"""
    
    def __init__(self):
        self.version = "2.0"
        self.status = "initializing"
        self.start_time = datetime.now()
        self.agents = {}
        self.skills = {}
        self.active_tasks = {}
        self.completed_tasks = []
        self.memory = {}
        self.config = self._load_config()
        
        logger.info("🔥 General Orchestrator initializing...")
        self._init_core()
        
    def _load_config(self) -> Dict:
        """Load swarm configuration"""
        config_path = Path(__file__).parent / 'config' / 'swarm_config.yaml'
        if config_path.exists():
            import yaml
            with open(config_path) as f:
                return yaml.safe_load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            'swarm_name': 'SWMAS-General',
            'max_agents': 20,
            'max_concurrent_tasks': 50,
            'task_timeout': 300,
            'autonomous_mode': True,
            'learning_enabled': True,
            'directions': [
                'research', 'content', 'automation', 'monitoring',
                'communication', 'analysis', 'problem_solving', 'learning'
            ],
            'agent_types': [
                'ResearchAgent', 'ContentAgent', 'AutomationAgent',
                'MonitorAgent', 'CommsAgent', 'AnalysisAgent',
                'SolverAgent', 'LearnAgent'
            ]
        }
    
    def _init_core(self):
        """Initialize core components"""
        logger.info("🧠 Initializing core components...")
        
        # Initialize task router
        from task_router import TaskRouter
        self.task_router = TaskRouter(self)
        
        # Initialize agent factory
        from agent_factory import AgentFactory
        self.agent_factory = AgentFactory(self)
        
        # Initialize skill registry
        from skill_registry import SkillRegistry
        self.skill_registry = SkillRegistry(self)
        
        # Initialize context engine
        from context_engine import ContextEngine
        self.context_engine = ContextEngine(self)
        
        # Initialize autonomous loop
        from autonomous_loop import AutonomousLoop
        self.autonomous_loop = AutonomousLoop(self)
        
        self.status = "ready"
        logger.info("✅ General Orchestrator ready!")
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming task
        
        Task format:
        {
            'id': 'unique-id',
            'type': 'research|content|automation|monitor|comms|analysis|solver|learn',
            'direction': 'general domain',
            'description': 'what to do',
            'context': {},
            'priority': 'critical|high|normal|low',
            'deadline': 'ISO timestamp',
            'callback': 'where to send results'
        }
        """
        task_id = task.get('id', f"task_{int(time.time())}")
        logger.info(f"📥 Received task: {task_id} | Type: {task.get('type', 'unknown')}")
        
        # Store in active tasks
        self.active_tasks[task_id] = {
            **task,
            'status': 'routing',
            'started_at': datetime.now().isoformat(),
            'agent': None
        }
        
        try:
            # Step 1: Route task to appropriate agent
            route = self.task_router.route(task)
            agent_type = route['agent_type']
            
            logger.info(f"🎯 Task {task_id} routed to {agent_type}")
            self.active_tasks[task_id]['status'] = 'assigned'
            self.active_tasks[task_id]['agent'] = agent_type
            
            # Step 2: Get or create agent
            agent = await self.agent_factory.get_or_create_agent(agent_type)
            
            # Step 3: Execute task
            self.active_tasks[task_id]['status'] = 'executing'
            result = await agent.execute(task)
            
            # Step 4: Process result
            self.active_tasks[task_id]['status'] = 'completed'
            self.active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            self.active_tasks[task_id]['result'] = result
            
            # Move to completed
            self.completed_tasks.append(self.active_tasks[task_id])
            del self.active_tasks[task_id]
            
            logger.info(f"✅ Task {task_id} completed successfully")
            
            return {
                'success': True,
                'task_id': task_id,
                'agent': agent_type,
                'result': result,
                'execution_time': self._calculate_execution_time(task_id)
            }
            
        except Exception as e:
            logger.error(f"❌ Task {task_id} failed: {e}")
            self.active_tasks[task_id]['status'] = 'failed'
            self.active_tasks[task_id]['error'] = str(e)
            
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e),
                'status': 'failed'
            }
    
    def _calculate_execution_time(self, task_id: str) -> float:
        """Calculate task execution time"""
        # Simplified calculation
        return 0.0
    
    async def spawn_agent(self, agent_type: str, config: Dict = None) -> str:
        """Spawn a new agent of given type"""
        agent_id = await self.agent_factory.spawn(agent_type, config)
        logger.info(f"🆕 Spawned {agent_type} agent: {agent_id}")
        return agent_id
    
    async def kill_agent(self, agent_id: str) -> bool:
        """Kill an agent"""
        return await self.agent_factory.kill(agent_id)
    
    def get_status(self) -> Dict:
        """Get swarm status"""
        return {
            'version': self.version,
            'status': self.status,
            'uptime': str(datetime.now() - self.start_time),
            'active_agents': len(self.agents),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'directions': self.config.get('directions', []),
            'agent_types': list(self.agents.keys()),
            'memory_size': len(self.memory)
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        for task in self.completed_tasks:
            if task.get('id') == task_id:
                return task
        return None
    
    async def run(self):
        """Main run loop"""
        logger.info("🚀 General Orchestrator running!")
        
        # Start autonomous loop
        asyncio.create_task(self.autonomous_loop.run())
        
        # Keep running
        while True:
            await asyncio.sleep(60)
            status = self.get_status()
            logger.info(f"💓 Heartbeat | Agents: {status['active_agents']} | Tasks: {status['active_tasks']}")
    
    async def handle_telegram_command(self, command: str, args: List[str], user_id: str) -> str:
        """Handle Telegram commands"""
        cmd = command.lower()
        
        if cmd == '/status':
            status = self.get_status()
            return f"""🌐 SWARM STATUS

Version: {status['version']}
Uptime: {status['uptime']}
Active Agents: {status['active_agents']}
Active Tasks: {status['active_tasks']}
Completed: {status['completed_tasks']}
Directions: {', '.join(status['directions'])}
"""
        
        elif cmd == '/agents':
            agents = self.agent_factory.list_agents()
            return f"""🤖 ACTIVE AGENTS

{chr(10).join([f"• {a['type']} ({a['status']})" for a in agents])}
"""
        
        elif cmd == '/tasks':
            tasks = list(self.active_tasks.values())
            return f"""📋 ACTIVE TASKS ({len(tasks)})

{chr(10).join([f"• {t['id']}: {t.get('type', 'unknown')} [{t['status']}]" for t in tasks[:10]])}
"""
        
        elif cmd == '/skills':
            skills = self.skill_registry.list_skills()
            return f"""🛠️ AVAILABLE SKILLS ({len(skills)})

{chr(10).join([f"• {s['name']} ({s['category']})" for s in skills[:20]])}
"""
        
        elif cmd == '/task':
            if not args:
                return "Usage: /task <description>"
            
            description = ' '.join(args)
            task = {
                'id': f"tg_{int(time.time())}",
                'type': 'general',
                'description': description,
                'context': {'source': 'telegram', 'user_id': user_id},
                'priority': 'normal'
            }
            
            # Process async
            asyncio.create_task(self.process_task(task))
            return f"✅ Task queued: {description[:50]}..."
        
        elif cmd == '/directions':
            return f"""🧭 SWARM DIRECTIONS

1. 🕵️ Research & Intelligence
2. ✍️ Content & Creation
3. 🤖 Automation & Execution
4. 📊 Monitoring & Alerting
5. 🗣️ Communication & Coordination
6. 🧮 Analysis & Decision Support
7. 🔧 Problem Solving & Debugging
8. 📚 Learning & Adaptation

Use /task <description> to send work to the swarm!
"""
        
        elif cmd == '/help':
            return f"""🌐 GENERAL SWARM COMMANDS

/status — Swarm status
/agents — Active agents
/tasks — Running tasks
/skills — Available skills
/task <desc> — Submit a task
/directions — Show all directions
/help — This message

The swarm handles everything automatically!
"""
        
        else:
            return f"Unknown command: {command}. Use /help for available commands."


# Singleton instance
_orchestrator = None

def get_orchestrator() -> GeneralOrchestrator:
    """Get or create orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = GeneralOrchestrator()
    return _orchestrator


if __name__ == '__main__':
    orchestrator = get_orchestrator()
    
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        logger.info("👋 Shutting down General Orchestrator")
