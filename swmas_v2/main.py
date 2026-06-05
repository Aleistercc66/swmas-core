"""
SWMAS — Self-Wvolving Multiplicative AI Swarm
main.py — Entry Point

Modes:
    demo        — Run a full demonstration
    daemon      — Run 24/7 with optional Telegram
    status      — Show current swarm status
    help        — Show help

Usage:
    python main.py demo
    python main.py daemon --telegram-token <TOKEN>
    python main.py daemon --telegram-token <TOKEN> --allowed-users user1,user2
"""

from __future__ import annotations

import argparse
import asyncio
import sys

# Core engine
from communication_bus import CommunicationBus, Priority, create_bus
from shared_memory import SharedMemory
from agent_factory import AgentFactory, AgentConfig, AgentType
from orchestrator import Orchestrator

# Agent templates
import researcher; researcher.register()
import analyst; analyst.register()
import executor; executor.register()
import monitor; monitor.register()
import optimizer; optimizer.register()


async def bootstrap_swarm() -> tuple[CommunicationBus, SharedMemory, AgentFactory, Orchestrator]:
    """Initialize and bootstrap the SWMAS swarm."""
    print("[SWMAS] Bootstrapping swarm...")

    bus = await create_bus()
    memory = SharedMemory(db_path="swmas_memory.db")
    factory = AgentFactory(bus=bus, memory=memory)
    orchestrator = Orchestrator(bus=bus, memory=memory, factory=factory)

    await orchestrator.start()

    monitor_id = await factory.spawn(AgentConfig(
        agent_type=AgentType.MONITOR,
        objective="Swarm health monitoring",
        context={"auto_check": True},
        priority=Priority.CRITICAL,
    ))
    print(f"   [OK] Monitor spawned: {monitor_id}")

    print("[SWMAS] Swarm is LIVE. Orchestrator ready.")
    return bus, memory, factory, orchestrator


async def submit_task(
    orchestrator: Orchestrator,
    description: str,
    priority: int = 2,
) -> str:
    """Submit a task to the swarm."""
    p = Priority(priority)
    obj_id = await orchestrator.submit_objective(description, priority=p)
    print(f"Task submitted: {obj_id}")
    return obj_id


async def swarm_status(orchestrator: Orchestrator) -> None:
    """Display current swarm status."""
    health = await orchestrator.health_check()
    print("SWARM STATUS")
    print("-" * 40)
    print(f"Orchestrator: {'running' if health['orchestrator']['running'] else 'stopped'}")
    print(f"Objectives:   {health['orchestrator']['total_objectives']} total, "
          f"{health['orchestrator']['active_objectives']} active")
    print(f"Agents:       {health['factory']['total_spawned']} spawned, "
          f"{health['factory']['active']} active, {health['factory']['paused']} paused")
    print(f"Messages:     {health['bus']['messages_sent']} sent, "
          f"{health['bus']['messages_delivered']} delivered")
    print(f"Memory:       {health['memory']['total_entries']} entries / "
          f"{health['memory']['max_entries']} max")
    print("-" * 40)


async def demo_run() -> None:
    """Run a demonstration of the swarm capabilities."""
    bus, memory, factory, orchestrator = await bootstrap_swarm()

    print("=" * 50)
    print("SWMAS DEMONSTRATION")
    print("=" * 50)

    print("Submitting research task...")
    await submit_task(
        orchestrator,
        "Research the latest trends in autonomous multi-agent systems and swarm intelligence",
        priority=1,
    )

    print("Submitting analysis task...")
    await submit_task(
        orchestrator,
        "Analyze the research findings on swarm intelligence and identify key patterns",
        priority=2,
    )

    print("Submitting execution task...")
    await submit_task(
        orchestrator,
        "Build and deploy a prototype communication protocol for agent coordination",
        priority=1,
    )

    print("Letting swarm process tasks (5 seconds)...")
    await asyncio.sleep(5)

    await swarm_status(orchestrator)

    print("Recent Memory Entries:")
    entries = memory.query(limit=10)
    for entry in entries:
        print(f"   [{entry.channel}] {entry.key[:50]}...")

    print("Objectives:")
    for obj in orchestrator.list_objectives():
        status = obj.status.value
        print(f"   {obj.objective_id[:12]}... [{status}] {obj.description[:50]}...")

    print("Shutting down swarm...")
    await orchestrator.stop()
    await bus.stop()
    memory.close()
    print("Swarm shutdown complete.")


async def run_daemon(telegram_token: str | None, allowed_users: list[str] | None) -> None:
    """Run the swarm as a 24/7 daemon."""
    from swarm_daemon import SwarmDaemon
    daemon = SwarmDaemon()
    await daemon.main(telegram_token=telegram_token, allowed_users=allowed_users)


def print_help() -> None:
    """Print CLI help."""
    print("""
SWMAS — Self-Wvolving Multiplicative AI Swarm

Usage: python main.py <command> [options]

Commands:
    demo        Run a full demonstration
    daemon      Run 24/7 daemon (optional Telegram)
    status      Show swarm status
    help        Show this help message

Daemon Options:
    --telegram-token <TOKEN>    Telegram bot token
    --allowed-users <U1,U2,...> Comma-separated authorized Telegram usernames

Examples:
    python main.py demo
    python main.py daemon
    python main.py daemon --telegram-token 123456:ABC-DEF
    python main.py daemon --telegram-token 123456:ABC-DEF --allowed-users admin,user2
""")


def main() -> None:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="SWMAS — Self-Wvolving Multiplicative AI Swarm", add_help=False)
    parser.add_argument("command", nargs="?", default="help", help="Command to run")
    parser.add_argument("--telegram-token", default=None, help="Telegram bot token")
    parser.add_argument("--allowed-users", default=None, help="Comma-separated authorized usernames")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")

    args = parser.parse_args()

    if args.help or args.command == "help":
        print_help()
        return

    allowed_users = args.allowed_users.split(",") if args.allowed_users else None

    if args.command == "demo":
        try:
            asyncio.run(demo_run())
        except KeyboardInterrupt:
            print("Interrupted by user.")
            sys.exit(0)

    elif args.command == "daemon":
        try:
            asyncio.run(run_daemon(telegram_token=args.telegram_token, allowed_users=allowed_users))
        except KeyboardInterrupt:
            print("Interrupted by user.")
            sys.exit(0)

    elif args.command == "status":
        print("Status command requires a running swarm daemon.")
        print("Use 'python main.py daemon' to start one.")

    else:
        print(f"Unknown command: {args.command}")
        print_help()


if __name__ == "__main__":
    main()
