"""
SWMAS — Main Entry Point
main.py

Usage:
    python main.py daemon --telegram-token <TOKEN>
    python main.py demo
    python main.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# Ensure Phase 1 + 2 are importable
_PHASE1 = Path(__file__).resolve().parent / "phase1"
_PHASE2 = Path(__file__).resolve().parent / "phase2"
for p in (_PHASE1, _PHASE2):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def cmd_daemon(args: argparse.Namespace) -> None:
    """Run SWMAS in 24/7 daemon mode with optional Telegram bot."""
    from daemon import main_daemon
    telegram_token: Optional[str] = args.telegram_token
    asyncio.run(main_daemon(telegram_token=telegram_token))


def cmd_demo(args: argparse.Namespace) -> None:
    """Run a quick standalone demo of the swarm core."""
    asyncio.run(_demo())


async def _demo() -> None:
    """Quick demo: initialize core, submit a test objective, show status."""
    from daemon import SwarmDaemon

    daemon = SwarmDaemon(telegram_token=None, db_path=":memory:")
    await daemon.start()

    # Submit a test objective
    obj_id = await daemon.orchestrator.submit_objective(
        description="Research the latest trends in AI agent swarms",
        priority=2,  # NORMAL
    )
    print(f"🎯 Submitted objective: {obj_id}")

    # Wait briefly for agents to spawn
    await asyncio.sleep(5)

    # Show status
    health = await daemon.orchestrator.health_check()
    print("\n📊 Swarm Health:")
    for section, data in health.items():
        print(f"  {section}: {data}")

    # List agents
    agents = daemon.factory.list_agents()
    print(f"\n🤖 Active Agents ({len(agents)}):")
    for a in agents[:10]:
        print(f"  • {a.agent_id} — {a.agent_type.value} ({a.status.value})")

    # Shutdown
    await daemon.stop()
    print("\n👋 Demo complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="swmas",
        description="SWMAS — Self-Wvolving Multiplicative AI Swarm",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Run 24/7 daemon with Telegram")
    p_daemon.add_argument(
        "--telegram-token",
        type=str,
        default=None,
        help="Telegram bot token (or set SWMAS_TELEGRAM_TOKEN env var)",
    )
    p_daemon.set_defaults(func=cmd_daemon)

    # demo
    p_demo = subparsers.add_parser("demo", help="Run quick standalone demo")
    p_demo.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
