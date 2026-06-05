"""
SWMAS Phase 2 — Agent Templates
optimizer.py — Optimizer Agent

Analyzes performance metrics, recommends improvements,
and suggests tuning parameters for swarm efficiency.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from agent_factory import BaseAgent, AgentConfig, AgentType, register_agent_template
from communication_bus import CommunicationBus, Message, Priority
from shared_memory import SharedMemory


class OptimizerAgent(BaseAgent):
    """
    Specialized agent for performance optimization and tuning.

    Capabilities:
    - Reads swarm-wide performance metrics
    - Identifies bottlenecks and inefficiencies
    - Recommends parameter tuning
    - Suggests structural improvements
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        bus: CommunicationBus,
        memory: SharedMemory,
    ) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._optimization_interval: float = 30.0  # seconds
        self._recommendations_history: list[dict[str, Any]] = []

    async def _run_loop(self) -> None:
        """Main optimization loop — periodic analysis and recommendations."""
        while not self._stop_event.is_set():
            try:
                await self._run_optimization_cycle()
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._optimization_interval,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _on_message(self, msg: Message) -> None:
        """Handle incoming optimization commands."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        command = payload.get("command", "")

        if command == "execute_task":
            obj_id = payload.get("objective_id", "")
            description = payload.get("description", "")
            await self._optimize(obj_id, description)

        elif command == "tune_agent":
            target_agent = payload.get("target_agent", "")
            metric = payload.get("metric", "")
            await self._tune_agent(target_agent, metric)

        elif command == "analyze_workload":
            await self._analyze_workload()

        else:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "original_msg_id": msg.msg_id},
                channel=msg.channel,
                priority=Priority.LOW,
            )

    async def _optimize(self, objective_id: str, description: str) -> None:
        """Run a full optimization analysis."""
        # Gather metrics
        bus_metrics = self.bus.get_metrics()
        memory_stats = self.memory.get_stats()
        health_snapshots = self.memory.query(channel="monitoring", tags=["health"], limit=10)
        execution_logs = self.memory.query(channel="execution", limit=20)

        # Analyze bottlenecks
        bottlenecks = self._identify_bottlenecks(
            bus_metrics, memory_stats, health_snapshots, execution_logs
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(bottlenecks)

        # Store optimization report
        report = {
            "objective_id": objective_id,
            "description": description,
            "optimized_by": self.agent_id,
            "timestamp": time.time(),
            "bottlenecks_found": len(bottlenecks),
            "recommendations_count": len(recommendations),
            "bottlenecks": bottlenecks,
            "recommendations": recommendations,
            "expected_improvement": self._estimate_improvement(recommendations),
        }

        self.memory.store(
            key=f"optimization:{objective_id}:{self.agent_id}",
            value=report,
            agent_id=self.agent_id,
            channel="optimization",
            tags=["optimization", "report", objective_id],
        )

        self._recommendations_history.extend(recommendations)

        # Send result
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id="orchestrator",
            payload={
                "event": "task_result",
                "objective_id": objective_id,
                "agent_id": self.agent_id,
                "agent_type": "optimizer",
                "summary": f"Found {len(bottlenecks)} bottlenecks, {len(recommendations)} recommendations",
                "report_key": f"optimization:{objective_id}:{self.agent_id}",
                "expected_improvement": report["expected_improvement"],
            },
            channel="swarm",
            priority=Priority.NORMAL,
        )

        self._metrics["tasks_completed"] += 1

    async def _tune_agent(self, target_agent: str, metric: str) -> None:
        """Suggest tuning for a specific agent."""
        agent_data = self.memory.retrieve(f"agent:{target_agent}")
        if agent_data is None:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id="orchestrator",
                payload={
                    "event": "agent_error",
                    "agent_id": self.agent_id,
                    "error": f"Cannot tune: agent {target_agent} not found",
                },
                channel="swarm",
                priority=Priority.HIGH,
            )
            return

        tuning = {
            "target_agent": target_agent,
            "metric": metric,
            "suggestions": [],
            "timestamp": time.time(),
        }

        if metric == "speed":
            tuning["suggestions"] = [
                {"param": "task_batch_size", "current": 1, "recommended": 5, "reason": "parallel processing"},
                {"param": "heartbeat_interval", "current": 5, "recommended": 10, "reason": "reduce overhead"},
            ]
        elif metric == "accuracy":
            tuning["suggestions"] = [
                {"param": "validation_depth", "current": 1, "recommended": 3, "reason": "more checks"},
            ]
        elif metric == "memory":
            tuning["suggestions"] = [
                {"param": "cache_ttl", "current": 3600, "recommended": 1800, "reason": "faster eviction"},
            ]

        self.memory.store(
            key=f"tuning:{target_agent}:{metric}",
            value=tuning,
            agent_id=self.agent_id,
            channel="optimization",
            tags=["tuning", target_agent, metric],
        )

    async def _analyze_workload(self) -> None:
        """Analyze current swarm workload distribution."""
        # Count agents by type
        registry = self.memory.query(channel="registry", limit=100)
        type_counts: dict[str, int] = {}
        for entry in registry:
            reg = entry.value
            if isinstance(reg, dict):
                t = reg.get("agent_type", "unknown")
                type_counts[t] = type_counts.get(t, 0) + 1

        workload = {
            "timestamp": time.time(),
            "agent_distribution": type_counts,
            "total_agents": len(registry),
            "recommendations": [],
        }

        # Recommend rebalancing if needed
        if type_counts.get("executor", 0) > type_counts.get("monitor", 0) * 3:
            workload["recommendations"].append("Add more monitor agents for better coverage")

        if type_counts.get("researcher", 0) > type_counts.get("analyst", 0) * 2:
            workload["recommendations"].append("Add more analysts to process research backlog")

        self.memory.store(
            key=f"workload:{int(time.time())}",
            value=workload,
            agent_id=self.agent_id,
            channel="optimization",
            tags=["workload", "analysis"],
        )

    def _identify_bottlenecks(
        self,
        bus_metrics: dict[str, int],
        memory_stats: dict[str, int],
        health_snapshots: list[Any],
        execution_logs: list[Any],
    ) -> list[dict[str, Any]]:
        """Identify performance bottlenecks."""
        bottlenecks = []

        # Bus bottleneck
        if bus_metrics.get("messages_sent", 0) > bus_metrics.get("messages_delivered", 0) * 2:
            bottlenecks.append({
                "type": "communication",
                "component": "communication_bus",
                "severity": "high",
                "description": "Message delivery lag detected",
                "metric": "delivery_ratio",
                "value": bus_metrics.get("messages_delivered", 0) / max(bus_metrics.get("messages_sent", 1), 1),
            })

        # Memory bottleneck
        usage_ratio = memory_stats.get("total_entries", 0) / max(memory_stats.get("max_entries", 1), 1)
        if usage_ratio > 0.8:
            bottlenecks.append({
                "type": "storage",
                "component": "shared_memory",
                "severity": "critical" if usage_ratio > 0.95 else "high",
                "description": "Shared memory near capacity",
                "metric": "usage_ratio",
                "value": round(usage_ratio, 2),
            })

        # Execution bottleneck
        if execution_logs:
            fail_count = sum(1 for e in execution_logs if isinstance(e.value, dict) and not e.value.get("success", True))
            if fail_count > len(execution_logs) * 0.3:
                bottlenecks.append({
                    "type": "execution",
                    "component": "executor_agents",
                    "severity": "high",
                    "description": f"High execution failure rate: {fail_count}/{len(execution_logs)}",
                    "metric": "failure_rate",
                    "value": round(fail_count / max(len(execution_logs), 1), 2),
                })

        return bottlenecks

    def _generate_recommendations(self, bottlenecks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate optimization recommendations from bottlenecks."""
        recommendations = []

        for bottleneck in bottlenecks:
            b_type = bottleneck["type"]
            severity = bottleneck["severity"]

            if b_type == "communication":
                recommendations.append({
                    "target": "communication_bus",
                    "action": "increase_workers",
                    "description": "Add dispatch workers or increase queue processing rate",
                    "priority": severity,
                    "expected_impact": "reduce latency by 30-50%",
                })
                recommendations.append({
                    "target": "communication_bus",
                    "action": "batch_messages",
                    "description": "Enable message batching for non-critical traffic",
                    "priority": "medium",
                    "expected_impact": "reduce bus load by 20-30%",
                })

            elif b_type == "storage":
                recommendations.append({
                    "target": "shared_memory",
                    "action": "increase_capacity",
                    "description": "Scale memory.max_entries or add tiered storage",
                    "priority": severity,
                    "expected_impact": "eliminate memory pressure",
                })
                recommendations.append({
                    "target": "shared_memory",
                    "action": "aggressive_ttl",
                    "description": "Reduce TTL defaults to free old entries faster",
                    "priority": "medium",
                    "expected_impact": "improve eviction efficiency",
                })

            elif b_type == "execution":
                recommendations.append({
                    "target": "executor_agents",
                    "action": "add_executors",
                    "description": "Spawn additional executor agents to handle load",
                    "priority": severity,
                    "expected_impact": "distribute execution load",
                })
                recommendations.append({
                    "target": "executor_agents",
                    "action": "retry_policy",
                    "description": "Implement exponential backoff for failed tasks",
                    "priority": "medium",
                    "expected_impact": "reduce transient failures",
                })

        # Always suggest general improvements
        recommendations.append({
            "target": "swarm",
            "action": "metrics_dashboard",
            "description": "Add real-time metrics dashboard for visibility",
            "priority": "low",
            "expected_impact": "better operational awareness",
        })

        return recommendations

    def _estimate_improvement(self, recommendations: list[dict[str, Any]]) -> dict[str, Any]:
        """Estimate aggregate improvement from recommendations."""
        high_priority = sum(1 for r in recommendations if r["priority"] in ("high", "critical"))
        total = len(recommendations)

        return {
            "recommendations_total": total,
            "high_priority_count": high_priority,
            "estimated_latency_reduction": f"{min(high_priority * 15, 60)}%",
            "estimated_throughput_increase": f"{min(high_priority * 20, 80)}%",
            "confidence": "medium",
        }


def register() -> None:
    """Register this agent template with the factory."""
    register_agent_template(AgentType.OPTIMIZER, OptimizerAgent)
