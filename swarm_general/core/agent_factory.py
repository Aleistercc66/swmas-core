"""
🏭 AGENT FACTORY
Creates, manages, and destroys swarm agents
Handles agent lifecycle, health, and scaling
"""

import asyncio
import importlib
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger('AgentFactory')

class AgentFactory:
    """Factory for creating and managing swarm agents"""
    
    # Agent module mapping
    AGENT_MODULES = {
        'ResearchAgent': 'agents.research_agent',
        'ContentAgent': 'agents.content_agent',
        'AutomationAgent': 'agents.automation_agent',
        'MonitorAgent': 'agents.monitor_agent',
        'CommsAgent': 'agents.comms_agent',
        'AnalysisAgent': 'agents.analysis_agent',
        'SolverAgent': 'agents.solver_agent',
        'LearnAgent': 'agents.learn_agent',
        # Legacy trading agents (compatibility)
        'TradingAgent': None,  # Use existing trading system
        'SecurityAgent': None,  # Future implementation
        'CreativeAgent': None,  # Future implementation
        'DevAgent': None,  # Future implementation
        'BizAgent': None,  # Future implementation
    }
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.active_agents: Dict[str, Any] = {}
        self.agent_pool: Dict[str, List[str]] = {}  # type -> [agent_ids]
        self.agent_stats: Dict[str, Dict] = {}
        self.max_agents_per_type = 5
        self.health_check_interval = 60
        
        logger.info("🏭 Agent Factory initialized")
    
    async def get_or_create_agent(self, agent_type: str) -> Any:
        """Get existing healthy agent or create new one"""
        
        # Check for healthy existing agents
        if agent_type in self.agent_pool:
            for agent_id in self.agent_pool[agent_type]:
                if self._is_healthy(agent_id):
                    logger.info(f"♻️ Reusing {agent_type}: {agent_id}")
                    return self.active_agents[agent_id]
        
        # Create new agent
        return await self.spawn(agent_type)
    
    async def spawn(self, agent_type: str, config: Dict = None) -> str:
        """Spawn a new agent"""
        agent_id = f"{agent_type.lower()}_{int(time.time())}_{len(self.active_agents)}"
        
        try:
            # Check agent limit
            current_count = len(self.agent_pool.get(agent_type, []))
            if current_count >= self.max_agents_per_type:
                # Reuse oldest agent - return the agent OBJECT not the ID
                logger.warning(f"⚠️ Agent limit reached for {agent_type}, reusing oldest")
                oldest_id = self.agent_pool[agent_type][0]
                return self.active_agents[oldest_id]
            
            # Import agent class
            module_name = self.AGENT_MODULES.get(agent_type)
            if module_name is None:
                raise ValueError(f"Agent type {agent_type} not yet implemented")
            
            module = importlib.import_module(module_name)
            agent_class = getattr(module, agent_type)
            
            # Instantiate agent
            agent = agent_class(
                agent_id=agent_id,
                orchestrator=self.orchestrator,
                config=config or {}
            )
            
            # Store agent
            self.active_agents[agent_id] = agent
            
            if agent_type not in self.agent_pool:
                self.agent_pool[agent_type] = []
            self.agent_pool[agent_type].append(agent_id)
            
            # Initialize stats
            self.agent_stats[agent_id] = {
                'created_at': datetime.now().isoformat(),
                'tasks_completed': 0,
                'tasks_failed': 0,
                'total_execution_time': 0,
                'status': 'idle',
                'last_health_check': datetime.now().isoformat()
            }
            
            logger.info(f"🆕 Spawned {agent_type}: {agent_id}")
            return agent_id
            
        except Exception as e:
            logger.error(f"❌ Failed to spawn {agent_type}: {e}")
            raise
    
    async def kill(self, agent_id: str) -> bool:
        """Kill an agent"""
        if agent_id not in self.active_agents:
            logger.warning(f"⚠️ Agent {agent_id} not found")
            return False
        
        try:
            agent = self.active_agents[agent_id]
            
            # Cleanup
            if hasattr(agent, 'cleanup'):
                await agent.cleanup()
            
            # Remove from pools
            del self.active_agents[agent_id]
            
            for agent_type, ids in self.agent_pool.items():
                if agent_id in ids:
                    ids.remove(agent_id)
                    break
            
            # Archive stats
            if agent_id in self.agent_stats:
                self.agent_stats[agent_id]['status'] = 'terminated'
                self.agent_stats[agent_id]['terminated_at'] = datetime.now().isoformat()
            
            logger.info(f"💀 Killed agent: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error killing agent {agent_id}: {e}")
            return False
    
    def _is_healthy(self, agent_id: str) -> bool:
        """Check if agent is healthy"""
        if agent_id not in self.active_agents:
            return False
        
        stats = self.agent_stats.get(agent_id, {})
        
        # Check if agent is stuck
        if stats.get('status') == 'executing':
            started = stats.get('task_started_at')
            if started:
                from datetime import datetime
                start_time = datetime.fromisoformat(started)
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > 300:  # 5 minutes timeout
                    logger.warning(f"⚠️ Agent {agent_id} appears stuck")
                    return False
        
        # Check failure rate
        completed = stats.get('tasks_completed', 0)
        failed = stats.get('tasks_failed', 0)
        if completed + failed > 10 and failed / (completed + failed) > 0.5:
            logger.warning(f"⚠️ Agent {agent_id} has high failure rate")
            return False
        
        return True
    
    async def health_check(self):
        """Run health checks on all agents"""
        logger.info("🏥 Running health checks...")
        
        for agent_id in list(self.active_agents.keys()):
            if not self._is_healthy(agent_id):
                logger.warning(f"🏥 Agent {agent_id} unhealthy, respawning...")
                
                # Determine type
                agent_type = None
                for atype, ids in self.agent_pool.items():
                    if agent_id in ids:
                        agent_type = atype
                        break
                
                if agent_type:
                    # Kill and respawn
                    await self.kill(agent_id)
                    await self.spawn(agent_type)
    
    def list_agents(self) -> List[Dict]:
        """List all active agents"""
        result = []
        for agent_id, agent in self.active_agents.items():
            stats = self.agent_stats.get(agent_id, {})
            result.append({
                'id': agent_id,
                'type': type(agent).__name__,
                'status': stats.get('status', 'unknown'),
                'tasks_completed': stats.get('tasks_completed', 0),
                'created_at': stats.get('created_at')
            })
        return result
    
    def get_agent_stats(self, agent_id: str) -> Optional[Dict]:
        """Get stats for specific agent"""
        return self.agent_stats.get(agent_id)
    
    def get_pool_stats(self) -> Dict:
        """Get pool statistics"""
        return {
            'total_agents': len(self.active_agents),
            'by_type': {k: len(v) for k, v in self.agent_pool.items()},
            'max_per_type': self.max_agents_per_type,
            'utilization': len(self.active_agents) / (len(self.AGENT_MODULES) * self.max_agents_per_type)
        }
    
    async def scale_up(self, agent_type: str, count: int = 1):
        """Scale up agents of a type"""
        logger.info(f"📈 Scaling up {agent_type} by {count}")
        for _ in range(count):
            await self.spawn(agent_type)
    
    async def scale_down(self, agent_type: str, count: int = 1):
        """Scale down agents of a type"""
        logger.info(f"📉 Scaling down {agent_type} by {count}")
        
        if agent_type not in self.agent_pool:
            return
        
        # Remove oldest agents first
        to_remove = self.agent_pool[agent_type][:count]
        for agent_id in to_remove:
            await self.kill(agent_id)
    
    async def run_health_checks(self):
        """Continuous health check loop"""
        while True:
            await asyncio.sleep(self.health_check_interval)
            await self.health_check()
