"""
SWMAS Phase 2 — Agent Templates
monitor.py — Monitor Agent

Παρακολουθεί metrics από bus και memory,
στέλνει alerts όταν εντοπίζει anomalies.
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


class MonitorAgent(BaseAgent):
    """
    Monitor Agent — εποπτεία της υγείας του swarm.

    Λειτουργίες:
    - Παρακολούθηση bus metrics (messages, delivery rate)
    - Παρακολούθηση memory stats (size, growth rate)
    - Detection of stalled agents, errors, resource spikes
    - Alert generation με throttling
    """

    def __init__(self, agent_id, config, bus, memory) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._check_interval = 10.0
        self._last_bus_metrics: dict[str, Any] = {}
        self._last_memory_stats: dict[str, int] = {}
        self._last_alert_ts = 0.0
        self._alert_cooldown = 30.0
        self._error_count = 0

    async def _run_loop(self) -> None:
        """Periodic health checks."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._check_interval)
            except asyncio.TimeoutError:
                if self.status.value != "active":
                    continue
                await self._health_check()

    async def _health_check(self) -> None:
        """Evaluate swarm health and fire alerts if needed."""
        alerts: list[str] = []

        # 1. Bus metrics drift
        bus_metrics = self.bus.get_metrics()
        if self._last_bus_metrics:
            sent_delta = bus_metrics.get("messages_sent", 0) - self._last_bus_metrics.get("messages_sent", 0)
            delivered_delta = bus_metrics.get("messages_delivered", 0) - self._last_bus_metrics.get("messages_delivered", 0)
            if sent_delta > 0 and delivered_delta == 0:
                alerts.append("bus_delivery_stalled")
        self._last_bus_metrics = bus_metrics

        # 2. Memory growth anomaly
        mem_stats = self.memory.get_stats()
        if self._last_memory_stats:
            old_entries = self._last_memory_stats.get("total_entries", 0)
            new_entries = mem_stats.get("total_entries", 0)
            if new_entries - old_entries > 500:  # >500 new entries in 10s
                alerts.append("memory_growth_spike")
        self._last_memory_stats = mem_stats

        # 3. Check for error signals in memory
        recent_errors = self.memory.query(tags=["error"], limit=10)
        if len(recent_errors) > 5:
            alerts.append("error_flood")

        # 4. Store health snapshot
        snapshot = {
            "timestamp": time.time(),
            "bus_metrics": bus_metrics,
            "memory_stats": mem_stats,
            "alerts": alerts,
        }
        self.memory.store(
            key=f"health:{self.agent_id}:{int(time.time())}",
            value=snapshot,
            agent_id=self.agent_id,
            channel="monitor",
            tags=["health", "snapshot"],
        )

        # 5. Broadcast alerts (throttled)
        if alerts and (time.time() - self._last_alert_ts) > self._alert_cooldown:
            self._last_alert_ts = time.time()
            await self.bus.broadcast(
                sender_id=self.agent_id,
                payload={
                    "event": "health_alert",
                    "alerts": alerts,
                    "severity": "high" if "error_flood" in alerts or "bus_delivery_stalled" in alerts else "medium",
                    "snapshot_key": f"health:{self.agent_id}:{int(time.time())}",
                },
                channel="swarm",
                priority=Priority.CRITICAL if "error_flood" in alerts else Priority.HIGH,
            )

    async def _on_message(self, msg: Message) -> None:
        """Handle commands."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        cmd = payload.get("command")

        if cmd == "execute_task":
            # Setup monitoring for a specific objective
            objective_id = payload.get("objective_id", "unknown")
            self.memory.store(
                key=f"monitor:objective:{objective_id}",
                value={"agent_id": self.agent_id, "started_at": time.time()},
                agent_id=self.agent_id,
                channel="monitor",
                tags=["monitor", "objective", objective_id],
            )
            self._metrics["tasks_completed"] += 1
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={
                    "event": "task_result",
                    "objective_id": objective_id,
                    "summary": f"Monitoring objective {objective_id}",
                },
                channel="swarm",
                priority=Priority.NORMAL,
            )
        elif cmd == "get_health":
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={
                    "event": "health_report",
                    "bus": self.bus.get_metrics(),
                    "memory": self.memory.get_stats(),
                    "subscriber_counts": {
                        ch: self.bus.get_subscriber_count(ch)
                        for ch in ("swarm", "default")
                    },
                },
                channel=msg.channel,
                priority=Priority.NORMAL,
            )
        else:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "msg_id": msg.msg_id, "status": "unknown_command"},
                channel=msg.channel,
                priority=Priority.LOW,
            )


def register() -> None:
    """Register this agent template."""
    register_agent_template(AgentType.MONITOR, MonitorAgent)
