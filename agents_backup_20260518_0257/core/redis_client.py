#!/usr/bin/env python3
"""
🔴 REDIS CLIENT — Async Redis for cache, pub/sub, rate limiting
Graceful degradation: if Redis is unavailable, caches become no-ops.
"""
import asyncio
import json
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone

import redis.asyncio as aioredis
from redis.asyncio import Redis

from core.config import settings
from core.logging_config import get_logger

logger = get_logger("redis")

# Singleton
_redis_client: Optional[Redis] = None
_redis_available: bool = False

async def get_redis() -> Optional[Redis]:
    """Singleton async Redis client. Returns None if unavailable."""
    global _redis_client, _redis_available
    
    if _redis_client is None and not _redis_available:
        try:
            _redis_client = aioredis.from_url(
                settings.redis.url,
                decode_responses=settings.redis.decode_responses,
                socket_connect_timeout=settings.redis.socket_connect_timeout,
                socket_timeout=settings.redis.socket_timeout,
            )
            await _redis_client.ping()
            _redis_available = True
            logger.info("Redis connected")
        except Exception as e:
            logger.warning(f"Redis unavailable (caching disabled): {e}")
            _redis_available = False
            _redis_client = None
    
    return _redis_client

async def close_redis():
    """Graceful close."""
    global _redis_client, _redis_available
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        _redis_available = False
        logger.info("Redis disconnected")

# ───────────────────────────────────────────────
# Cache Helpers — graceful degradation
# ───────────────────────────────────────────────

async def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    """JSON-serialized cache entry. No-op if Redis unavailable."""
    r = await get_redis()
    if r is None:
        return
    try:
        payload = json.dumps(value, default=str)
        await r.setex(key, ttl_seconds, payload)
    except Exception as e:
        logger.warning(f"Cache set failed: {e}")

async def cache_get(key: str) -> Optional[Any]:
    """Get and deserialize cache entry. Returns None if Redis unavailable."""
    r = await get_redis()
    if r is None:
        return None
    try:
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Cache get failed: {e}")
        return None

async def cache_delete(key: str):
    r = await get_redis()
    if r is None:
        return
    try:
        await r.delete(key)
    except Exception:
        pass

async def cache_exists(key: str) -> bool:
    r = await get_redis()
    if r is None:
        return False
    try:
        return await r.exists(key) > 0
    except Exception:
        return False

# ───────────────────────────────────────────────
# Pub/Sub — graceful degradation
# ───────────────────────────────────────────────

async def publish_event(channel: str, event: Dict[str, Any]):
    """Publish JSON event to Redis channel. No-op if unavailable."""
    r = await get_redis()
    if r is None:
        return
    try:
        payload = json.dumps(event, default=str)
        await r.publish(channel, payload)
        logger.debug(f"Published to {channel}: {event.get('event_type', 'unknown')}")
    except Exception as e:
        logger.warning(f"Event publish failed: {e}")

async def subscribe_channel(channel: str):
    """Get async generator for channel messages. Raises if unavailable."""
    r = await get_redis()
    if r is None:
        raise RuntimeError("Redis unavailable — cannot subscribe to channels")
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    return pubsub

# ───────────────────────────────────────────────
# Rate Limiting (Token Bucket) — graceful degradation
# ───────────────────────────────────────────────

async def rate_limit_check(key: str, max_calls: int, window_seconds: int) -> bool:
    """
    Token bucket rate limiter. Returns True if call allowed.
    If Redis unavailable, allows all calls (fail open).
    """
    r = await get_redis()
    if r is None:
        return True  # Fail open when Redis down
    
    now = datetime.now(timezone.utc).timestamp()
    bucket_key = f"ratelimit:{key}"
    
    lua_script = """
    local key = KEYS[1]
    local window = tonumber(ARGV[2])
    local max_calls = tonumber(ARGV[3])
    
    local current = redis.call('GET', key)
    if current == false then
        redis.call('SET', key, 1, 'EX', window)
        return 1
    end
    
    current = tonumber(current)
    if current >= max_calls then
        return 0
    end
    
    redis.call('INCR', key)
    return 1
    """
    
    try:
        result = await r.eval(
            lua_script, 1, bucket_key,
            str(now), str(window_seconds), str(max_calls)
        )
        allowed = result == 1
        if not allowed:
            logger.warning(f"Rate limited: {key}")
        return allowed
    except Exception as e:
        logger.error(f"Rate limit error: {e}")
        return True  # Fail open

# ───────────────────────────────────────────────
# Distributed Lock — graceful degradation
# ───────────────────────────────────────────────

async def acquire_lock(lock_name: str, timeout_seconds: int = 10) -> bool:
    """Distributed lock via Redis SET NX. Returns False if Redis unavailable."""
    r = await get_redis()
    if r is None:
        logger.warning(f"Redis unavailable — lock {lock_name} not acquired")
        return False
    
    lock_key = f"lock:{lock_name}"
    try:
        acquired = await r.set(lock_key, "1", nx=True, ex=timeout_seconds)
        if acquired:
            logger.debug(f"Lock acquired: {lock_name}")
        return acquired is not None
    except Exception as e:
        logger.error(f"Lock acquire failed: {e}")
        return False

async def release_lock(lock_name: str):
    r = await get_redis()
    if r is None:
        return
    
    lock_key = f"lock:{lock_name}"
    try:
        await r.delete(lock_key)
        logger.debug(f"Lock released: {lock_name}")
    except Exception:
        pass

# ───────────────────────────────────────────────
# Portfolio Cache (hot path)
# ───────────────────────────────────────────────

async def get_cached_portfolio() -> Optional[Dict]:
    return await cache_get("portfolio:current")

async def set_cached_portfolio(data: Dict, ttl: int = 5):
    """Cache portfolio for 5 seconds (very hot)."""
    await cache_set("portfolio:current", data, ttl)

async def invalidate_portfolio_cache():
    await cache_delete("portfolio:current")
