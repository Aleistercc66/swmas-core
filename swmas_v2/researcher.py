"""
SWMAS Phase 2 — Agent Templates
researcher.py — Research Agent

Gathers information, performs simulated web searches,
stores findings in shared memory, produces research reports.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any

from agent_factory import BaseAgent, AgentConfig, AgentType, register_agent_template
from communication_bus import CommunicationBus, Message, Priority
from shared_memory import SharedMemory


class ResearcherAgent(BaseAgent):
    """
    Specialized agent for information gathering and research.

    Capabilities:
    - Simulated multi-source information collection
    - Keyword-based topic exploration
    - Fact cross-referencing and validation
    - Research report generation
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        bus: CommunicationBus,
        memory: SharedMemory,
    ) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._current_topic: str = ""
        self._sources_found: list[dict[str, Any]] = []
        self._findings: list[dict[str, Any]] = []
        self._research_depth: int = 3  # How many "sources" to simulate

    async def _run_loop(self) -> None:
        """Main research loop — continuous mode: auto-research periodically."""
        continuous = self.config.context.get("continuous", False)
        interval = self.config.context.get("interval", 300)
        topic = self.config.context.get("topic", "general research")
        last_auto_research = 0

        while not self._stop_event.is_set():
            try:
                # Heartbeat: report status if researching
                if self._current_topic:
                    await self._heartbeat()

                # Auto-research in continuous mode
                if continuous and (time.time() - last_auto_research) > interval:
                    await self._auto_research(topic)
                    last_auto_research = time.time()

                await asyncio.wait_for(self._stop_event.wait(), timeout=8.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _auto_research(self, topic: str) -> None:
        """Perform automated periodic research."""
        obj_id = f"auto-research-{int(time.time())}"
        await self._perform_research(
            obj_id,
            f"Auto-research: {topic} at {time.strftime('%H:%M:%S')}",
            {"auto": True, "continuous": True},
        )

    async def _on_message(self, msg: Message) -> None:
        """Handle incoming research commands."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        command = payload.get("command", "")

        if command == "execute_task":
            description = payload.get("description", "")
            analysis = payload.get("analysis", {})
            obj_id = payload.get("objective_id", "")
            await self._perform_research(obj_id, description, analysis)

        elif command == "deep_dive":
            topic = payload.get("topic", "")
            depth = payload.get("depth", 5)
            await self._deep_dive_research(topic, depth)

        else:
            # Default acknowledge
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "original_msg_id": msg.msg_id},
                channel=msg.channel,
                priority=Priority.LOW,
            )

    async def _perform_research(
        self,
        objective_id: str,
        description: str,
        analysis: dict[str, Any],
    ) -> None:
        """Execute a research task."""
        self._current_topic = description
        self._sources_found = []
        self._findings = []

        # Phase 2: Simulated research — future: real web search, API calls
        keywords = self._extract_keywords(description)

        for i in range(self._research_depth):
            source = self._simulate_source(keywords, i)
            self._sources_found.append(source)
            finding = self._extract_finding(source, keywords)
            self._findings.append(finding)
            await asyncio.sleep(0.1)  # Simulate work

        # Store findings in shared memory
        report = self._compile_report(objective_id, description)
        self.memory.store(
            key=f"research:{objective_id}:{self.agent_id}",
            value=report,
            agent_id=self.agent_id,
            channel="research",
            tags=["research", "findings", objective_id],
        )

        # Share raw sources
        self.memory.store(
            key=f"sources:{objective_id}:{self.agent_id}",
            value=self._sources_found,
            agent_id=self.agent_id,
            channel="research",
            tags=["research", "sources", objective_id],
        )

        # Send result back to orchestrator
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id="orchestrator",
            payload={
                "event": "task_result",
                "objective_id": objective_id,
                "agent_id": self.agent_id,
                "agent_type": "researcher",
                "summary": f"Found {len(self._sources_found)} sources on: {description[:60]}...",
                "findings_count": len(self._findings),
                "keywords": keywords,
                "report_key": f"research:{objective_id}:{self.agent_id}",
            },
            channel="swarm",
            priority=Priority.NORMAL,
        )

        self._metrics["tasks_completed"] += 1
        self._current_topic = ""

    async def _deep_dive_research(self, topic: str, depth: int) -> None:
        """Extended research with configurable depth."""
        self._research_depth = depth
        await self._perform_research(
            objective_id=f"deep-dive-{int(time.time())}",
            description=topic,
            analysis={"needs_research": True},
        )

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract research keywords from description."""
        # Simple keyword extraction — future: NLP/LLM
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "be", "this", "that"}
        words = [w.lower().strip(".,;:!?") for w in text.split() if len(w) > 3]
        keywords = [w for w in words if w not in stopwords]
        return list(set(keywords))[:8]  # Top 8 unique keywords

    def _simulate_source(self, keywords: list[str], index: int) -> dict[str, Any]:
        """Simulate a research source (future: real API calls)."""
        domains = ["arxiv.org", "github.com", "news.ycombinator.com", "sec.gov", "crunchbase.com", "who.int", "ietf.org"]
        source_types = ["paper", "repository", "news", "filing", "profile", "report", "standard"]
        return {
            "source_id": f"src-{index}-{int(time.time() * 1000) % 10000}",
            "domain": random.choice(domains),
            "type": random.choice(source_types),
            "keywords_matched": random.sample(keywords, min(2, len(keywords))),
            "relevance_score": round(random.uniform(0.6, 0.99), 2),
            "timestamp": time.time(),
            "url": f"https://{random.choice(domains)}/search?q={'+'.join(keywords[:3])}",
        }

    def _extract_finding(self, source: dict[str, Any], keywords: list[str]) -> dict[str, Any]:
        """Extract a finding from a simulated source."""
        finding_templates = [
            "Data indicates strong correlation between {k1} and {k2}.",
            "Recent developments in {k1} suggest accelerated growth.",
            "Study confirms {k1} as primary driver for {k2}.",
            "Market analysis reveals {k1} outperforming benchmarks.",
            "Technical documentation for {k1} updated with {k2} integration.",
        ]
        template = random.choice(finding_templates)
        k1 = random.choice(keywords) if keywords else "topic"
        k2 = random.choice(keywords) if len(keywords) > 1 else k1
        return {
            "source_id": source["source_id"],
            "text": template.format(k1=k1, k2=k2),
            "confidence": source["relevance_score"],
            "keywords": [k1, k2],
            "extracted_at": time.time(),
        }

    def _compile_report(self, objective_id: str, description: str) -> dict[str, Any]:
        """Compile research findings into a structured report."""
        return {
            "objective_id": objective_id,
            "topic": description,
            "researched_by": self.agent_id,
            "timestamp": time.time(),
            "sources_count": len(self._sources_found),
            "findings_count": len(self._findings),
            "avg_confidence": round(
                sum(f.get("confidence", 0) for f in self._findings) / max(len(self._findings), 1), 2
            ),
            "keywords": self._extract_keywords(description),
            "findings": self._findings,
            "sources": self._sources_found,
        }

    async def _heartbeat(self) -> None:
        """Send periodic status update while researching."""
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id="orchestrator",
            payload={
                "event": "status_report",
                "agent_id": self.agent_id,
                "status": "researching",
                "topic": self._current_topic[:50],
                "sources_so_far": len(self._sources_found),
            },
            channel="swarm",
            priority=Priority.LOW,
        )


def register() -> None:
    """Register this agent template with the factory."""
    register_agent_template(AgentType.RESEARCHER, ResearcherAgent)
