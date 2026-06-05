"""
SWMAS Phase 2 — Agent Templates
monitor.py — Monitor Agent

Monitors swarm metrics, detects anomalies, sends alerts,
and tracks health across all agents and systems.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from agent_factory import BaseAgent, AgentConfig, AgentType, register_agent_template, AgentStatus
from communication_bus import CommunicationBus, Message, Priority
from shared_memory import SharedMemory


class MonitorAgent(BaseAgent):
    """
    Specialized agent for monitoring and alerting.

    Capabilities:
    - Periodic health checks on swarm components
    - Anomaly detection in metrics and behavior
    - Alert generation with severity levels
    - Metrics aggregation and trend analysis
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        bus: CommunicationBus,
        memory: SharedMemory,
    ) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._check_interval: float = 10.0  # seconds between checks
        self._alert_history: list[dict[str, Any]] = []
        self._thresholds = {
            "bus_queue_size": 100,
            "memory_entries_max": 45_000,
            "agent_error_rate": 0.2,
            "objective_timeout": 600,  # seconds
        }

    async def _run_loop(self) -> None:
        """Main monitoring loop — periodic health checks."""
        while not self._stop_event.is_set():
            try:
                await self._perform_health_check()
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._check_interval,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _on_message(self, msg: Message) -> None:
        """Handle incoming monitoring commands."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        command = payload.get("command", "")

        if command == "execute_task":
            obj_id = payload.get("objective_id", "")
            await self._monitor_objective(obj_id)

        elif command == "set_threshold":
            metric = payload.get("metric", "")
            value = payload.get("value", 0)
            self._thresholds[metric] = value

        elif command == "check_agent":
            agent_id = payload.get("target_agent", "")
            await self._check_specific_agent(agent_id)

        else:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "original_msg_id": msg.msg_id},
                channel=msg.channel,
                priority=Priority.LOW,
            )

    async def _perform_health_check(self) -> None:
        """Run a full swarm health check."""
        alerts: list[dict[str, Any]] = []
        timestamp = time.time()

        # Check bus metrics
        bus_metrics = self.bus.get_metrics()
        if bus_metrics.get("messages_sent", 0) > self._thresholds["bus_queue_size"]:
            alerts.append({
                "severity": "warning",
                "component": "communication_bus",
                "metric": "messages_sent",
                "value": bus_metrics["messages_sent"],
                "threshold": self._thresholds["bus_queue_size"],
                "message": "High message volume detected on bus",
            })

        # Check memory usage
        memory_stats = self.memory.get_stats()
        if memory_stats.get("total_entries", 0) > self._thresholds["memory_entries_max"]:
            alerts.append({
                "severity": "critical",
                "component": "shared_memory",
                "metric": "total_entries",
                "value": memory_stats["total_entries"],
                "threshold": self._thresholds["memory_entries_max"],
                "message": "Shared memory approaching capacity limit",
            })

        # Check for stale objectives
        objectives = self.memory.query(channel="objectives", limit=50)
        for obj_entry in objectives:
            obj = obj_entry.value
            if isinstance(obj, dict):
                created = obj.get("created_at", 0)
                status = obj.get("status", "")
                if status not in ("completed", "failed") and (timestamp - created) > self._thresholds["objective_timeout"]:
                    alerts.append({
                        "severity": "warning",
                        "component": "orchestrator",
                        "metric": "objective_age",
                        "value": round(timestamp - created, 0),
                        "threshold": self._thresholds["objective_timeout"],
                        "message": f"Objective {obj.get('objective_id', 'unknown')} is stale",
                    })

        # Check agent health from registry
        agent_entries = self.memory.query(channel="registry", limit=100)
        error_count = 0
        for entry in agent_entries:
            reg = entry.value
            if isinstance(reg, dict) and reg.get("status") == "error":
                error_count += 1

        total_agents = len(agent_entries)
        error_rate = error_count / max(total_agents, 1)
        if error_rate > self._thresholds["agent_error_rate"]:
            alerts.append({
                "severity": "critical",
                "component": "agent_factory",
                "metric": "error_rate",
                "value": round(error_rate, 2),
                "threshold": self._thresholds["agent_error_rate"],
                "message": f"High agent error rate: {error_count}/{total_agents}",
            })

        # Store and broadcast alerts
        if alerts:
            self._alert_history.extend(alerts)
            self.memory.store(
                key=f"alerts:{int(timestamp)}",
                value=alerts,
                agent_id=self.agent_id,
                channel="monitoring",
                tags=["alert", "health_check"],
            )

            for alert in alerts:
                await self.bus.broadcast(
                    sender_id=self.agent_id,
                    payload={
                        "event": "alert",
                        "severity": alert["severity"],
                        "component": alert["component"],
                        "message": alert["message"],
                        "timestamp": timestamp,
                    },
                    channel="swarm",
                    priority=Priority.CRITICAL if alert["severity"] == "critical" else Priority.HIGH,
                )

        # Store health snapshot
        self.memory.store(
            key=f"health:{int(timestamp)}",
            value={
                "timestamp": timestamp,
                "checks_performed": 4,
                "alerts_generated": len(alerts),
                "bus_metrics": bus_metrics,
                "memory_stats": memory_stats,
                "total_agents": total_agents,
                "error_count": error_count,
            },
            agent_id=self.agent_id,
            channel="monitoring",
            tags=["health", "snapshot"],
        )

        self._metrics["tasks_completed"] += 1

    async def _monitor_objective(self, objective_id: str) -> None:
        """Monitor a specific objective's progress."""
        obj_data = self.memory.retrieve(f"objective:{objective_id}")
        if obj_data is None:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id="orchestrator",
                payload={
                    "event": "alert",
                    "severity": "warning",
                    "message": f"Objective {objective_id} not found in memory",
                },
                channel="swarm",
                priority=Priority.HIGH,
            )
            return

        # Check progress
        results = self.memory.query(pattern=f"result:{objective_id}", limit=10)
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id="orchestrator",
            payload={
                "event": "status_report",
                "agent_id": self.agent_id,
                "objective_id": objective_id,
                "results_found": len(results),
                "status": "monitoring",
            },
            channel="swarm",
            priority=Priority.LOW,
        )

    async def _check_specific_agent(self, agent_id: str) -> None:
        """Run a targeted health check on one agent."""
        agent_data = self.memory.retrieve(f"agent:{agent_id}")
        if agent_data is None:
            await self.bus.broadcast(
                sender_id=self.agent_id,
                payload={
                    "event": "alert",
                    "severity": "warning",
                    "message": f"Agent {agent_id} not found in registry",
                },
                channel="swarm",
                priority=Priority.HIGH,
            )
            return

        # Report agent health
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id="orchestrator",
            payload={
                "event": "status_report",
                "agent_id": self.agent_id,
                "target_agent": agent_id,
                "agent_data": agent_data,
                "status": "checked",
            },
            channel="swarm",
            priority=Priority.LOW,
        )


def register() -> None:
    """Register this agent template with the factory."""
    register_agent_template(AgentType.MONITOR, MonitorAgent)
