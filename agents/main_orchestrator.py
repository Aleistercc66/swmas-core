#!/usr/bin/env python3
"""
🚀 MAIN ORCHESTRATOR — Coordinates all V2 agents
Single entry point. Spawns agents as tasks, handles graceful shutdown.
"""
import asyncio
import signal
import sys
from typing import List

# Add parent to path
sys.path.insert(0, "/root/.openclaw/workspace/agents")

from core import get_logger, init_db, start_metrics_server

logger = get_logger("orchestrator")

# Import agents
from agents_v2.scanner import AsyncScanner
from agents_v2.validator import AsyncValidator
from agents_v2.risk_engine import AsyncRiskEngine
from agents_v2.executor import AsyncExecutor
from agents_v2.position_monitor import AsyncPositionMonitor
from agents_v2.telegram_bot import AsyncTelegramBot
from agents_v2.meta_supervisor import AsyncMetaSupervisor

class Orchestrator:
    """Central orchestrator for the trading swarm."""
    
    def __init__(self):
        self.agents = {}
        self.tasks: List[asyncio.Task] = []
        self.running = False
        
        # Wire up references
        self.executor = AsyncExecutor()
        self.telegram = AsyncTelegramBot()
        self.telegram.executor_ref = self.executor
        
        self.agents = {
            "scanner": AsyncScanner(),
            "validator": AsyncValidator(),
            "risk_engine": AsyncRiskEngine(),
            "executor": self.executor,
            "position_monitor": AsyncPositionMonitor(),
            "telegram_bot": self.telegram,
            "meta_supervisor": AsyncMetaSupervisor(),
        }
    
    async def start(self):
        """Initialize and start all agents."""
        logger.info("╔═══════════════════════════════════════════════════════╗")
        logger.info("║  🚀 CRYPTO TRADING SWARM V2 — ORCHESTRATOR           ║")
        logger.info("║  Event-driven | Atomic | Observable | Scalable        ║")
        logger.info("╚═══════════════════════════════════════════════════════╝")
        
        # Init database
        await init_db()
        logger.info("✅ Database initialized")
        
        # Start metrics server
        start_metrics_server()
        logger.info("✅ Prometheus metrics started")
        
        # Create tasks
        self.running = True
        
        for name, agent in self.agents.items():
            if name in ["scanner", "position_monitor"]:
                # These use async context managers
                task = asyncio.create_task(
                    self._run_with_context(name, agent),
                    name=f"agent_{name}"
                )
            else:
                task = asyncio.create_task(
                    agent.run(),
                    name=f"agent_{name}"
                )
            self.tasks.append(task)
            logger.info(f"  🟢 Started: {name}")
        
        logger.info(f"\n✅ All {len(self.tasks)} agents running")
        logger.info("📊 Metrics: http://localhost:9090/metrics")
        logger.info("Press Ctrl+C to stop\n")
        
        # Wait for all tasks
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.info("Orchestrator shutting down...")
    
    async def _run_with_context(self, name: str, agent):
        """Run agent with async context manager."""
        async with agent:
            await agent.run()
    
    async def stop(self):
        """Graceful shutdown."""
        logger.info("🛑 Stopping all agents...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for cleanup
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop all agents
        for agent in self.agents.values():
            if hasattr(agent, 'stop'):
                agent.stop()
        
        logger.info("✅ All agents stopped")
    
    def signal_handler(self, sig):
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig.name}")
        asyncio.create_task(self.stop())

async def main():
    orchestrator = Orchestrator()
    
    # Register signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: orchestrator.signal_handler(s))
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        await orchestrator.stop()
    finally:
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGTERM)

if __name__ == "__main__":
    asyncio.run(main())
