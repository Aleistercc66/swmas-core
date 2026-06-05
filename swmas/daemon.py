"""
SWMAS — 24/7 Daemon Runner
daemon.py

Starts the full swarm (bus, memory, factory, orchestrator, agents),
optionally the Telegram bot, and runs in an infinite loop
with graceful shutdown on SIGTERM/SIGINT.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Path setup
_PHASE1 = Path(__file__).resolve().parent / "phase1"
_PHASE2 = Path(__file__).resolve().parent / "phase2"
for p in (_PHASE1, _PHASE2):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from communication_bus import create_bus
from shared_memory import SharedMemory
from agent_factory import AgentFactory, AgentType, register_agent_template
from orchestrator import Orchestrator

# Register Phase 2 agent templates
from researcher import register as register_researcher
from analyst import register as register_analyst
from executor import register as register_executor
from monitor import register as register_monitor
from optimizer import register as register_optimizer

register_researcher()
register_analyst()
register_executor()
register_monitor()
register_optimizer()

logger = logging.getLogger("swmas.daemon")

# Global shutdown event (used by signal handlers + Telegram /stop)
shutdown_event = asyncio.Event()


class SwarmDaemon:
    """
    24/7 daemon that orchestrates the entire SWMAS lifecycle.

    Responsibilities:
    - Initialize core infrastructure (bus, memory, factory, orchestrator)
    - Register all agent templates
    - Optionally start Telegram bot
    - Run infinite loop with graceful shutdown
    - Signal handling (SIGTERM / SIGINT)
    """

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        db_path: str = "swmas_memory.db",
    ) -> None:
        self.telegram_token = telegram_token
        self.db_path = db_path
        self.bus = None
        self.memory = None
        self.factory = None
        self.orchestrator = None
        self.telegram_bot = None
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Initialize and start all swarm components."""
        logger.info("🔥 SWMAS Daemon starting...")

        # 1. Core infrastructure
        self.bus = await create_bus()
        logger.info("✅ CommunicationBus started")

        self.memory = SharedMemory(db_path=self.db_path)
        logger.info("✅ SharedMemory initialized (%s)", self.db_path)

        self.factory = AgentFactory(bus=self.bus, memory=self.memory)
        logger.info("✅ AgentFactory ready")

        self.orchestrator = Orchestrator(
            bus=self.bus,
            memory=self.memory,
            factory=self.factory,
        )
        await self.orchestrator.start()
        logger.info("✅ Orchestrator started")

        # 2. Telegram bot (optional)
        if self.telegram_token:
            from telegram_bot import create_bot
            self.telegram_bot = create_bot(self.telegram_token, self.orchestrator)
            await self.telegram_bot.start()
            logger.info("✅ Telegram bot started")

        # 3. Spawn a default Monitor agent for self-health
        monitor_id = await self.factory.spawn(
            AgentConfig(
                agent_type=AgentType.MONITOR,
                objective="Swarm health monitoring",
                priority=2,  # NORMAL
            )
        )
        logger.info("✅ Default Monitor spawned: %s", monitor_id)

        self._running = True
        logger.info("🏁 SWMAS Daemon fully operational")

    async def run(self) -> None:
        """Infinite loop — waits for shutdown_event."""
        logger.info("⏳ Daemon running. Waiting for shutdown signal...")
        try:
            await shutdown_event.wait()
        except asyncio.CancelledError:
            logger.info("Daemon loop cancelled")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Graceful shutdown — stop all components in reverse order."""
        if not self._running:
            return
        self._running = False
        logger.info("🛑 Shutdown initiated...")

        # Telegram bot
        if self.telegram_bot:
            await self.telegram_bot.stop()
            logger.info("Telegram bot stopped")

        # Orchestrator
        if self.orchestrator:
            await self.orchestrator.stop()
            logger.info("Orchestrator stopped")

        # Terminate all live agents
        if self.factory:
            for rec in self.factory.list_agents():
                if rec.status.value not in ("terminated", "error"):
                    await self.factory.terminate(rec.agent_id)
            logger.info("All agents terminated")

        # Bus
        if self.bus:
            await self.bus.stop()
            logger.info("CommunicationBus stopped")

        # Memory
        if self.memory:
            self.memory.close()
            logger.info("SharedMemory closed")

        logger.info("👋 SWMAS Daemon stopped gracefully")

    def _signal_handler(self, sig: signal.Signals) -> None:
        """Handle SIGTERM / SIGINT."""
        logger.info("Received signal %s — triggering shutdown", sig.name)
        shutdown_event.set()


async def main_daemon(telegram_token: Optional[str] = None) -> None:
    """Entry point for daemon mode."""
    daemon = SwarmDaemon(telegram_token=telegram_token)

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, daemon._signal_handler, sig)

    try:
        await daemon.start()
        await daemon.run()
    except Exception as exc:
        logger.exception("Daemon fatal error: %s", exc)
        raise
    finally:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    # Allow token via env var for testing
    import os
    token = os.getenv("SWMAS_TELEGRAM_TOKEN")
    asyncio.run(main_daemon(telegram_token=token))
