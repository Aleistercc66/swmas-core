"""
SWMAS Phase 1 — Core Engine
shared_memory.py — Shared Memory & Context Store

Central knowledge store for the swarm.
Features: key-value storage, TTL expiry, pattern query,
SQLite persistence, cross-agent memory access.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class MemoryEntry:
    """A single entry in shared memory."""
    key: str
    value: Any
    agent_id: str = "system"
    channel: str = "default"
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    tags: list[str] = field(default_factory=list)
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "key": self.key,
            "value": self.value,
            "agent_id": self.agent_id,
            "channel": self.channel,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "tags": self.tags,
        }


class SharedMemory:
    """
    Centralized shared memory for the SWMAS swarm.

    - In-memory LRU cache with TTL
    - SQLite persistence layer
    - Pattern-based query
    - Cross-agent memory sharing
    - JSON serialization for complex values
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        max_entries: int = 50_000,
    ) -> None:
        self._store: dict[str, MemoryEntry] = {}
        self._max_entries = max_entries
        self._lock = threading.RLock()
        self._db_path = db_path

        # SQLite persistence
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite schema."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                agent_id TEXT,
                channel TEXT,
                created_at REAL,
                expires_at REAL,
                tags TEXT,
                entry_id TEXT
            )
            """
        )
        self._conn.commit()

    def store(
        self,
        key: str,
        value: Any,
        agent_id: str = "system",
        channel: str = "default",
        ttl: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> MemoryEntry:
        """
        Store a value in shared memory.

        Args:
            key: Unique identifier.
            value: Any JSON-serializable value.
            agent_id: Owner of the entry.
            channel: Logical grouping.
            ttl: Seconds until expiry (None = never).
            tags: Optional list of tags for querying.
        """
        expires_at = time.time() + ttl if ttl else None
        entry = MemoryEntry(
            key=key,
            value=value,
            agent_id=agent_id,
            channel=channel,
            expires_at=expires_at,
            tags=tags or [],
        )

        with self._lock:
            # Evict oldest if at capacity
            if len(self._store) >= self._max_entries and key not in self._store:
                oldest = min(self._store, key=lambda k: self._store[k].created_at)
                del self._store[oldest]

            self._store[key] = entry
            self._persist_entry(entry)

        return entry

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value by key. Returns None if not found or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._store[key]
                self._delete_from_db(key)
                return None
            return entry.value

    def retrieve_entry(self, key: str) -> Optional[MemoryEntry]:
        """Retrieve full entry metadata."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._store[key]
                self._delete_from_db(key)
                return None
            return entry

    def query(
        self,
        pattern: Optional[str] = None,
        channel: Optional[str] = None,
        agent_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """
        Query memory with filters.

        - pattern: substring match on key
        - channel: exact channel match
        - agent_id: exact agent match
        - tags: entry must contain ALL specified tags
        """
        results: list[MemoryEntry] = []
        now = time.time()

        with self._lock:
            for entry in list(self._store.values()):
                if entry.is_expired():
                    del self._store[entry.key]
                    self._delete_from_db(entry.key)
                    continue
                if pattern and pattern not in entry.key:
                    continue
                if channel and entry.channel != channel:
                    continue
                if agent_id and entry.agent_id != agent_id:
                    continue
                if tags and not all(t in entry.tags for t in tags):
                    continue
                results.append(entry)

        results.sort(key=lambda e: e.created_at, reverse=True)
        return results[:limit]

    def share(self, from_agent: str, to_agent: str, key: str) -> bool:
        """
        Share a memory entry from one agent to another.
        Creates a copy with the new agent_id.
        """
        entry = self.retrieve_entry(key)
        if entry is None:
            return False
        new_key = f"{key}@{to_agent}"
        self.store(
            key=new_key,
            value=entry.value,
            agent_id=to_agent,
            channel=entry.channel,
            tags=entry.tags + ["shared", from_agent],
        )
        return True

    def delete(self, key: str) -> bool:
        """Delete an entry by key."""
        with self._lock:
            existed = key in self._store
            self._store.pop(key, None)
            self._delete_from_db(key)
            return existed

    def get_stats(self) -> dict[str, int]:
        """Return memory statistics."""
        with self._lock:
            return {
                "total_entries": len(self._store),
                "max_entries": self._max_entries,
            }

    def _persist_entry(self, entry: MemoryEntry) -> None:
        """Write entry to SQLite."""
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO memory
                (key, value, agent_id, channel, created_at, expires_at, tags, entry_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.key,
                    json.dumps(entry.value, default=str),
                    entry.agent_id,
                    entry.channel,
                    entry.created_at,
                    entry.expires_at,
                    json.dumps(entry.tags),
                    entry.entry_id,
                ),
            )
            self._conn.commit()
        except Exception as exc:
            print(f"[SharedMemory] Persistence error: {exc}")

    def _delete_from_db(self, key: str) -> None:
        """Delete entry from SQLite."""
        try:
            self._conn.execute("DELETE FROM memory WHERE key = ?", (key,))
            self._conn.commit()
        except Exception as exc:
            print(f"[SharedMemory] DB delete error: {exc}")

    def export_to_file(self, path: str) -> None:
        """Export all memory to a JSONL file."""
        with open(path, "w") as f:
            for entry in self.query(limit=1_000_000):
                f.write(json.dumps(entry.to_dict(), default=str) + "\n")

    def close(self) -> None:
        """Close SQLite connection."""
        self._conn.close()
