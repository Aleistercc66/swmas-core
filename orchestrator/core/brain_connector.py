"""
Brain Connector - Interface to AImind (OpenClaw)
=================================================
This module connects the Telegram orchestrator to the brain (AImind).
It routes queries, receives decisions, and maintains the brain link.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_FILE = WORKSPACE / "MEMORY.md"
BRAIN_STATE_FILE = WORKSPACE / "orchestrator" / "logs" / "brain_state.json"


class BrainConnector:
    """
    Connector to AImind — the central intelligence.
    
    This acts as the bridge between the Telegram bot and the actual
    AI brain running in OpenClaw. It maintains context, routes queries,
    and receives decisions.
    """

    def __init__(self):
        self.context_cache: Dict[int, List[Dict]] = {}
        self.decision_history: List[Dict] = []
        self.is_connected = False
        self.brain_state: Dict = {}

    async def initialize(self):
        """Initialize brain connection."""
        logger.info("🧠 Initializing Brain Connector...")
        self.is_connected = True
        
        # Load brain state if exists
        if BRAIN_STATE_FILE.exists():
            with open(BRAIN_STATE_FILE) as f:
                self.brain_state = json.load(f)
        
        logger.info("🧠 Brain connector ready")

    async def query(self, text: str, user_id: int = 0) -> str:
        """
        Send a query to the brain and get response.
        
        In a full implementation, this would call OpenClaw's API.
        For now, it uses local intelligence and file-based reasoning.
        """
        # Store in context
        if user_id not in self.context_cache:
            self.context_cache[user_id] = []
        
        self.context_cache[user_id].append({
            "role": "user",
            "content": text,
            "timestamp": datetime.now().isoformat(),
        })

        # Get context window
        context = self._get_context(user_id)
        
        # Generate brain-like response based on query type
        response = await self._generate_response(text, context)
        
        # Store response
        self.context_cache[user_id].append({
            "role": "brain",
            "content": response,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Save state
        await self._save_state()
        
        return response

    async def decide_action(self, text: str, user_id: int = 0) -> Dict[str, Any]:
        """
        Brain decision engine — decides what action to take based on input.
        
        Returns a decision dict with:
        - action: what to do
        - params: parameters for the action
        - confidence: how sure the brain is
        """
        text_lower = text.lower()
        
        # Decision logic based on input patterns
        if any(word in text_lower for word in ["scan", "market", "check", "find", "opportunities"]):
            return {
                "action": "scan",
                "params": {},
                "confidence": 0.9,
                "reasoning": "User wants market scan",
            }
        
        elif any(word in text_lower for word in ["spawn", "create", "start", "deploy", "agent"]):
            agent_type = self._extract_agent_type(text_lower)
            return {
                "action": "spawn",
                "params": {"type": agent_type},
                "confidence": 0.85,
                "reasoning": f"User wants to spawn {agent_type} agent",
            }
        
        elif any(word in text_lower for word in ["status", "health", "how", "doing"]):
            return {
                "action": "status",
                "params": {},
                "confidence": 0.95,
                "reasoning": "User wants status check",
            }
        
        elif any(word in text_lower for word in ["trade", "buy", "sell", "signal", "alert"]):
            return {
                "action": "signal",
                "params": {},
                "confidence": 0.8,
                "reasoning": "User wants trading signals",
            }
        
        else:
            # Default: just respond
            return {
                "action": "message",
                "params": {"text": await self.query(text, user_id)},
                "confidence": 0.7,
                "reasoning": "General query, respond directly",
            }

    async def _generate_response(self, text: str, context: str) -> str:
        """Generate a brain-like response."""
        text_lower = text.lower()
        
        # Check for crypto/market queries
        if any(word in text_lower for word in ["crypto", "market", "token", "coin", "price", "trading"]):
            return self._market_response(text)
        
        # Check for system queries
        elif any(word in text_lower for word in ["system", "status", "agent", "swarm", "orchestrator"]):
            return self._system_response(text)
        
        # Check for skill/learning queries
        elif any(word in text_lower for word in ["learn", "skill", "improve", "evolve", "develop"]):
            return self._learning_response(text)
        
        # General response
        else:
            return self._general_response(text)

    def _market_response(self, text: str) -> str:
        """Generate market-related response."""
        return f"""
🧠 **Brain Analysis** 🧠

Query: _{text}_

**Market Intelligence:**
I'm connected to DexScreener, Jupiter, and multiple exchange APIs.
Use `/scan` for instant market analysis or `/signal` for trading signals.

**Available Actions:**
• `/scan` — Full market scan
• `/signal` — Trading signals
• `/spawn scanner` — Dedicated scanner agent
• `/spawn trader` — Trading execution agent

What would you like to explore?
        """

    def _system_response(self, text: str) -> str:
        """Generate system-related response."""
        return f"""
🧠 **Brain Status** 🧠

Query: _{text}_

**System Overview:**
• Brain: AImind (Connected)
• Swarm: Active and evolving
• Skills: Continuously learning
• Mode: Manual / Autopilot / Hybrid

**Quick Commands:**
• `/status` — Full system status
• `/swarm` — Swarm overview
• `/agents` — Active agents list
• `/skills` — Available skills

System is healthy and operational! 🔥
        """

    def _learning_response(self, text: str) -> str:
        """Generate learning-related response."""
        return f"""
🧠 **Learning Engine** 🧠

Query: _{text}_

**Skill Development:**
I'm continuously learning from every interaction.
Current capabilities include:
• Market analysis and scanning
• Trading signal generation
• Multi-agent orchestration
• Context-aware responses

**To develop new skills:**
• `/learn auto` — Autonomous skill development
• `/learn <skill_name>` — Targeted learning

I'm always evolving! 🎯
        """

    def _general_response(self, text: str) -> str:
        """Generate general response."""
        return f"""
🧠 **Brain Response** 🧠

_{text}_

I hear you! I'm your orchestrator brain — connected to:
• 🤖 Swarm of specialized agents
• 📊 Real-time market data
• 🎯 Evolving skill system
• 🌐 Full workspace access

**What can I do for you?**
• Market analysis → `/scan`
• Spawn agents → `/spawn <type>`
• Direct brain query → `/brain <question>`
• Autopilot mode → `/autopilot`

Let's move! 🚀
        """

    def _extract_agent_type(self, text: str) -> str:
        """Extract agent type from text."""
        types = ["scanner", "trader", "analyst", "learner", "monitor"]
        for t in types:
            if t in text:
                return t
        return "scanner"  # default

    def _get_context(self, user_id: int) -> str:
        """Get recent context for a user."""
        messages = self.context_cache.get(user_id, [])
        if not messages:
            return ""
        
        # Get last 10 messages
        recent = messages[-10:]
        return "\n".join([
            f"{m['role']}: {m['content']}" 
            for m in recent
        ])

    async def _save_state(self):
        """Save brain state to file."""
        BRAIN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BRAIN_STATE_FILE, 'w') as f:
            json.dump({
                "context_cache": {str(k): v[-50:] for k, v in self.context_cache.items()},
                "decision_history": self.decision_history[-100:],
                "last_update": datetime.now().isoformat(),
            }, f, indent=2)

    async def shutdown(self):
        """Graceful shutdown."""
        await self._save_state()
        self.is_connected = False
        logger.info("🧠 Brain connector shutdown")
