"""
SWMAS Phase 2 — Agent Templates
optimizer.py — Optimizer Agent

Διαβάζει performance metrics, προτείνει βελτιώσεις,
κάνει tuning suggestions για το swarm.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

# Path setup for Phase 1 imports
import sys
from pathlib import Path
_PHASE1 = Path(__file__).resolve().parent.parent / "phase1"
if str(_PHASE1) not in sys.path:
    sys.path.insert(0, str(_PHASE1))

from agent_factory import BaseAgent, AgentType, register_agent_template
from communication_bus import Message, Priority


class OptimizerAgent(BaseAgent):
    """
    Optimizer Agent — βελτιστοποιεί το swarm βάσει δεδομένων.

    Λειτουργίες:
    - Ανάγνωση metrics από bus, memory, agents
    - Detection inefficiencies (stalled queues, idle agents, high error rates)
    - Παραγωγή tuning suggestions
    - Auto-recommendation για resource reallocation
    """

    def __init__(self, agent_id, config, bus, memory) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._scan_interval = 20.0
        self._suggestion_history: list[dict[str, Any]] = []

    async def _run_loop(self) -> None:
        """Periodic optimization scans."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._scan_interval)
            except asyncio.TimeoutError:
                if self.status.value != "active":
                    continue
                await self._optimization_scan()

    async def _optimization_scan(self) -> None:
        """Analyze swarm performance and generate suggestions."""
        suggestions: list[dict[str, Any]] = []

        # 1. Bus efficiency
        bus_metrics = self.bus.get_metrics()
        sent = bus_metrics.get("messages_sent", 0)
        delivered = bus_metrics.get("messages_delivered", 0)
        if sent > 0:
            delivery_rate = delivered / sent
            if delivery_rate < 0.8:
                suggestions.append({
                    "area": "communication_bus",
                    "issue": "low_delivery_rate",
                    "current": delivery_rate,
                    "recommendation": "Check for unsubscribed agents or handler crashes; consider retry policy",
                    "priority": "high",
                })

        # 2. Memory pressure
        mem_stats = self.memory.get_stats()
        total = mem_stats.get("total_entries", 0)
        max_cap = mem_stats.get("max_entries", 50000)
        if total / max_cap > 0.9:
            suggestions.append({
                "area": "shared_memory",
                "issue": "near_capacity",
                "current": f"{total}/{max_cap}",
                "recommendation": "Increase max_entries or add aggressive TTL cleanup",
                "priority": "critical",
            })
        elif total / max_cap > 0.7:
            suggestions.append({
                "area": "shared_memory",
                "issue": "growing_fast",
                "current": f"{total}/{max_cap}",
                "recommendation": "Review TTL policies; archive old entries",
                "priority": "medium",
            })

        # 3. Agent efficiency via memory scan
        agent_entries = self.memory.query(channel="registry", limit=100)
        active_count = sum(1 for e in agent_entries if "active" in str(e.value))
        if active_count > 20:
            suggestions.append({
                "area": "agent_factory",
                "issue": "high_agent_count",
                "current": active_count,
                "recommendation": "Consider agent pool limits or auto-terminate idle agents",
                "priority": "medium",
            })

        # Store suggestions
        if suggestions:
            suggestion_key = f"optimizer:suggestions:{int(time.time())}"
            self.memory.store(
                key=suggestion_key,
                value={
                    "timestamp": time.time(),
                    "suggestions": suggestions,
                    "count": len(suggestions),
                },
                agent_id=self.agent_id,
                channel="optimizer",
                tags=["optimizer", "suggestions"],
            )
            self._suggestion_history.extend(suggestions)

            # Notify swarm if critical
            critical = [s for s in suggestions if s.get("priority") == "critical"]
            if critical:
                await self.bus.broadcast(
                    sender_id=self.agent_id,
                    payload={
                        "event": "optimization_alert",
                        "critical_suggestions": len(critical),
                        "suggestion_key": suggestion_key,
                    },
                    channel="swarm",
                    priority=Priority.CRITICAL,
                )

    async def _on_message(self, msg: Message) -> None:
        """Handle commands."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        cmd = payload.get("command")

        if cmd == "execute_task":
            await self._handle_execute_task(payload, msg.sender_id)
        elif cmd == "get_suggestions":
            await self._handle_get_suggestions(msg.sender_id)
        else:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "msg_id": msg.msg_id, "status": "unknown_command"},
                channel=msg.channel,
                priority=Priority.LOW,
            )

    async def _handle_execute_task(self, payload: dict[str, Any], sender: str) -> None:
        """Run on-demand optimization for a specific objective area."""
        objective_id = payload.get("objective_id", "unknown")
        area = payload.get("area", "general")

        # Pull area-specific metrics
        if area == "bus":
            metrics = self.bus.get_metrics()
            rec = "Increase queue workers if backlog detected" if metrics.get("messages_sent", 0) > 1000 else "Bus operating normally"
        elif area == "memory":
            stats = self.memory.get_stats()
            rec = f"Memory at {stats.get('total_entries',0)}/{stats.get('max_entries',50000)} — review TTLs if >80%"
        else:
            rec = "Run full scan for detailed suggestions"

        result = {
            "objective_id": objective_id,
            "area": area,
            "recommendation": rec,
            "timestamp": time.time(),
        }
        key = f"optimizer:task:{objective_id}:{int(time.time())}"
        self.memory.store(key=key, value=result, agent_id=self.agent_id, channel="optimizer", tags=["optimizer", "task"])

        self._metrics["tasks_completed"] += 1
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id=sender,
            payload={
                "event": "task_result",
                "objective_id": objective_id,
                "summary": rec,
                "result_key": key,
            },
            channel="swarm",
            priority=Priority.HIGH,
        )

    async def _handle_get_suggestions(self, sender: str) -> None:
        """Return all recent suggestions."""
        recent = self.memory.query(channel="optimizer", limit=20)
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id=sender,
            payload={
                "event": "suggestions_list",
                "count": len(self._suggestion_history),
                "recent_keys": [e.key for e in recent],
            },
            channel="swarm",
            priority=Priority.NORMAL,
        )


def register() -> None:
    """Register this agent template."""
    register_agent_template(AgentType.OPTIMIZER, OptimizerAgent)
