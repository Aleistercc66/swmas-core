"""
SWMAS Phase 1 — Core Engine
agent_factory.py — Agent Factory

Dynamically spawns new agents based on type, context, and objective.
Manages agent lifecycle: creation, initialization, registration, tracking.
"""

from __future__ import annotations

import asyncio
import enum
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Awaitable, Type

from communication_bus import CommunicationBus, Message, Priority
from shared_memory import SharedMemory


class AgentType(enum.StrEnum):
    """Supported agent templates."""
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    EXECUTOR = "executor"
    MONITOR = "monitor"
    OPTIMIZER = "optimizer"
    LEARNER = "learner"


class AgentStatus(enum.StrEnum):
    """Agent lifecycle status."""
    SPAWNING = "spawning"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class AgentConfig:
    """Configuration for spawning an agent."""
    agent_type: AgentType
    objective: str
    context: dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    priority: Priority = Priority.NORMAL
    max_tasks: int = 10
    ttl: Optional[float] = None  # seconds until auto-terminate


@dataclass
class AgentRecord:
    """Registry entry for a spawned agent."""
    agent_id: str
    agent_type: AgentType
    status: AgentStatus
    config: AgentConfig
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    tasks_completed: int = 0
    tasks_failed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all SWMAS agents.

    Every agent runs in its own asyncio task, has access to the
    CommunicationBus and SharedMemory, and reports status back.
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        bus: CommunicationBus,
        memory: SharedMemory,
    ) -> None:
        self.agent_id = agent_id
        self.config = config
        self.bus = bus
        self.memory = memory
        self.status = AgentStatus.SPAWNING
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._metrics = {
            "messages_received": 0,
            "messages_sent": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
        }

    async def start(self) -> None:
        """Register handler and begin execution loop."""
        self.bus.register_handler(self.agent_id, self._on_message)
        await self.bus.subscribe(self.agent_id, self.agent_id)  # personal channel
        await self.bus.subscribe(self.agent_id, "swarm")         # swarm-wide channel
        self.status = AgentStatus.ACTIVE
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Gracefully stop the agent."""
        self._stop_event.set()
        self.bus.unregister_handler(self.agent_id)
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.status = AgentStatus.TERMINATED

    async def pause(self) -> None:
        """Pause execution (retain state)."""
        self.status = AgentStatus.PAUSED

    async def resume(self) -> None:
        """Resume from paused."""
        if self.status == AgentStatus.PAUSED:
            self.status = AgentStatus.ACTIVE

    async def _on_message(self, msg: Message) -> None:
        """Incoming message handler. Override in subclasses."""
        self._metrics["messages_received"] += 1
        # Default: acknowledge
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id=msg.sender_id,
            payload={"ack": True, "original_msg_id": msg.msg_id},
            channel=msg.channel,
            priority=Priority.LOW,
        )

    @abstractmethod
    async def _run_loop(self) -> None:
        """Main agent execution loop. Must be implemented by subclasses."""
        ...

    def get_status(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "type": self.config.agent_type.value,
            "status": self.status.value,
            "objective": self.config.objective,
            "metrics": dict(self._metrics),
        }


class PlaceholderAgent(BaseAgent):
    """
    Fallback agent that simply waits for tasks via messages.
    Used when no specialized subclass exists yet.
    """

    async def _run_loop(self) -> None:
        """Idle loop — real work happens via message handlers."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Heartbeat / idle work can go here
                pass


# ── Template registry ──
_AGENT_REGISTRY: dict[AgentType, Type[BaseAgent]] = {
    AgentType.RESEARCHER: PlaceholderAgent,
    AgentType.ANALYST: PlaceholderAgent,
    AgentType.EXECUTOR: PlaceholderAgent,
    AgentType.MONITOR: PlaceholderAgent,
    AgentType.OPTIMIZER: PlaceholderAgent,
    AgentType.LEARNER: PlaceholderAgent,
}


def register_agent_template(agent_type: AgentType, cls: Type[BaseAgent]) -> None:
    """Register a specialized agent class for a given type."""
    _AGENT_REGISTRY[agent_type] = cls


class AgentFactory:
    """
    Factory for creating, tracking, and managing agent lifecycle.

    - Spawns agents with unique IDs
    - Selects templates by AgentType
    - Initializes context and registers in swarm
    - Provides lifecycle API (pause, resume, terminate)
    """

    def __init__(self, bus: CommunicationBus, memory: SharedMemory) -> None:
        self.bus = bus
        self.memory = memory
        self._registry: dict[str, AgentRecord] = {}
        self._agents: dict[str, BaseAgent] = {}
        self._lock = asyncio.Lock()
        self._spawn_counter = 0

    async def spawn(self, config: AgentConfig) -> str:
        """
        Spawn a new agent.

        Returns:
            agent_id: Unique identifier for the new agent.
        """
        async with self._lock:
            self._spawn_counter += 1
            agent_id = f"{config.agent_type.value}-{self._spawn_counter:04d}-{uuid.uuid4().hex[:6]}"

        # Select template
        agent_class = _AGENT_REGISTRY.get(config.agent_type, PlaceholderAgent)

        # Instantiate
        agent = agent_class(
            agent_id=agent_id,
            config=config,
            bus=self.bus,
            memory=self.memory,
        )

        # Register
        record = AgentRecord(
            agent_id=agent_id,
            agent_type=config.agent_type,
            status=AgentStatus.SPAWNING,
            config=config,
            metadata={"parent_id": config.parent_id},
        )

        async with self._lock:
            self._registry[agent_id] = record
            self._agents[agent_id] = agent

        # Persist to shared memory
        self.memory.store(
            key=f"agent:{agent_id}",
            value=record.__dict__,
            agent_id=agent_id,
            channel="registry",
            tags=["agent", config.agent_type.value],
        )

        # Start
        await agent.start()
        record.status = AgentStatus.ACTIVE
        record.last_active = time.time()

        # Notify swarm
        await self.bus.broadcast(
            sender_id="factory",
            payload={
                "event": "agent_spawned",
                "agent_id": agent_id,
                "type": config.agent_type.value,
                "objective": config.objective,
            },
            channel="swarm",
            priority=Priority.HIGH,
        )

        return agent_id

    async def terminate(self, agent_id: str) -> bool:
        """Terminate an agent. Returns True if found."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return False

        await agent.stop()

        async with self._lock:
            if agent_id in self._registry:
                self._registry[agent_id].status = AgentStatus.TERMINATED
            self._agents.pop(agent_id, None)

        await self.bus.broadcast(
            sender_id="factory",
            payload={"event": "agent_terminated", "agent_id": agent_id},
            channel="swarm",
            priority=Priority.HIGH,
        )
        return True

    async def pause(self, agent_id: str) -> bool:
        """Pause an agent."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        await agent.pause()
        if agent_id in self._registry:
            self._registry[agent_id].status = AgentStatus.PAUSED
        return True

    async def resume(self, agent_id: str) -> bool:
        """Resume a paused agent."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        await agent.resume()
        if agent_id in self._registry:
            self._registry[agent_id].status = AgentStatus.ACTIVE
            self._registry[agent_id].last_active = time.time()
        return True

    def get_status(self, agent_id: str) -> Optional[AgentRecord]:
        """Get registry record for an agent."""
        return self._registry.get(agent_id)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get live agent instance."""
        return self._agents.get(agent_id)

    def list_agents(
        self,
        status: Optional[AgentStatus] = None,
        agent_type: Optional[AgentType] = None,
    ) -> list[AgentRecord]:
        """List agents with optional filtering."""
        results = list(self._registry.values())
        if status:
            results = [r for r in results if r.status == status]
        if agent_type:
            results = [r for r in results if r.agent_type == agent_type]
        return results

    def get_metrics(self) -> dict[str, Any]:
        return {
            "total_spawned": self._spawn_counter,
            "active": len([a for a in self._agents.values() if a.status == AgentStatus.ACTIVE]),
            "paused": len([a for a in self._agents.values() if a.status == AgentStatus.PAUSED]),
            "registry_size": len(self._registry),
        }
