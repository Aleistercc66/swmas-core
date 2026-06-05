"""Event-driven messaging with Redis Streams and fallback to in-memory."""
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from redis.asyncio.client import Redis

from config import get_settings

logger = logging.getLogger("event_bus")


# ───────────────────────────────────────────────
# Event Types
# ───────────────────────────────────────────────

class EventType(str, Enum):
    """Standard event types for the swarm."""
    TOKENS_DISCOVERED = "tokens_discovered"
    TOKENS_VALIDATED = "tokens_validated"
    RISK_ASSESSED = "risk_assessed"
    SIGNAL_GENERATED = "signal_generated"
    POSITION_OPENED = "position_opened"
    POSITION_UPDATED = "position_updated"
    POSITION_CLOSED = "position_closed"
    STOP_HIT = "stop_hit"
    TAKE_PROFIT = "take_profit"
    ALERT = "alert"
    HEARTBEAT = "heartbeat"


# ───────────────────────────────────────────────
# Event Data Model
# ───────────────────────────────────────────────

@dataclass
class SwarmEvent:
    """Standardized event for inter-agent communication."""
    event_type: str
    source: str  # agent name
    timestamp: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    priority: int = 0  # 0=normal, 1=high, 2=critical
    
    def to_dict(self) -> Dict[str, Any]:
        def _serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, list):
                return [_serialize(i) for i in obj]
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            return obj
        
        return {
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": json.dumps(_serialize(self.data)),
            "correlation_id": self.correlation_id or "",
            "priority": self.priority,
        }
    
    @classmethod
    def from_stream(cls, msg_id: str, fields: Dict[bytes, bytes]) -> "SwarmEvent":
        """Parse from Redis Stream message."""
        return cls(
            event_type=fields[b"event_type"].decode(),
            source=fields[b"source"].decode(),
            timestamp=fields[b"timestamp"].decode(),
            data=json.loads(fields[b"data"].decode()),
            correlation_id=fields.get(b"correlation_id", b"").decode() or None,
            priority=int(fields.get(b"priority", b"0")),
        )


# ───────────────────────────────────────────────
# Backward-Compatible Emit Functions
# ───────────────────────────────────────────────

async def emit_event(
    event_type: str,
    data: Dict[str, Any],
    source: str = "unknown",
    correlation_id: Optional[str] = None,
) -> Optional[str]:
    """Backward-compatible event emitter."""
    bus = await get_event_bus()
    return await bus.publish_simple(
        event_type=event_type,
        data=data,
        source=source,
        correlation_id=correlation_id,
    )


async def emit_token_discovered(
    symbol: str,
    batch_id: str,
    payload: Dict[str, Any],
) -> Optional[str]:
    """Emit token discovered event."""
    return await emit_event(
        event_type=EventType.TOKENS_DISCOVERED,
        data={
            "symbol": symbol,
            "batch_id": batch_id,
            "payload": payload,
        },
        source="scanner",
        correlation_id=batch_id,
    )


async def emit_validated(
    validator_output_id: int,
    symbol: str,
    tier: str,
    confidence: float,
    is_approved: bool,
) -> Optional[str]:
    """Emit validation completed event."""
    return await emit_event(
        event_type=EventType.TOKENS_VALIDATED,
        data={
            "validator_output_id": validator_output_id,
            "symbol": symbol,
            "tier": tier,
            "confidence": confidence,
            "is_approved": is_approved,
        },
        source="validator",
    )


async def emit_risk_assessed(
    risk_id: int,
    symbol: str,
    tier: str,
    composite_score: float,
    is_active: bool,
) -> Optional[str]:
    """Emit risk assessment event."""
    return await emit_event(
        event_type=EventType.RISK_ASSESSED,
        data={
            "risk_id": risk_id,
            "symbol": symbol,
            "tier": tier,
            "composite_score": composite_score,
            "is_active": is_active,
        },
        source="risk_engine",
    )


async def emit_position_opened(
    position_id: int,
    symbol: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
) -> Optional[str]:
    """Emit position opened event."""
    return await emit_event(
        event_type=EventType.POSITION_OPENED,
        data={
            "position_id": position_id,
            "symbol": symbol,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        },
        source="executor",
    )


async def emit_position_closed(
    position_id: int,
    symbol: str,
    close_price: float,
    pnl_pct: float,
    close_reason: str,
) -> Optional[str]:
    """Emit position closed event."""
    return await emit_event(
        event_type=EventType.POSITION_CLOSED,
        data={
            "position_id": position_id,
            "symbol": symbol,
            "close_price": close_price,
            "pnl_pct": pnl_pct,
            "close_reason": close_reason,
        },
        source="executor",
    )


async def emit_alert(
    alert_type: str,
    symbol: str,
    message: str,
    data: Dict[str, Any],
) -> Optional[str]:
    """Emit alert event."""
    return await emit_event(
        event_type=EventType.ALERT,
        data={
            "alert_type": alert_type,
            "symbol": symbol,
            "message": message,
            "data": data,
        },
        source="system",
    )


# ───────────────────────────────────────────────
# SystemEvent (backward compatible wrapper)
# ───────────────────────────────────────────────

class SystemEvent:
    """Wrapper for backward compatibility."""
    
    def __init__(self, event_type: str, data: Dict[str, Any], source: str = "system"):
        self.event_type = event_type
        self.data = data
        self.source = source
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    async def emit(self) -> Optional[str]:
        return await emit_event(
            event_type=self.event_type,
            data=self.data,
            source=self.source,
        )


# ───────────────────────────────────────────────
# Event Bus Implementation
# ───────────────────────────────────────────────

class EventBus:
    """Redis Streams-based event bus with in-memory fallback."""
    
    def __init__(self):
        self.settings = get_settings()
        self.prefix = self.settings.event_stream_prefix
        self.redis: Optional[Redis] = None
        self._connected = False
        self._handlers: Dict[str, List[Callable]] = {}
        self._memory_queue: asyncio.Queue = asyncio.Queue()
        self._shutdown = False
    
    # ── Connection ──
    
    async def connect(self) -> bool:
        """Connect to Redis. Returns True if successful."""
        try:
            self.redis = redis.from_url(
                self.settings.redis_url,
                decode_responses=False,  # We handle decoding manually
                max_connections=self.settings.redis_max_connections,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            await self.redis.ping()
            self._connected = True
            logger.info("EventBus connected to Redis")
            return True
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Clean disconnect."""
        self._shutdown = True
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("EventBus disconnected")
    
    # ── Publishing ──
    
    def _stream_name(self, event_type: str) -> str:
        return f"{self.prefix}:stream:{event_type}"
    
    def _group_name(self, consumer: str) -> str:
        return f"{self.prefix}:group:{consumer}"
    
    async def publish(self, event: SwarmEvent) -> Optional[str]:
        """Publish event to stream. Returns message ID or None."""
        try:
            if self._connected and self.redis:
                msg_id = await self.redis.xadd(
                    self._stream_name(event.event_type),
                    event.to_dict(),
                    maxlen=10000,  # Keep last 10k messages per stream
                    approximate=True,
                )
                return msg_id
            else:
                # In-memory fallback
                await self._memory_queue.put(event)
                return "memory"
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            # Fallback to memory
            await self._memory_queue.put(event)
            return "memory"
    
    async def publish_simple(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str = "unknown",
        correlation_id: Optional[str] = None,
        priority: int = 0,
    ) -> Optional[str]:
        """Convenience method to publish without creating SwarmEvent."""
        event = SwarmEvent(
            event_type=event_type,
            source=source,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data,
            correlation_id=correlation_id,
            priority=priority,
        )
        return await self.publish(event)
    
    # ── Subscribing (Consumer Groups) ──
    
    async def subscribe(
        self,
        event_type: str,
        consumer_name: str,
        handler: Callable[[SwarmEvent], Any],
        auto_create_group: bool = True,
    ) -> asyncio.Task:
        """Subscribe to events with consumer group. Returns background task."""
        stream = self._stream_name(event_type)
        group = self._group_name(consumer_name)
        
        # Create consumer group if not exists
        if self._connected and auto_create_group:
            try:
                await self.redis.xgroup_create(stream, group, id="0", mkstream=True)
            except redis.ResponseError as e:
                if "already exists" not in str(e).lower():
                    raise
        
        # Start background consumer
        task = asyncio.create_task(
            self._consume_loop(event_type, consumer_name, handler),
            name=f"consumer:{consumer_name}:{event_type}"
        )
        logger.info(f"Consumer {consumer_name} subscribed to {event_type}")
        return task
    
    async def _consume_loop(
        self,
        event_type: str,
        consumer_name: str,
        handler: Callable[[SwarmEvent], Any],
    ):
        """Background loop consuming events."""
        stream = self._stream_name(event_type)
        group = self._group_name(consumer_name)
        
        if self._connected:
            # Redis Streams consumer
            while not self._shutdown:
                try:
                    messages = await self.redis.xreadgroup(
                        groupname=group,
                        consumername=consumer_name,
                        streams={stream: ">"},  # Only new messages
                        count=self.settings.event_batch_size,
                        block=self.settings.event_block_timeout_ms,
                    )
                    
                    for stream_name, msgs in messages:
                        for msg_id, fields in msgs:
                            try:
                                event = SwarmEvent.from_stream(msg_id, fields)
                                await handler(event)
                                # Acknowledge
                                await self.redis.xack(stream, group, msg_id)
                            except Exception as e:
                                logger.error(f"Handler error for {msg_id}: {e}")
                                # Don't ack - will be redelivered
                                
                except Exception as e:
                    if not self._shutdown:
                        logger.error(f"Consumer loop error: {e}")
                        await asyncio.sleep(1)
        else:
            # In-memory fallback
            while not self._shutdown:
                try:
                    event = await asyncio.wait_for(
                        self._memory_queue.get(),
                        timeout=1.0
                    )
                    if event.event_type == event_type:
                        await handler(event)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Memory handler error: {e}")
    
    # ── Direct Read (for testing/batch) ──
    
    async def read_pending(
        self,
        event_type: str,
        consumer_name: str,
        count: int = 10,
    ) -> List[tuple]:
        """Read pending (unacknowledged) messages."""
        if not self._connected:
            return []
        
        stream = self._stream_name(event_type)
        group = self._group_name(consumer_name)
        
        pending = await self.redis.xpending_range(
            stream, group,
            min="-", max="+", count=count
        )
        return pending
    
    # ── Stream Management ──
    
    async def get_stream_info(self, event_type: str) -> Dict[str, Any]:
        """Get stream info (length, groups, etc)."""
        if not self._connected:
            return {"length": 0, "groups": 0}
        
        stream = self._stream_name(event_type)
        info = await self.redis.xinfo_stream(stream)
        return {
            "length": info.get("length", 0),
            "groups": info.get("groups", 0),
            "last_generated_id": str(info.get("last-generated-id", "0-0")),
            "first_entry": bool(info.get("first-entry")),
            "last_entry": bool(info.get("last-entry")),
        }
    
    async def trim_stream(self, event_type: str, maxlen: int = 1000):
        """Trim stream to max length."""
        if self._connected:
            stream = self._stream_name(event_type)
            await self.redis.xtrim(stream, maxlen=maxlen, approximate=True)
            logger.info(f"Trimmed {event_type} stream to ~{maxlen}")
    
    # ── Health ──
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for monitoring."""
        try:
            if self._connected and self.redis:
                info = await self.redis.info("server")
                return {
                    "status": "connected",
                    "redis_version": info.get("redis_version", "unknown"),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                }
        except Exception as e:
            pass
        
        return {
            "status": "fallback",
            "redis_version": "none",
            "used_memory_human": "in-memory",
            "connected_clients": 0,
        }


# ───────────────────────────────────────────────
# Global Event Bus Singleton
# ───────────────────────────────────────────────

_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """Get or create event bus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.connect()
    return _event_bus


def get_event_bus_sync() -> Optional[EventBus]:
    """Synchronous access (returns None if not initialized)."""
    return _event_bus
