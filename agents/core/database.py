#!/usr/bin/env python3
"""
🗄️ DATABASE LAYER — SQLAlchemy 2.0 + SQLModel
Async engine with connection pooling. SQLite default, PostgreSQL ready.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import os

from core.config import settings
from core.logging_config import get_logger

logger = get_logger("database")

# ───────────────────────────────────────────────
# Engine Factory
# ───────────────────────────────────────────────

_engine = None
_async_session_maker = None

def get_engine():
    """Singleton async engine."""
    global _engine
    if _engine is None:
        db = settings.db
        
        # Ensure data directory exists for SQLite
        if db.is_sqlite:
            os.makedirs(os.path.dirname(db.url.replace("sqlite+aiosqlite:///", "")), exist_ok=True)
        
        connect_args = {}
        if db.is_sqlite:
            connect_args["check_same_thread"] = False
        
        kwargs = {
            "echo": db.echo,
            "pool_pre_ping": db.pool_pre_ping,
        }
        
        if db.is_postgres:
            kwargs["pool_size"] = db.pool_size
            kwargs["max_overflow"] = db.max_overflow
        
        _engine = create_async_engine(
            db.url,
            connect_args=connect_args,
            **kwargs,
        )
        logger.info(f"Database engine created: {db.url}")
    return _engine

def get_session_maker():
    """Async session factory with autocommit=False (manual tx)."""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_maker

async def get_session() -> AsyncSession:
    """Dependency injection helper."""
    maker = get_session_maker()
    async with maker() as session:
        yield session

# ───────────────────────────────────────────────
# Schema Management
# ───────────────────────────────────────────────

async def init_db():
    """Create all tables. Call once at startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database tables created")

async def drop_db():
    """Drop all tables — DANGEROUS!"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    logger.warning("Database tables dropped")

# ───────────────────────────────────────────────
# Transaction Helpers
# ───────────────────────────────────────────────

class AtomicTransaction:
    """
    Context manager for atomic DB transactions.
    Usage:
        async with AtomicTransaction() as session:
            session.add(obj)
            await session.commit()
    """
    def __init__(self):
        self.session: AsyncSession | None = None
        self.committed = False
    
    async def __aenter__(self) -> AsyncSession:
        maker = get_session_maker()
        self.session = maker()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session is None:
            return
        try:
            if exc_type is None:
                if not self.committed:
                    await self.session.commit()
                self.committed = True
            else:
                await self.session.rollback()
                logger.error(f"Transaction rolled back: {exc_val}")
        finally:
            await self.session.close()
    
    async def commit(self):
        """Explicit commit."""
        if self.session:
            await self.session.commit()
            self.committed = True
    
    async def rollback(self):
        """Explicit rollback."""
        if self.session:
            await self.session.rollback()
            self.committed = False

# ───────────────────────────────────────────────
# Optimistic Locking
# ───────────────────────────────────────────────

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

async def update_with_optimistic_lock(
    session: AsyncSession,
    model_class,
    obj_id: int,
    expected_version: int,
    **updates
) -> bool:
    """
    Atomic update with version check.
    Returns True if updated, False if version mismatch (another process changed it).
    """
    from sqlalchemy import select
    
    # Fetch current
    result = await session.execute(
        select(model_class).where(model_class.id == obj_id)
    )
    obj = result.scalar_one_or_none()
    
    if obj is None:
        logger.warning(f"Object {model_class.__name__}#{obj_id} not found")
        return False
    
    if obj.version != expected_version:
        logger.warning(
            f"Version conflict: {model_class.__name__}#{obj_id} "
            f"expected v{expected_version}, found v{obj.version}"
        )
        return False
    
    # Apply updates
    for key, value in updates.items():
        setattr(obj, key, value)
    
    obj.version += 1
    obj.updated_at = datetime.now(timezone.utc)
    
    await session.commit()
    logger.info(f"Updated {model_class.__name__}#{obj_id} to v{obj.version}")
    return True

# Import needed at bottom to avoid circular
from datetime import datetime, timezone
