"""
Context Engine - Conversation and Session Management
====================================================
Maintains context across conversations, tracks user sessions,
and enables personalized responses based on history.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CONTEXT_DIR = Path("/root/.openclaw/workspace/orchestrator/logs/context")


class ContextEngine:
    """
    Manages conversation context and user sessions.
    
    Features:
    - Per-user message history
    - Context window management
    - Session state tracking
    - Pattern recognition
    """

    def __init__(self):
        self.sessions: Dict[int, Dict] = {}
        self.global_context: Dict = {
            "total_messages": 0,
            "unique_users": set(),
            "commands_used": {},
            "topics_discussed": [],
        }

    async def initialize(self):
        """Initialize context engine."""
        logger.info("🌐 Initializing Context Engine...")
        
        CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing sessions
        for session_file in CONTEXT_DIR.glob("*.json"):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                    user_id = int(session_file.stem)
                    self.sessions[user_id] = data
            except:
                pass
        
        logger.info(f"🌐 Loaded {len(self.sessions)} sessions")

    async def add_message(self, user_id: int, text: str, role: str = "user"):
        """
        Add a message to user's context.
        
        Args:
            user_id: Telegram user ID
            text: Message content
            role: "user" or "brain"
        """
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "messages": [],
                "started_at": datetime.now().isoformat(),
                "preferences": {},
                "patterns": [],
                "topics": [],
            }
        
        message = {
            "role": role,
            "content": text,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.sessions[user_id]["messages"].append(message)
        
        # Keep only last 100 messages per user
        if len(self.sessions[user_id]["messages"]) > 100:
            self.sessions[user_id]["messages"] = self.sessions[user_id]["messages"][-100:]
        
        # Update global stats
        self.global_context["total_messages"] += 1
        self.global_context["unique_users"].add(user_id)
        
        # Extract topics (simple keyword matching)
        await self._extract_topics(user_id, text)
        
        # Save session
        await self._save_session(user_id)

    async def get_context(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get recent context for a user.
        
        Args:
            user_id: Telegram user ID
            limit: Number of recent messages to return
            
        Returns:
            List of recent messages
        """
        if user_id not in self.sessions:
            return []
        
        messages = self.sessions[user_id]["messages"]
        return messages[-limit:]

    async def get_user_profile(self, user_id: int) -> Dict:
        """
        Get user profile with patterns and preferences.
        
        Returns:
            User profile dict
        """
        if user_id not in self.sessions:
            return {"status": "new_user"}
        
        session = self.sessions[user_id]
        messages = session["messages"]
        
        # Calculate stats
        user_msgs = [m for m in messages if m["role"] == "user"]
        brain_msgs = [m for m in messages if m["role"] == "brain"]
        
        # Detect patterns (simple frequency analysis)
        topics = session.get("topics", [])
        topic_counts = {}
        for t in topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1
        
        return {
            "user_id": user_id,
            "session_start": session["started_at"],
            "total_messages": len(messages),
            "user_messages": len(user_msgs),
            "brain_responses": len(brain_msgs),
            "top_topics": sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "preferences": session.get("preferences", {}),
        }

    async def set_preference(self, user_id: int, key: str, value: Any):
        """Set a user preference."""
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "messages": [],
                "started_at": datetime.now().isoformat(),
                "preferences": {},
                "patterns": [],
                "topics": [],
            }
        
        self.sessions[user_id]["preferences"][key] = value
        await self._save_session(user_id)

    async def get_preference(self, user_id: int, key: str) -> Optional[Any]:
        """Get a user preference."""
        if user_id not in self.sessions:
            return None
        
        return self.sessions[user_id]["preferences"].get(key)

    async def get_size(self) -> int:
        """Get total context size."""
        return sum(len(s["messages"]) for s in self.sessions.values())

    async def clear_context(self, user_id: int):
        """Clear a user's context."""
        if user_id in self.sessions:
            self.sessions[user_id]["messages"] = []
            await self._save_session(user_id)

    async def _extract_topics(self, user_id: int, text: str):
        """Extract topics from text."""
        # Simple keyword-based topic extraction
        topic_keywords = {
            "crypto": ["crypto", "bitcoin", "btc", "ethereum", "eth", "altcoin", "token"],
            "trading": ["trade", "trading", "buy", "sell", "signal", "entry", "exit"],
            "solana": ["solana", "sol", "jupiter", "raydium", "serum"],
            "market": ["market", "scan", "dexscreener", "volume", "liquidity"],
            "system": ["agent", "swarm", "system", "orchestrator", "bot"],
            "learning": ["learn", "skill", "evolve", "improve", "develop"],
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                if topic not in self.sessions[user_id]["topics"]:
                    self.sessions[user_id]["topics"].append(topic)

    async def _save_session(self, user_id: int):
        """Save a user session to file."""
        session_file = CONTEXT_DIR / f"{user_id}.json"
        with open(session_file, 'w') as f:
            json.dump(self.sessions[user_id], f, indent=2)

    async def get_global_stats(self) -> Dict:
        """Get global context statistics."""
        return {
            "total_messages": self.global_context["total_messages"],
            "unique_users": len(self.global_context["unique_users"]),
            "active_sessions": len(self.sessions),
            "most_used_commands": dict(
                sorted(
                    self.global_context["commands_used"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
            ),
        }
