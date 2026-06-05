"""
Skill Registry - Continuous Learning and Skill Development
===========================================================
Manages agent skills, tracks usage, and evolves capabilities.
Skills are stored in JSON and can be dynamically loaded/unloaded.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_DIR = Path("/root/.openclaw/workspace/orchestrator/skills")
SKILLS_REGISTRY_FILE = SKILLS_DIR / "registry.json"

# Default skills that come with the orchestrator
DEFAULT_SKILLS = {
    "dexscreener_analysis": {
        "name": "DexScreener Analysis",
        "description": "Analyze tokens and pairs from DexScreener data",
        "level": 1,
        "uses": 0,
        "created_at": datetime.now().isoformat(),
        "capabilities": ["token_scanning", "pair_analysis", "momentum_detection"],
    },
    "signal_generation": {
        "name": "Signal Generation",
        "description": "Generate trading signals with entry/exit points",
        "level": 1,
        "uses": 0,
        "created_at": datetime.now().isoformat(),
        "capabilities": ["entry_points", "stop_loss", "take_profit", "confidence_scoring"],
    },
    "swarm_orchestration": {
        "name": "Swarm Orchestration",
        "description": "Manage and coordinate multiple agents",
        "level": 1,
        "uses": 0,
        "created_at": datetime.now().isoformat(),
        "capabilities": ["agent_spawning", "task_routing", "health_monitoring"],
    },
    "context_management": {
        "name": "Context Management",
        "description": "Maintain and utilize conversation context",
        "level": 1,
        "uses": 0,
        "created_at": datetime.now().isoformat(),
        "capabilities": ["memory", "pattern_recognition", "personalization"],
    },
    "risk_assessment": {
        "name": "Risk Assessment",
        "description": "Evaluate trading and operational risks",
        "level": 1,
        "uses": 0,
        "created_at": datetime.now().isoformat(),
        "capabilities": ["liquidity_check", "volatility_analysis", "position_sizing"],
    },
    "autonomous_operation": {
        "name": "Autonomous Operation",
        "description": "Self-directed operation without user input",
        "level": 1,
        "uses": 0,
        "created_at": datetime.now().isoformat(),
        "capabilities": ["self_triggering", "adaptive_behavior", "goal_pursuit"],
    },
}


class SkillRegistry:
    """
    Manages the skill system for continuous learning.
    
    Features:
    - Track skill levels and usage
    - Learn new skills from interactions
    - Evolve existing skills
    - Load skill modules dynamically
    """

    def __init__(self):
        self.skills: Dict[str, Dict] = {}
        self.learning_history: List[Dict] = []

    async def initialize(self):
        """Initialize skill registry."""
        logger.info("🎯 Initializing Skill Registry...")
        
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load or create registry
        if SKILLS_REGISTRY_FILE.exists():
            with open(SKILLS_REGISTRY_FILE) as f:
                self.skills = json.load(f)
            logger.info(f"🎯 Loaded {len(self.skills)} skills")
        else:
            self.skills = DEFAULT_SKILLS.copy()
            await self._save_registry()
            logger.info(f"🎯 Created default skills: {len(self.skills)}")

    async def list_skills(self) -> List[Dict]:
        """List all available skills."""
        return [
            {
                "name": info["name"],
                "description": info["description"],
                "level": info["level"],
                "uses": info["uses"],
                "capabilities": info.get("capabilities", []),
            }
            for info in self.skills.values()
        ]

    async def get_skill(self, skill_name: str) -> Optional[Dict]:
        """Get a specific skill."""
        return self.skills.get(skill_name)

    async def learn_skill(self, skill_name: str) -> str:
        """
        Learn or improve a skill.
        
        Args:
            skill_name: Name of skill to learn
            
        Returns:
            Learning result description
        """
        if skill_name == "auto":
            return await self._autonomous_learning()

        if skill_name not in self.skills:
            # Create new skill
            self.skills[skill_name] = {
                "name": skill_name,
                "description": f"Auto-generated skill: {skill_name}",
                "level": 1,
                "uses": 0,
                "created_at": datetime.now().isoformat(),
                "capabilities": [],
            }
            await self._save_registry()
            return f"✅ New skill created: **{skill_name}** (Level 1)"

        # Improve existing skill
        skill = self.skills[skill_name]
        old_level = skill["level"]
        skill["level"] = min(old_level + 1, 10)  # Cap at level 10
        skill["uses"] = skill.get("uses", 0) + 1
        skill["last_improved"] = datetime.now().isoformat()
        
        await self._save_registry()
        
        return f"""
🎯 **Skill Evolution!** 🎯

**{skill['name']}**
Level: {old_level} → **{skill['level']}**
Uses: {skill['uses']}

Capabilities:
{chr(10).join('• ' + c for c in skill.get('capabilities', []))}

Keep using it to level up further!
        """

    async def use_skill(self, skill_name: str) -> bool:
        """
        Record skill usage.
        
        Returns:
            True if skill exists and was used
        """
        if skill_name not in self.skills:
            return False
        
        self.skills[skill_name]["uses"] = self.skills[skill_name].get("uses", 0) + 1
        
        # Auto-level up based on usage
        uses = self.skills[skill_name]["uses"]
        level = self.skills[skill_name]["level"]
        
        if uses >= level * 10 and level < 10:
            self.skills[skill_name]["level"] = level + 1
            logger.info(f"🎯 Skill {skill_name} leveled up to {level + 1}!")
        
        await self._save_registry()
        return True

    async def discover_skill(self, trigger: str, context: str) -> Optional[str]:
        """
        Discover if a new skill should be learned based on interaction.
        
        Returns:
            Skill name if discovered, None otherwise
        """
        # Pattern matching for skill discovery
        triggers = {
            "chart": "chart_analysis",
            "graph": "chart_analysis",
            "social": "sentiment_analysis",
            "sentiment": "sentiment_analysis",
            "news": "news_analysis",
            "whale": "whale_tracking",
            "nft": "nft_analysis",
            "defi": "defi_analysis",
            "arbitrage": "arbitrage_detection",
        }
        
        trigger_lower = trigger.lower()
        for keyword, skill_name in triggers.items():
            if keyword in trigger_lower:
                if skill_name not in self.skills:
                    await self.learn_skill(skill_name)
                    return skill_name
        
        return None

    async def _autonomous_learning(self) -> str:
        """Perform autonomous skill development."""
        # Analyze usage patterns
        total_uses = sum(s.get("uses", 0) for s in self.skills.values())
        avg_level = sum(s["level"] for s in self.skills.values()) / len(self.skills)
        
        # Identify weak skills
        weak_skills = [
            name for name, info in self.skills.items()
            if info["level"] < 3
        ]
        
        # Improve weak skills
        improved = []
        for skill_name in weak_skills[:3]:  # Improve up to 3
            result = await self.learn_skill(skill_name)
            improved.append(skill_name)
        
        return f"""
🧠 **Autonomous Learning Complete!** 🧠

Analyzed {len(self.skills)} skills
Total uses: {total_uses}
Average level: {avg_level:.1f}

**Improved Skills:**
{chr(10).join(f'• {s} (+1 level)' for s in improved)}

**Recommendations:**
• Use `/scan` to practice dexscreener_analysis
• Use `/signal` to practice signal_generation
• Use `/spawn` to practice swarm_orchestration

Keep interacting to evolve further!
        """

    async def get_skill_stats(self) -> str:
        """Get skill statistics."""
        total = len(self.skills)
        total_uses = sum(s.get("uses", 0) for s in self.skills.values())
        avg_level = sum(s["level"] for s in self.skills.values()) / total if total > 0 else 0
        max_level = max((s["level"] for s in self.skills.values()), default=0)
        
        return f"""
🎯 **SKILL STATISTICS** 🎯

Total Skills: {total}
Total Uses: {total_uses}
Average Level: {avg_level:.1f}
Max Level: {max_level}

Top Skills:
{chr(10).join(f"• {s['name']} (Lv.{s['level']}, {s['uses']} uses)" for s in sorted(self.skills.values(), key=lambda x: x['uses'], reverse=True)[:5])}
        """

    async def _save_registry(self):
        """Save skill registry."""
        with open(SKILLS_REGISTRY_FILE, 'w') as f:
            json.dump(self.skills, f, indent=2)
