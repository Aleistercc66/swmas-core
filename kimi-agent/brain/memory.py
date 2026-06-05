"""Per-user conversation memory using SQLite."""
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship

from config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


class UserProfile(Base):
    """User profile and preferences."""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    language_code = Column(String, nullable=True)
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("ConversationMessage", back_populates="user", lazy="selectin")


class ConversationMessage(Base):
    """Individual conversation message."""
    __tablename__ = "conversation_messages"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    message_type = Column(String, default="text")  # text, photo, url, news, research
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("UserProfile", back_populates="messages")


class MemoryManager:
    """Manages per-user conversation memory."""
    
    def __init__(self):
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False
        )
        Base.metadata.create_all(self.engine)
    
    def get_or_create_user(self, telegram_id: str, **kwargs) -> dict:
        """Get or create user profile."""
        from sqlalchemy.orm import Session
        
        with Session(self.engine) as session:
            user = session.query(UserProfile).filter_by(telegram_id=str(telegram_id)).first()
            if not user:
                user = UserProfile(
                    telegram_id=str(telegram_id),
                    username=kwargs.get("username"),
                    first_name=kwargs.get("first_name"),
                    language_code=kwargs.get("language_code", "en")
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Created new user: {telegram_id}")
            
            return {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "language_code": user.language_code,
                "preferences": user.preferences or {}
            }
    
    def add_message(
        self,
        telegram_id: str,
        role: str,
        content: str,
        message_type: str = "text",
        metadata: dict | None = None
    ) -> None:
        """Add a message to conversation history."""
        from sqlalchemy.orm import Session
        
        with Session(self.engine) as session:
            user = session.query(UserProfile).filter_by(telegram_id=str(telegram_id)).first()
            if not user:
                user = UserProfile(telegram_id=str(telegram_id))
                session.add(user)
                session.commit()
                session.refresh(user)
            
            msg = ConversationMessage(
                user_id=user.id,
                role=role,
                content=content,
                message_type=message_type,
                metadata=metadata or {}
            )
            session.add(msg)
            session.commit()
    
    def get_recent_messages(
        self,
        telegram_id: str,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get recent messages for a user."""
        from sqlalchemy.orm import Session
        
        limit = limit or settings.MEMORY_MESSAGE_LIMIT
        
        with Session(self.engine) as session:
            user = session.query(UserProfile).filter_by(telegram_id=str(telegram_id)).first()
            if not user:
                return []
            
            messages = session.query(ConversationMessage).filter_by(
                user_id=user.id
            ).order_by(ConversationMessage.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "type": m.message_type,
                    "metadata": m.metadata,
                    "timestamp": m.created_at.isoformat() if m.created_at else None
                }
                for m in reversed(messages)
            ]
    
    def clear_memory(self, telegram_id: str) -> int:
        """Clear conversation memory for a user. Returns count of deleted messages."""
        from sqlalchemy.orm import Session
        
        with Session(self.engine) as session:
            user = session.query(UserProfile).filter_by(telegram_id=str(telegram_id)).first()
            if not user:
                return 0
            
            count = session.query(ConversationMessage).filter_by(user_id=user.id).delete()
            session.commit()
            logger.info(f"Cleared {count} messages for user {telegram_id}")
            return count
    
    def update_preferences(self, telegram_id: str, preferences: dict) -> None:
        """Update user preferences."""
        from sqlalchemy.orm import Session
        
        with Session(self.engine) as session:
            user = session.query(UserProfile).filter_by(telegram_id=str(telegram_id)).first()
            if user:
                current_prefs = user.preferences or {}
                current_prefs.update(preferences)
                user.preferences = current_prefs
                session.commit()
    
    def get_user_stats(self, telegram_id: str) -> dict:
        """Get user statistics."""
        from sqlalchemy.orm import Session
        
        with Session(self.engine) as session:
            user = session.query(UserProfile).filter_by(telegram_id=str(telegram_id)).first()
            if not user:
                return {"messages": 0, "first_seen": None}
            
            msg_count = session.query(ConversationMessage).filter_by(user_id=user.id).count()
            return {
                "messages": msg_count,
                "first_seen": user.created_at.isoformat() if user.created_at else None,
                "language": user.language_code
            }


memory = MemoryManager()
