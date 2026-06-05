"""
SWMAS — 24/7 Daemon Runner
swarm_daemon.py

Runs the swarm continuously with:
- Signal handling (SIGTERM, SIGINT)
- Automatic restart on failure
- Health monitoring
- Graceful shutdown
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

from communication_bus import CommunicationBus, create_bus, Priority
from shared_memory import SharedMemory
from agent_factory import AgentFactory, AgentConfig, AgentType
from orchestrator import Orchestrator

# Agent templates
import researcher; researcher.register()
import analyst; analyst.register()
import executor; executor.register()
import monitor; monitor.register()
import optimizer; optimizer.register()


class SwarmDaemon:
    """
    24/7 daemon for the SWMAS swarm.

    Manages the full lifecycle:
    - Bootstrap core components
    - Start orchestrator and initial agents
    - Run health monitoring
    - Handle signals for graceful shutdown
    """

    def __init__(self, db_path: str = "swmas_memory.db") -> None:
        self.db_path = db_path
        self.bus: CommunicationBus | None = None
        self.memory: SharedMemory | None = None
        self.factory: AgentFactory | None = None
        self.orchestrator: Orchestrator | None = None
        self._shutdown_event = asyncio.Event()
        self._restart_count = 0
        self._max_restarts = 5
        self._running = False
        self._telegram_bot: Any = None

    async def bootstrap(self) -> None:
        """Initialize all swarm components with continuous workers."""
        print(f"[SWMAS Daemon] Bootstrapping swarm... (restart #{self._restart_count})")

        self.bus = await create_bus()
        self.memory = SharedMemory(db_path=self.db_path)
        self.factory = AgentFactory(bus=self.bus, memory=self.memory)
        self.orchestrator = Orchestrator(bus=self.bus, memory=self.memory, factory=self.factory)

        await self.orchestrator.start()

        # Spawn continuous workers
        await self._spawn_continuous_workers()

        print("[SWMAS Daemon] Swarm is LIVE with continuous workers.")

    async def _spawn_continuous_workers(self) -> None:
        """Spawn agents that run periodic tasks continuously."""
        print("[SWMAS Daemon] Spawning continuous workers...")

        # Monitor: always running
        monitor_id = await self.factory.spawn(AgentConfig(
            agent_type=AgentType.MONITOR,
            objective="Swarm health monitoring 24/7",
            context={"auto_check": True, "continuous": True},
            priority=Priority.CRITICAL,
        ))
        print(f"   [OK] Monitor: {monitor_id}")

        # Optimizer: always running
        optimizer_id = await self.factory.spawn(AgentConfig(
            agent_type=AgentType.OPTIMIZER,
            objective="Swarm performance optimization 24/7",
            context={"auto_optimize": True, "continuous": True},
            priority=Priority.NORMAL,
        ))
        print(f"   [OK] Optimizer: {optimizer_id}")

        # Researcher: periodic market research
        researcher_id = await self.factory.spawn(AgentConfig(
            agent_type=AgentType.RESEARCHER,
            objective="Periodic crypto market research",
            context={"continuous": True, "interval": 300, "topic": "crypto trends"},
            priority=Priority.NORMAL,
        ))
        print(f"   [OK] Researcher: {researcher_id}")

        # Analyst: periodic analysis
        analyst_id = await self.factory.spawn(AgentConfig(
            agent_type=AgentType.ANALYST,
            objective="Periodic market analysis",
            context={"continuous": True, "interval": 300, "auto_analyze": True},
            priority=Priority.NORMAL,
        ))
        print(f"   [OK] Analyst: {analyst_id}")

        # Executor: on-demand but ready
        executor_id = await self.factory.spawn(AgentConfig(
            agent_type=AgentType.EXECUTOR,
            objective="Task execution standby",
            context={"continuous": True, "standby": True},
            priority=Priority.NORMAL,
        ))
        print(f"   [OK] Executor: {executor_id}")

        # Start the continuous task scheduler
        asyncio.create_task(self._continuous_task_scheduler())
        print("   [OK] Continuous scheduler started")

    async def _continuous_task_scheduler(self) -> None:
        """Submit periodic tasks to keep agents working 24/7."""
        tasks = [
            ("Research latest crypto market trends and top movers", 300, AgentType.RESEARCHER),
            ("Analyze current market sentiment and patterns", 300, AgentType.ANALYST),
            ("Monitor swarm health and report metrics", 60, AgentType.MONITOR),
            ("Optimize swarm performance and suggest improvements", 180, AgentType.OPTIMIZER),
            ("Scan for new opportunities and alert on high-probability setups", 300, AgentType.RESEARCHER),
        ]

        while self._running:
            try:
                for description, interval, agent_type in tasks:
                    if self.orchestrator:
                        obj_id = await self.orchestrator.submit_objective(
                            description,
                            priority=Priority.NORMAL,
                            metadata={"source": "auto_scheduler", "agent_type": agent_type.value, "continuous": True},
                        )
                        print(f"   [Auto] Scheduled: {description[:50]}... (ID: {obj_id[:12]})")
                    await asyncio.sleep(interval / len(tasks))  # Spread tasks evenly

            except Exception as exc:
                print(f"[Scheduler] Error: {exc}")
                await asyncio.sleep(30)

    async def run(self) -> None:
        """Main daemon loop."""
        self._running = True

        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self._signal_handler(sig)))

        print("[SWMAS Daemon] Running 24/7. Press Ctrl+C to stop.")

        while self._running and not self._shutdown_event.is_set():
            try:
                # Health heartbeat
                if self.orchestrator:
                    health = await self.orchestrator.health_check()
                    active = health["orchestrator"]["active_objectives"]
                    agents = health["factory"]["active"]
                    print(f"   [{time.strftime('%H:%M:%S')}] {active} active objectives, {agents} agents")

                await asyncio.wait_for(self._shutdown_event.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                print(f"[SWMAS Daemon] Loop error: {exc}")
                if self._restart_count < self._max_restarts:
                    self._restart_count += 1
                    print(f"   Restarting swarm... (attempt {self._restart_count}/{self._max_restarts})")
                    await self.shutdown()
                    await asyncio.sleep(2)
                    await self.bootstrap()
                else:
                    print("   Max restarts reached. Shutting down.")
                    break

    async def _signal_handler(self, sig: int) -> None:
        """Handle shutdown signals."""
        sig_name = signal.Signals(sig).name
        print(f"[SWMAS Daemon] Received {sig_name}. Shutting down gracefully...")
        self._shutdown_event.set()
        self._running = False

    async def shutdown(self) -> None:
        """Graceful shutdown of all components."""
        print("[SWMAS Daemon] Stopping components...")

        if self._telegram_bot:
            try:
                await self._telegram_bot.stop()
            except Exception as exc:
                print(f"   Telegram bot stop error: {exc}")

        if self.orchestrator:
            try:
                await self.orchestrator.stop()
            except Exception as exc:
                print(f"   Orchestrator stop error: {exc}")

        if self.bus:
            try:
                await self.bus.stop()
            except Exception as exc:
                print(f"   Bus stop error: {exc}")

        if self.memory:
            try:
                self.memory.close()
            except Exception as exc:
                print(f"   Memory close error: {exc}")

        print("[SWMAS Daemon] Shutdown complete.")

    async def attach_telegram(self, token: str, allowed_usernames: list[str] | None = None) -> None:
        """Attach a Telegram bot to the daemon."""
        try:
            from telegram_bot import SwarmTelegramBot
        except ImportError:
            print("python-telegram-bot not installed. Run: pip install python-telegram-bot")
            return

        self._telegram_bot = SwarmTelegramBot(
            token=token,
            orchestrator=self.orchestrator,
            factory=self.factory,
            memory=self.memory,
            bus=self.bus,
            allowed_usernames=allowed_usernames,
        )

        # Start bot in background
        asyncio.create_task(self._telegram_bot.start())
        print("[Telegram] Bot attached and running.")

    async def main(self, telegram_token: str | None = None, allowed_users: list[str] | None = None) -> None:
        """Full daemon entry point."""
        try:
            await self.bootstrap()

            if telegram_token:
                await self.attach_telegram(telegram_token, allowed_users)

            await self.run()
        finally:
            await self.shutdown()


def run_daemon(telegram_token: str | None = None, allowed_users: list[str] | None = None) -> None:
    """Synchronous entry point for the daemon."""
    daemon = SwarmDaemon()
    try:
        asyncio.run(daemon.main(telegram_token=telegram_token, allowed_users=allowed_users))
    except KeyboardInterrupt:
        print("Interrupted by user.")
        sys.exit(0)
