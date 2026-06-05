"""
Swarm Manager - Agent Lifecycle and Orchestration
==================================================
Manages the spawning, monitoring, and termination of swarm agents.
Connects to existing agent infrastructure in /workspace/agents/
"""

import os
import json
import logging
import asyncio
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

WORKSPACE = Path("/root/.openclaw/workspace")
AGENTS_DIR = WORKSPACE / "agents"
SWARM_STATE_FILE = WORKSPACE / "orchestrator" / "logs" / "swarm_state.json"

# Agent type configurations
AGENT_TYPES = {
    "scanner": {
        "script": "dexscreener_scanner.py",
        "description": "Market scanner using DexScreener",
        "interval": 300,  # 5 minutes
    },
    "trader": {
        "script": "signal_generator.py",
        "description": "Trading signal generator",
        "interval": 60,
    },
    "analyst": {
        "script": "blockchain_analyzer.py",
        "description": "Blockchain data analyst",
        "interval": 600,
    },
    "learner": {
        "script": None,
        "description": "Skill learning agent",
        "interval": 3600,
    },
    "monitor": {
        "script": "realtime_dexscreener.py",
        "description": "Real-time market monitor",
        "interval": 30,
    },
}


class SwarmManager:
    """
    Manages the swarm of agents.
    
    Capabilities:
    - Spawn new agents on demand
    - Monitor agent health
    - Route tasks to appropriate agents
    - Handle agent lifecycle
    """

    def __init__(self, brain=None):
        self.brain = brain
        self.active_agents: Dict[str, Dict] = {}
        self.agent_processes: Dict[str, subprocess.Popen] = {}
        self.agent_counter = 0
        self.is_running = False

    async def initialize(self):
        """Initialize swarm manager."""
        logger.info("🐝 Initializing Swarm Manager...")
        
        # Load existing state
        if SWARM_STATE_FILE.exists():
            with open(SWARM_STATE_FILE) as f:
                state = json.load(f)
                self.active_agents = state.get("agents", {})
        
        self.is_running = True
        logger.info(f"🐝 Swarm manager ready. Active agents: {len(self.active_agents)}")

    async def spawn_agent(self, agent_type: str, config: Optional[str] = None) -> Dict:
        """
        Spawn a new agent of the given type.
        
        Args:
            agent_type: Type of agent (scanner, trader, analyst, learner, monitor)
            config: Optional configuration string
            
        Returns:
            Agent information dict
        """
        if agent_type not in AGENT_TYPES:
            available = ", ".join(AGENT_TYPES.keys())
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {available}")

        self.agent_counter += 1
        agent_id = f"{agent_type}_{self.agent_counter}_{uuid.uuid4().hex[:6]}"
        
        agent_info = {
            "id": agent_id,
            "name": f"{agent_type.capitalize()}Agent-{self.agent_counter}",
            "type": agent_type,
            "status": "initializing",
            "created_at": datetime.now().isoformat(),
            "uptime": "0s",
            "tasks_done": 0,
            "config": config or "default",
            "script": AGENT_TYPES[agent_type]["script"],
            "interval": AGENT_TYPES[agent_type]["interval"],
        }

        # Start the agent process if it has a script
        if agent_info["script"] and (AGENTS_DIR / agent_info["script"]).exists():
            try:
                process = subprocess.Popen(
                    ["python3", str(AGENTS_DIR / agent_info["script"])],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=WORKSPACE,
                )
                self.agent_processes[agent_id] = process
                agent_info["status"] = "running"
                agent_info["pid"] = process.pid
                logger.info(f"🐝 Agent {agent_id} spawned (PID: {process.pid})")
            except Exception as e:
                agent_info["status"] = "error"
                agent_info["error"] = str(e)
                logger.error(f"❌ Failed to spawn agent {agent_id}: {e}")
        else:
            # Agent without script (e.g., learner)
            agent_info["status"] = "active"
            logger.info(f"🐝 Agent {agent_id} created (no script, virtual agent)")

        self.active_agents[agent_id] = agent_info
        await self._save_state()
        
        return agent_info

    async def kill_agent(self, agent_id: str) -> bool:
        """
        Terminate an agent.
        
        Args:
            agent_id: ID of agent to kill
            
        Returns:
            True if successful
        """
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent {agent_id} not found")

        agent = self.active_agents[agent_id]
        
        # Kill process if running
        if agent_id in self.agent_processes:
            process = self.agent_processes[agent_id]
            try:
                process.terminate()
                process.wait(timeout=5)
                del self.agent_processes[agent_id]
            except:
                process.kill()
        
        agent["status"] = "terminated"
        agent["terminated_at"] = datetime.now().isoformat()
        
        # Move to history
        del self.active_agents[agent_id]
        
        await self._save_state()
        logger.info(f"💀 Agent {agent_id} terminated")
        
        return True

    async def list_agents(self) -> List[Dict]:
        """List all active agents."""
        return [
            {
                "id": aid,
                "name": info["name"],
                "type": info["type"],
                "status": info["status"],
                "uptime": self._calculate_uptime(info),
                "tasks_done": info["tasks_done"],
            }
            for aid, info in self.active_agents.items()
        ]

    async def get_status(self) -> str:
        """Get swarm status as formatted text."""
        agents = await self.list_agents()
        
        if not agents:
            return "🌑 **SWARM EMPTY**\n\nNo active agents. Spawn one with `/spawn <type>`"

        text = "🐝 **SWARM STATUS** 🐝\n\n"
        
        # Group by type
        by_type = {}
        for a in agents:
            t = a["type"]
            by_type.setdefault(t, []).append(a)
        
        for agent_type, agent_list in by_type.items():
            text += f"**{agent_type.upper()}** ({len(agent_list)})\n"
            for a in agent_list:
                status_emoji = "🟢" if a["status"] == "running" else "🟡"
                text += f"  {status_emoji} {a['name']} — {a['status']}\n"
            text += "\n"
        
        text += f"**Total:** {len(agents)} agents active"
        return text

    async def get_agent_status(self, agent_id: str) -> Dict:
        """Get detailed status of a specific agent."""
        if agent_id not in self.active_agents:
            return {"error": "Agent not found"}
        
        agent = self.active_agents[agent_id]
        
        # Check if process is alive
        if agent_id in self.agent_processes:
            process = self.agent_processes[agent_id]
            agent["process_alive"] = process.poll() is None
        
        return agent

    async def broadcast_task(self, task: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Broadcast a task to all appropriate agents.
        
        Returns:
            List of results from each agent
        """
        results = []
        
        for agent_id, agent in self.active_agents.items():
            if agent["status"] == "running":
                try:
                    # In a full implementation, send task via IPC
                    result = {"agent": agent_id, "status": "acknowledged"}
                    agent["tasks_done"] = agent.get("tasks_done", 0) + 1
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Failed to send task to {agent_id}: {e}")
        
        await self._save_state()
        return results

    async def shutdown(self):
        """Shutdown all agents."""
        logger.info("🛑 Shutting down swarm...")
        
        for agent_id in list(self.active_agents.keys()):
            try:
                await self.kill_agent(agent_id)
            except Exception as e:
                logger.error(f"❌ Error killing {agent_id}: {e}")
        
        self.is_running = False
        logger.info("🐝 Swarm shutdown complete")

    def _calculate_uptime(self, agent: Dict) -> str:
        """Calculate human-readable uptime."""
        try:
            created = datetime.fromisoformat(agent["created_at"])
            delta = datetime.now() - created
            
            if delta.days > 0:
                return f"{delta.days}d {delta.seconds//3600}h"
            elif delta.seconds >= 3600:
                return f"{delta.seconds//3600}h {(delta.seconds%3600)//60}m"
            else:
                return f"{delta.seconds//60}m"
        except:
            return "unknown"

    async def _save_state(self):
        """Save swarm state to file."""
        SWARM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SWARM_STATE_FILE, 'w') as f:
            json.dump({
                "agents": self.active_agents,
                "agent_counter": self.agent_counter,
                "last_update": datetime.now().isoformat(),
            }, f, indent=2)
