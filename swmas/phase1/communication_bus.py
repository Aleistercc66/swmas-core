"""
SWMAS Phase 1 — Core Engine
communication_bus.py — AsyncIO Messaging Bus

Provides broadcast, channel-based routing, priority queues,
and agent-to-agent / agent-to-orchestrator communication.
"""

from __future__ import annotations

import asyncio
import enum
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Awaitable, Optional


class Priority(enum.IntEnum):
    """Message priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Message:
    """A message on the communication bus."""
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender_id: str = "system"
    recipient_id: Optional[str] = None  # None = broadcast
    channel: str = "default"
    priority: Priority = Priority.NORMAL
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "channel": self.channel,
            "priority": self.priority.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(
            msg_id=data.get("msg_id", str(uuid.uuid4())[:8]),
            sender_id=data.get("sender_id", "system"),
            recipient_id=data.get("recipient_id"),
            channel=data.get("channel", "default"),
            priority=Priority(data.get("priority", 2)),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            reply_to=data.get("reply_to"),
        )


class CommunicationBus:
    """
    AsyncIO-based messaging bus for the SWMAS swarm.

    Features:
    - Broadcast and directed messaging
    - Channel-based routing
    - Priority queue (asyncio.PriorityQueue)
    - Subscription model for agents
    - Message history for replay / audit
    """

    def __init__(self, history_limit: int = 10_000) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, Message]] = asyncio.PriorityQueue()
        self._subscribers: dict[str, list[str]] = {}  # channel -> [agent_id, ...]
        self._handlers: dict[str, Callable[[Message], Awaitable[None]]] = {}  # agent_id -> handler
        self._history: list[Message] = []
        self._history_limit = history_limit
        self._lock = asyncio.Lock()
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None
        self._metrics = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "broadcasts": 0,
        }

    async def start(self) -> None:
        """Start the dispatch loop."""
        if self._running:
            return
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        """Stop the dispatch loop."""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
            self._dispatch_task = None

    async def subscribe(self, agent_id: str, channel: str) -> None:
        """Subscribe an agent to a channel."""
        async with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = []
            if agent_id not in self._subscribers[channel]:
                self._subscribers[channel].append(agent_id)

    async def unsubscribe(self, agent_id: str, channel: str) -> None:
        """Unsubscribe an agent from a channel."""
        async with self._lock:
            if channel in self._subscribers:
                subs = self._subscribers[channel]
                if agent_id in subs:
                    subs.remove(agent_id)

    def register_handler(self, agent_id: str, handler: Callable[[Message], Awaitable[None]]) -> None:
        """Register a message handler for an agent."""
        self._handlers[agent_id] = handler

    def unregister_handler(self, agent_id: str) -> None:
        """Unregister an agent's message handler."""
        self._handlers.pop(agent_id, None)

    async def send(
        self,
        sender_id: str,
        recipient_id: Optional[str],
        payload: dict[str, Any],
        channel: str = "default",
        priority: Priority = Priority.NORMAL,
        reply_to: Optional[str] = None,
    ) -> Message:
        """
        Send a message (broadcast if recipient_id is None).
        Returns the sent Message for reference.
        """
        msg = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            channel=channel,
            priority=priority,
            payload=payload,
            reply_to=reply_to,
        )
        await self._queue.put((priority.value, msg))
        self._metrics["messages_sent"] += 1
        return msg

    async def broadcast(
        self,
        sender_id: str,
        payload: dict[str, Any],
        channel: str = "default",
        priority: Priority = Priority.NORMAL,
    ) -> Message:
        """Broadcast a message to all subscribers of a channel."""
        msg = await self.send(sender_id, None, payload, channel, priority)
        self._metrics["broadcasts"] += 1
        return msg

    async def _dispatch_loop(self) -> None:
        """Main dispatch loop — pulls from queue and routes to handlers."""
        while self._running:
            try:
                _, msg = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                await self._route(msg)
                self._history.append(msg)
                if len(self._history) > self._history_limit:
                    self._history.pop(0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"[CommunicationBus] Dispatch error: {exc}")

    async def _route(self, msg: Message) -> None:
        """Route a message to its recipient(s)."""
        delivered = 0
        async with self._lock:
            targets: list[str] = []
            if msg.recipient_id is not None:
                targets.append(msg.recipient_id)
            else:
                # Broadcast to channel subscribers
                targets.extend(self._subscribers.get(msg.channel, []))

        # Fire handlers concurrently
        tasks = []
        for agent_id in targets:
            handler = self._handlers.get(agent_id)
            if handler:
                tasks.append(asyncio.create_task(handler(msg)))
                delivered += 1

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._metrics["messages_delivered"] += delivered

    async def get_history(
        self,
        channel: Optional[str] = None,
        sender_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[Message]:
        """Query message history with optional filters."""
        results = self._history
        if channel:
            results = [m for m in results if m.channel == channel]
        if sender_id:
            results = [m for m in results if m.sender_id == sender_id]
        return results[-limit:]

    def get_metrics(self) -> dict[str, int]:
        """Return bus metrics."""
        return dict(self._metrics)

    def get_subscriber_count(self, channel: str) -> int:
        """Return number of subscribers on a channel."""
        return len(self._subscribers.get(channel, []))


# ── Convenience factory ──
async def create_bus() -> CommunicationBus:
    """Create and start a CommunicationBus instance."""
    bus = CommunicationBus()
    await bus.start()
    return bus
