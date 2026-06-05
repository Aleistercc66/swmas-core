"""
Autonomous Loop - Self-Directed Operation
=========================================
Enables the orchestrator to run autonomously without user input.
Monitors markets, spawns agents, learns, and adapts automatically.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class AutonomousLoop:
    """
    Manages autonomous operation of the orchestrator.
    
    Features:
    - Continuous market monitoring
    - Automatic agent spawning
    - Self-triggered learning
    - Adaptive behavior based on market conditions
    """

    def __init__(self, brain=None, swarm=None, skills=None, context=None):
        self.brain = brain
        self.swarm = swarm
        self.skills = skills
        self.context = context
        
        self.autopilot_users: set = set()
        self.is_running = False
        self.tasks: List[asyncio.Task] = []
        
        # Intervals (seconds)
        self.market_scan_interval = 300  # 5 minutes
        self.agent_health_interval = 60  # 1 minute
        self.learning_interval = 3600  # 1 hour
        self.report_interval = 86400  # 24 hours

    async def initialize(self):
        """Initialize autonomous loop."""
        logger.info("🤖 Initializing Autonomous Loop...")
        self.is_running = True
        logger.info("🤖 Autonomous loop ready")

    async def start_for_user(self, user_id: int):
        """Start autopilot for a specific user."""
        self.autopilot_users.add(user_id)
        logger.info(f"🤖 Autopilot started for user {user_id}")
        
        # Start background tasks if not already running
        if not self.tasks:
            self._start_background_tasks()

    async def stop_for_user(self, user_id: int):
        """Stop autopilot for a specific user."""
        if user_id in self.autopilot_users:
            self.autopilot_users.remove(user_id)
        logger.info(f"🛑 Autopilot stopped for user {user_id}")

    async def pause_all(self):
        """Pause all autonomous operations."""
        self.is_running = False
        for task in self.tasks:
            task.cancel()
        self.tasks = []
        logger.info("⏸️ All autonomous operations paused")

    async def stop(self):
        """Stop autonomous loop completely."""
        self.is_running = False
        self.autopilot_users.clear()
        for task in self.tasks:
            task.cancel()
        self.tasks = []
        logger.info("🛑 Autonomous loop stopped")

    def _start_background_tasks(self):
        """Start background monitoring tasks."""
        self.tasks = [
            asyncio.create_task(self._market_scan_loop()),
            asyncio.create_task(self._agent_health_loop()),
            asyncio.create_task(self._learning_loop()),
            asyncio.create_task(self._report_loop()),
        ]

    async def _market_scan_loop(self):
        """Continuous market scanning."""
        while self.is_running and self.autopilot_users:
            try:
                await asyncio.sleep(self.market_scan_interval)
                
                if not self.autopilot_users:
                    continue
                
                logger.info("🔍 Autonomous market scan triggered")
                
                # Spawn scanner agent if not exists
                agents = await self.swarm.list_agents()
                has_scanner = any(a["type"] == "scanner" for a in agents)
                
                if not has_scanner:
                    await self.swarm.spawn_agent("scanner")
                    logger.info("🐝 Auto-spawned scanner agent")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Market scan loop error: {e}")

    async def _agent_health_loop(self):
        """Monitor agent health."""
        while self.is_running and self.autopilot_users:
            try:
                await asyncio.sleep(self.agent_health_interval)
                
                if not self.autopilot_users:
                    continue
                
                agents = await self.swarm.list_agents()
                for agent in agents:
                    # Check if agent is healthy
                    if agent["status"] != "running":
                        logger.warning(f"⚠️ Agent {agent['id']} not running")
                        # Could restart here
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Health loop error: {e}")

    async def _learning_loop(self):
        """Continuous learning."""
        while self.is_running and self.autopilot_users:
            try:
                await asyncio.sleep(self.learning_interval)
                
                if not self.autopilot_users:
                    continue
                
                logger.info("🧠 Autonomous learning triggered")
                await self.skills.learn_skill("auto")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Learning loop error: {e}")

    async def _report_loop(self):
        """Periodic reporting."""
        while self.is_running and self.autopilot_users:
            try:
                await asyncio.sleep(self.report_interval)
                
                if not self.autopilot_users:
                    continue
                
                logger.info("📈 Daily report triggered")
                # Generate and send report
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Report loop error: {e}")
