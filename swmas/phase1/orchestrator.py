"""
SWMAS Phase 1 — Core Engine
orchestrator.py — Swarm Orchestrator (Kimi Brain Layer)

Strategic analyzer, task allocator, quality controller.
Accepts objectives, decides what the swarm needs, routes tasks,
and synthesizes results back to the brain (Kimi).
"""

from __future__ import annotations

import asyncio
import enum
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from communication_bus import CommunicationBus, Message, Priority
from shared_memory import SharedMemory
from agent_factory import AgentFactory, AgentConfig, AgentType, AgentStatus, BaseAgent


class ObjectiveStatus(enum.StrEnum):
    """Status of a high-level objective."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    DISPATCHING = "dispatching"
    EXECUTING = "executing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Objective:
    """A top-level objective given to the swarm."""
    objective_id: str = field(default_factory=lambda: f"obj-{uuid.uuid4().hex[:8]}")
    description: str = ""
    priority: Priority = Priority.NORMAL
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    assigned_agents: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    """
    The brain of the SWMAS swarm.

    Responsibilities:
    1. Accept objectives from external sources (Kimi, user, system)
    2. Analyze and decompose into sub-tasks
    3. Decide if new agents are needed or existing ones suffice
    4. Dispatch tasks via the AgentFactory and CommunicationBus
    5. Monitor execution, collect results
    6. Synthesize and report back
    7. Quality control — retry, escalate, or spawn helpers
    """

    def __init__(
        self,
        bus: CommunicationBus,
        memory: SharedMemory,
        factory: AgentFactory,
    ) -> None:
        self.bus = bus
        self.memory = memory
        self.factory = factory
        self._objectives: dict[str, Objective] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._metrics = {
            "objectives_received": 0,
            "objectives_completed": 0,
            "objectives_failed": 0,
            "agents_spawned": 0,
            "tasks_dispatched": 0,
        }

    async def start(self) -> None:
        """Start the orchestrator loop."""
        if self._running:
            return
        self._running = True
        # Register handler for result messages
        self.bus.register_handler("orchestrator", self._on_message)
        await self.bus.subscribe("orchestrator", "swarm")
        self._task = asyncio.create_task(self._control_loop())

    async def stop(self) -> None:
        """Stop the orchestrator."""
        self._running = False
        self.bus.unregister_handler("orchestrator")
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def submit_objective(
        self,
        description: str,
        priority: Priority = Priority.NORMAL,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Submit a new objective to the swarm.

        Returns:
            objective_id: Unique ID for tracking.
        """
        obj = Objective(
            description=description,
            priority=priority,
            metadata=metadata or {},
        )
        self._objectives[obj.objective_id] = obj
        self._metrics["objectives_received"] += 1

        # Persist
        self.memory.store(
            key=f"objective:{obj.objective_id}",
            value=obj.__dict__,
            agent_id="orchestrator",
            channel="objectives",
            tags=["objective", priority.name],
        )

        # Notify swarm
        await self.bus.broadcast(
            sender_id="orchestrator",
            payload={
                "event": "objective_submitted",
                "objective_id": obj.objective_id,
                "description": description,
                "priority": priority.value,
            },
            channel="swarm",
            priority=priority,
        )

        return obj.objective_id

    async def _control_loop(self) -> None:
        """Main control loop — processes objectives and manages swarm."""
        while self._running:
            try:
                # Process pending objectives
                pending = [
                    o for o in self._objectives.values()
                    if o.status in (ObjectiveStatus.PENDING, ObjectiveStatus.ANALYZING)
                ]
                for obj in pending:
                    await self._process_objective(obj)

                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"[Orchestrator] Control loop error: {exc}")

    async def _process_objective(self, obj: Objective) -> None:
        """
        Analyze an objective and dispatch to the swarm.
        Phase 1 simplified: decompose into 1-N tasks and spawn/route.
        """
        obj.status = ObjectiveStatus.ANALYZING

        # ── DECISION: What does this objective need? ──
        analysis = self._analyze_objective(obj)

        # ── DECISION: Spawn new agents or reuse? ──
        needed_agents = await self._decide_agents(obj, analysis)

        obj.status = ObjectiveStatus.DISPATCHING
        for agent_id in needed_agents:
            await self._dispatch_to_agent(obj, agent_id, analysis)

        obj.status = ObjectiveStatus.EXECUTING
        self._metrics["tasks_dispatched"] += len(needed_agents)

    def _analyze_objective(self, obj: Objective) -> dict[str, Any]:
        """
        Strategic analysis of an objective.
        Phase 1: keyword-based heuristic. Future: LLM call.
        """
        desc = obj.description.lower()
        analysis = {
            "needs_research": any(k in desc for k in ["research", "find", "discover", "look up"]),
            "needs_analysis": any(k in desc for k in ["analyze", "evaluate", "assess", "compare"]),
            "needs_execution": any(k in desc for k in ["execute", "run", "deploy", "build", "create"]),
            "needs_monitoring": any(k in desc for k in ["monitor", "watch", "track", "alert"]),
            "urgency": obj.priority.value <= Priority.HIGH.value,
            "complexity": "high" if len(desc) > 200 else "medium" if len(desc) > 100 else "low",
        }
        return analysis

    async def _decide_agents(
        self,
        obj: Objective,
        analysis: dict[str, Any],
    ) -> list[str]:
        """
        Decide which agents to use for this objective.
        Returns list of agent_ids (spawning new ones if needed).
        """
        agents: list[str] = []
        factory = self.factory

        # Try to find existing active agents first
        if analysis["needs_research"]:
            existing = factory.list_agents(agent_type=AgentType.RESEARCHER, status=AgentStatus.ACTIVE)
            if existing:
                agents.append(existing[0].agent_id)
            else:
                agent_id = await factory.spawn(AgentConfig(
                    agent_type=AgentType.RESEARCHER,
                    objective=f"Research for {obj.objective_id}: {obj.description[:80]}",
                    context={"objective_id": obj.objective_id},
                    priority=obj.priority,
                ))
                agents.append(agent_id)
                self._metrics["agents_spawned"] += 1

        if analysis["needs_analysis"]:
            existing = factory.list_agents(agent_type=AgentType.ANALYST, status=AgentStatus.ACTIVE)
            if existing:
                agents.append(existing[0].agent_id)
            else:
                agent_id = await factory.spawn(AgentConfig(
                    agent_type=AgentType.ANALYST,
                    objective=f"Analyze for {obj.objective_id}: {obj.description[:80]}",
                    context={"objective_id": obj.objective_id},
                    priority=obj.priority,
                ))
                agents.append(agent_id)
                self._metrics["agents_spawned"] += 1

        if analysis["needs_execution"]:
            agent_id = await factory.spawn(AgentConfig(
                agent_type=AgentType.EXECUTOR,
                objective=f"Execute for {obj.objective_id}: {obj.description[:80]}",
                context={"objective_id": obj.objective_id},
                priority=obj.priority,
            ))
            agents.append(agent_id)
            self._metrics["agents_spawned"] += 1

        if analysis["needs_monitoring"]:
            agent_id = await factory.spawn(AgentConfig(
                agent_type=AgentType.MONITOR,
                objective=f"Monitor for {obj.objective_id}: {obj.description[:80]}",
                context={"objective_id": obj.objective_id},
                priority=obj.priority,
            ))
            agents.append(agent_id)
            self._metrics["agents_spawned"] += 1

        # Fallback: if no specific need, spawn a general executor
        if not agents:
            agent_id = await factory.spawn(AgentConfig(
                agent_type=AgentType.EXECUTOR,
                objective=f"Handle objective {obj.objective_id}: {obj.description[:80]}",
                context={"objective_id": obj.objective_id},
                priority=obj.priority,
            ))
            agents.append(agent_id)
            self._metrics["agents_spawned"] += 1

        obj.assigned_agents = agents
        return agents

    async def _dispatch_to_agent(
        self,
        obj: Objective,
        agent_id: str,
        analysis: dict[str, Any],
    ) -> None:
        """Send task instructions to an agent."""
        await self.bus.send(
            sender_id="orchestrator",
            recipient_id=agent_id,
            payload={
                "command": "execute_task",
                "objective_id": obj.objective_id,
                "description": obj.description,
                "analysis": analysis,
                "deadline": time.time() + 300,  # 5 min default
            },
            channel=agent_id,
            priority=obj.priority,
        )

    async def _on_message(self, msg: Message) -> None:
        """Handle incoming messages (results, status, errors)."""
        payload = msg.payload
        event = payload.get("event", "")

        if event == "task_result":
            obj_id = payload.get("objective_id")
            if obj_id and obj_id in self._objectives:
                obj = self._objectives[obj_id]
                obj.results.append(payload)
                await self._evaluate_progress(obj)

        elif event == "agent_error":
            # Quality control: retry or escalate
            agent_id = payload.get("agent_id")
            obj_id = payload.get("objective_id")
            print(f"[Orchestrator] Agent {agent_id} error on {obj_id}: {payload.get('error')}")
            # Phase 1: log and continue. Phase 3: auto-retry with optimizer.

        elif event == "status_report":
            # Update registry
            pass

    async def _evaluate_progress(self, obj: Objective) -> None:
        """
        Evaluate if objective is complete.
        Phase 1: mark complete when any result arrives.
        Phase 3: smarter synthesis with cross-validation.
        """
        if obj.results:
            obj.status = ObjectiveStatus.SYNTHESIZING
            # Simple synthesis: store best result
            best = obj.results[-1]
            self.memory.store(
                key=f"result:{obj.objective_id}",
                value=best,
                agent_id="orchestrator",
                channel="results",
                tags=["result", obj.objective_id],
            )
            obj.status = ObjectiveStatus.COMPLETED
            obj.completed_at = time.time()
            self._metrics["objectives_completed"] += 1

            await self.bus.broadcast(
                sender_id="orchestrator",
                payload={
                    "event": "objective_completed",
                    "objective_id": obj.objective_id,
                    "result_summary": best.get("summary", "done"),
                },
                channel="swarm",
                priority=Priority.HIGH,
            )

    def get_objective(self, objective_id: str) -> Optional[Objective]:
        """Get objective by ID."""
        return self._objectives.get(objective_id)

    def list_objectives(
        self,
        status: Optional[ObjectiveStatus] = None,
    ) -> list[Objective]:
        """List objectives with optional filtering."""
        results = list(self._objectives.values())
        if status:
            results = [o for o in results if o.status == status]
        return results

    def get_metrics(self) -> dict[str, Any]:
        """Return orchestrator metrics."""
        return {
            **self._metrics,
            "active_objectives": len([o for o in self._objectives.values() if o.status not in (ObjectiveStatus.COMPLETED, ObjectiveStatus.FAILED)]),
            "total_objectives": len(self._objectives),
        }

    async def health_check(self) -> dict[str, Any]:
        """Quick health snapshot of the entire swarm."""
        return {
            "orchestrator": {"running": self._running, **self.get_metrics()},
            "factory": self.factory.get_metrics(),
            "bus": self.bus.get_metrics(),
            "memory": self.memory.get_stats(),
        }
