"""
SWMAS Phase 2 — Agent Templates
researcher.py — Research Agent

Συλλέγει πληροφορίες, κάνει web search simulation,
αποθηκεύει findings στη shared memory.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

# Adjust path so Phase 2 can import Phase 1 modules
import sys
from pathlib import Path
_PHASE1 = Path(__file__).resolve().parent.parent / "phase1"
if str(_PHASE1) not in sys.path:
    sys.path.insert(0, str(_PHASE1))

from agent_factory import BaseAgent, AgentType, register_agent_template
from communication_bus import Message, Priority
from shared_memory import SharedMemory


class ResearcherAgent(BaseAgent):
    """
    Researcher Agent — συλλέγει, οργανώνει και αποθηκεύει πληροφορίες.

    Λειτουργίες:
    - Ανταποκρίνεται σε commands από orchestrator για έρευνα
    - Κάνει periodic scan στη μνήμη για data gaps
    - Simulates web research (aggregates από memory + external hints)
    - Αποθηκεύει structured findings
    """

    def __init__(self, agent_id, config, bus, memory) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._current_task: dict[str, Any] | None = None
        self._research_cycles = 0

    async def _run_loop(self) -> None:
        """Periodic research cycle: scan for gaps, consolidate findings."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                if self.status.value != "active":
                    continue
                self._research_cycles += 1
                await self._perform_background_research()

    async def _perform_background_research(self) -> None:
        """Scan shared memory for data gaps and consolidate loose findings."""
        # Find all entries tagged as 'finding' without a 'consolidated' tag
        loose = self.memory.query(tags=["finding"], limit=50)
        unconsolidated = [e for e in loose if "consolidated" not in e.tags]

        if len(unconsolidated) >= 3:
            # Build a mini report
            report = {
                "timestamp": time.time(),
                "cycle": self._research_cycles,
                "topic": self.config.objective,
                "findings_count": len(unconsolidated),
                "summary": f"Consolidated {len(unconsolidated)} loose findings",
                "sources": [e.key for e in unconsolidated],
            }
            self.memory.store(
                key=f"research:consolidated:{self.agent_id}:{self._research_cycles}",
                value=report,
                agent_id=self.agent_id,
                channel="research",
                tags=["research", "consolidated", "report"],
            )
            # Mark originals as consolidated
            for e in unconsolidated:
                self.memory.store(
                    key=e.key,
                    value=e.value,
                    agent_id=e.agent_id,
                    channel=e.channel,
                    tags=e.tags + ["consolidated"],
                )

            # Notify swarm
            await self.bus.broadcast(
                sender_id=self.agent_id,
                payload={
                    "event": "research_consolidated",
                    "agent_id": self.agent_id,
                    "findings": len(unconsolidated),
                    "report_key": f"research:consolidated:{self.agent_id}:{self._research_cycles}",
                },
                channel="swarm",
                priority=Priority.NORMAL,
            )

    async def _on_message(self, msg: Message) -> None:
        """Handle commands from orchestrator or other agents."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        cmd = payload.get("command")

        if cmd == "execute_task":
            await self._handle_execute_task(payload, msg.sender_id)
        elif cmd == "query_research":
            await self._handle_query_research(payload, msg.sender_id)
        else:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "msg_id": msg.msg_id, "status": "unknown_command"},
                channel=msg.channel,
                priority=Priority.LOW,
            )

    async def _handle_execute_task(self, payload: dict[str, Any], sender: str) -> None:
        """Execute a research task assigned by orchestrator."""
        objective_id = payload.get("objective_id", "unknown")
        description = payload.get("description", "")
        analysis = payload.get("analysis", {})

        # Simulate research: search shared memory for related data
        related = self.memory.query(pattern=description[:20], limit=20)
        related += self.memory.query(channel="research", limit=20)

        # Build simulated findings
        findings = {
            "objective_id": objective_id,
            "description": description,
            "related_entries_found": len(related),
            "related_keys": [e.key for e in related[:10]],
            "analysis_needs": analysis,
            "researched_at": time.time(),
            "agent_id": self.agent_id,
        }

        # Store structured finding
        finding_key = f"finding:{objective_id}:{int(time.time())}"
        self.memory.store(
            key=finding_key,
            value=findings,
            agent_id=self.agent_id,
            channel="research",
            tags=["finding", objective_id, "auto"],
        )

        self._metrics["tasks_completed"] += 1

        # Report back
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id=sender,
            payload={
                "event": "task_result",
                "objective_id": objective_id,
                "agent_id": self.agent_id,
                "summary": f"Found {len(related)} related entries; stored finding at {finding_key}",
                "finding_key": finding_key,
            },
            channel="swarm",
            priority=Priority.HIGH,
        )

    async def _handle_query_research(self, payload: dict[str, Any], sender: str) -> None:
        """Answer a direct query about stored research."""
        pattern = payload.get("pattern", "")
        results = self.memory.query(pattern=pattern, channel="research", limit=10)
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id=sender,
            payload={
                "event": "query_result",
                "pattern": pattern,
                "matches": [e.to_dict() for e in results],
                "count": len(results),
            },
            channel="swarm",
            priority=Priority.NORMAL,
        )


def register() -> None:
    """Register this agent template in the global registry."""
    register_agent_template(AgentType.RESEARCHER, ResearcherAgent)
