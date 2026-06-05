"""
SWMAS Phase 2 — Agent Templates
analyst.py — Analyst Agent

Αναλύει δεδομένα από τη shared memory, βρίσκει patterns,
παράγει reports και insights.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

# Path setup for Phase 1 imports
import sys
from pathlib import Path
_PHASE1 = Path(__file__).resolve().parent.parent / "phase1"
if str(_PHASE1) not in sys.path:
    sys.path.insert(0, str(_PHASE1))

from agent_factory import BaseAgent, AgentType, register_agent_template
from communication_bus import Message, Priority


class AnalystAgent(BaseAgent):
    """
    Analyst Agent — μετατρέπει raw data σε structured insights.

    Λειτουργίες:
    - Ανάλυση findings από researcher
    - Pattern detection σε metrics και data streams
    - Παραγωγή reports με statistics
    - Alert σε anomalies
    """

    def __init__(self, agent_id, config, bus, memory) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._analysis_cycles = 0
        self._last_alert_ts = 0.0

    async def _run_loop(self) -> None:
        """Periodic analysis: scan memory, detect patterns, generate reports."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=15.0)
            except asyncio.TimeoutError:
                if self.status.value != "active":
                    continue
                self._analysis_cycles += 1
                await self._perform_background_analysis()

    async def _perform_background_analysis(self) -> None:
        """Analyze recent memory entries and produce summary reports."""
        # Pull recent findings and raw data
        findings = self.memory.query(channel="research", limit=30)
        raw_data = self.memory.query(channel="data", limit=30)
        all_entries = findings + raw_data

        if not all_entries:
            return

        # Simple pattern detection: frequency by source agent
        agent_counts: dict[str, int] = {}
        for e in all_entries:
            agent_counts[e.agent_id] = agent_counts.get(e.agent_id, 0) + 1

        # Detect anomaly: any single agent flooding memory
        max_count = max(agent_counts.values()) if agent_counts else 0
        anomaly = max_count > 20

        # Build report
        report = {
            "cycle": self._analysis_cycles,
            "timestamp": time.time(),
            "entries_analyzed": len(all_entries),
            "agent_distribution": agent_counts,
            "anomaly_detected": anomaly,
            "top_keys": [e.key for e in all_entries[:5]],
        }

        report_key = f"analysis:report:{self.agent_id}:{self._analysis_cycles}"
        self.memory.store(
            key=report_key,
            value=report,
            agent_id=self.agent_id,
            channel="analysis",
            tags=["analysis", "report", "auto"],
        )

        # If anomaly, alert swarm (throttle to once per 60s)
        if anomaly and (time.time() - self._last_alert_ts) > 60:
            self._last_alert_ts = time.time()
            await self.bus.broadcast(
                sender_id=self.agent_id,
                payload={
                    "event": "anomaly_alert",
                    "type": "memory_flood",
                    "details": f"Agent {max(agent_counts, key=agent_counts.get)} has {max_count} entries",
                    "report_key": report_key,
                },
                channel="swarm",
                priority=Priority.HIGH,
            )

    async def _on_message(self, msg: Message) -> None:
        """Handle commands from orchestrator."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        cmd = payload.get("command")

        if cmd == "execute_task":
            await self._handle_execute_task(payload, msg.sender_id)
        elif cmd == "analyze_data":
            await self._handle_analyze_data(payload, msg.sender_id)
        else:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "msg_id": msg.msg_id, "status": "unknown_command"},
                channel=msg.channel,
                priority=Priority.LOW,
            )

    async def _handle_execute_task(self, payload: dict[str, Any], sender: str) -> None:
        """Run analysis for an orchestrator-assigned objective."""
        objective_id = payload.get("objective_id", "unknown")
        description = payload.get("description", "")

        # Fetch related research
        related = self.memory.query(channel="research", limit=50)
        related += self.memory.query(pattern=description[:15], limit=20)

        # Simple quant analysis: count entries, time spread
        timestamps = [e.created_at for e in related if hasattr(e, "created_at")]
        time_span = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0

        analysis_result = {
            "objective_id": objective_id,
            "description": description,
            "entries_considered": len(related),
            "time_span_seconds": time_span,
            "top_channels": self._top_channels(related),
            "confidence": "medium" if len(related) >= 10 else "low",
            "generated_at": time.time(),
        }

        result_key = f"analysis:result:{objective_id}:{int(time.time())}"
        self.memory.store(
            key=result_key,
            value=analysis_result,
            agent_id=self.agent_id,
            channel="analysis",
            tags=["analysis", "result", objective_id],
        )

        self._metrics["tasks_completed"] += 1

        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id=sender,
            payload={
                "event": "task_result",
                "objective_id": objective_id,
                "agent_id": self.agent_id,
                "summary": f"Analyzed {len(related)} entries; confidence={analysis_result['confidence']}",
                "result_key": result_key,
            },
            channel="swarm",
            priority=Priority.HIGH,
        )

    async def _handle_analyze_data(self, payload: dict[str, Any], sender: str) -> None:
        """Direct request to analyze a specific data key."""
        keys = payload.get("keys", [])
        results = {}
        for k in keys:
            val = self.memory.retrieve(k)
            if val is not None:
                # Simple size-based "complexity" score
                size = len(str(val))
                results[k] = {"size": size, "complexity": "high" if size > 1000 else "low"}
            else:
                results[k] = {"error": "not_found"}

        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id=sender,
            payload={
                "event": "analyze_result",
                "keys": keys,
                "results": results,
            },
            channel="swarm",
            priority=Priority.NORMAL,
        )

    @staticmethod
    def _top_channels(entries: list) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in entries:
            ch = getattr(e, "channel", "unknown")
            counts[ch] = counts.get(ch, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5])


def register() -> None:
    """Register this agent template."""
    register_agent_template(AgentType.ANALYST, AnalystAgent)
