"""
SWMAS Phase 2 — Agent Templates
analyst.py — Analyst Agent

Analyzes data from shared memory, detects patterns,
generates insights and structured reports.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from typing import Any

from agent_factory import BaseAgent, AgentConfig, AgentType, register_agent_template
from communication_bus import CommunicationBus, Message, Priority
from shared_memory import SharedMemory


class AnalystAgent(BaseAgent):
    """
    Specialized agent for data analysis and pattern detection.

    Capabilities:
    - Reads data from shared memory (research, metrics, logs)
    - Statistical analysis and trend detection
    - Pattern recognition across multiple sources
    - Structured report generation with recommendations
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        bus: CommunicationBus,
        memory: SharedMemory,
    ) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._analysis_queue: list[dict[str, Any]] = []
        self._reports_generated: int = 0

    async def _run_loop(self) -> None:
        """Main analysis loop — continuous mode: auto-analyze periodically."""
        continuous = self.config.context.get("continuous", False)
        interval = self.config.context.get("interval", 300)
        last_auto_scan = 0

        while not self._stop_event.is_set():
            try:
                if self._analysis_queue:
                    task = self._analysis_queue.pop(0)
                    await self._perform_analysis(task)
                else:
                    # Passive monitoring: scan for new data to analyze
                    await self._passive_scan()

                    # Auto-analysis in continuous mode
                    if continuous and (time.time() - last_auto_scan) > interval:
                        await self._auto_analyze()
                        last_auto_scan = time.time()

                    await asyncio.wait_for(self._stop_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _auto_analyze(self) -> None:
        """Perform automated periodic analysis."""
        # Look for latest research to analyze
        research_entries = self.memory.query(channel="research", limit=5)
        if research_entries:
            latest = research_entries[0]
            obj_id = f"auto-analysis-{int(time.time())}"
            self._analysis_queue.append({
                "objective_id": obj_id,
                "description": f"Auto-analysis of {latest.key}",
                "analysis_req": {"auto": True, "continuous": True},
            })

    async def _on_message(self, msg: Message) -> None:
        """Handle incoming analysis commands."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        command = payload.get("command", "")

        if command == "execute_task":
            obj_id = payload.get("objective_id", "")
            description = payload.get("description", "")
            analysis_req = payload.get("analysis", {})
            self._analysis_queue.append({
                "objective_id": obj_id,
                "description": description,
                "analysis_req": analysis_req,
            })

        elif command == "analyze_data":
            data_key = payload.get("data_key", "")
            analysis_type = payload.get("analysis_type", "general")
            await self._analyze_specific(data_key, analysis_type)

        else:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "original_msg_id": msg.msg_id},
                channel=msg.channel,
                priority=Priority.LOW,
            )

    async def _perform_analysis(self, task: dict[str, Any]) -> None:
        """Execute an analysis task."""
        obj_id = task["objective_id"]
        description = task["description"]
        req = task["analysis_req"]

        # Gather relevant data from shared memory
        data_entries = self.memory.query(
            pattern=obj_id,
            channel="research",
            limit=50,
        )

        if not data_entries:
            # Try broader search
            data_entries = self.memory.query(
                channel="research",
                limit=30,
            )

        # Extract and analyze
        findings = [entry.value for entry in data_entries if entry.value]
        report = self._generate_report(obj_id, description, findings, req)

        # Store report
        self.memory.store(
            key=f"analysis:{obj_id}:{self.agent_id}",
            value=report,
            agent_id=self.agent_id,
            channel="analysis",
            tags=["analysis", "report", obj_id],
        )

        # Send result
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id="orchestrator",
            payload={
                "event": "task_result",
                "objective_id": obj_id,
                "agent_id": self.agent_id,
                "agent_type": "analyst",
                "summary": f"Analysis complete: {report['key_insights_count']} insights, {report['patterns_found']} patterns",
                "report_key": f"analysis:{obj_id}:{self.agent_id}",
                "confidence": report["overall_confidence"],
            },
            channel="swarm",
            priority=Priority.NORMAL,
        )

        self._metrics["tasks_completed"] += 1
        self._reports_generated += 1

    async def _analyze_specific(self, data_key: str, analysis_type: str) -> None:
        """Analyze a specific dataset by key."""
        data = self.memory.retrieve(data_key)
        if data is None:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id="orchestrator",
                payload={
                    "event": "agent_error",
                    "agent_id": self.agent_id,
                    "error": f"Data not found for key: {data_key}",
                },
                channel="swarm",
                priority=Priority.HIGH,
            )
            return

        result = {"data_key": data_key, "analysis_type": analysis_type, "timestamp": time.time()}

        if analysis_type == "trend":
            result["trends"] = self._detect_trends(data)
        elif analysis_type == "correlation":
            result["correlations"] = self._find_correlations(data)
        elif analysis_type == "summary":
            result["summary"] = self._summarize(data)
        else:
            result["overview"] = self._general_analysis(data)

        self.memory.store(
            key=f"analysis:{data_key}:{analysis_type}",
            value=result,
            agent_id=self.agent_id,
            channel="analysis",
            tags=["analysis", analysis_type],
        )

    def _generate_report(
        self,
        obj_id: str,
        description: str,
        findings: list[Any],
        req: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a structured analysis report."""
        patterns = self._extract_patterns(findings)
        insights = self._generate_insights(findings, patterns)
        recommendations = self._generate_recommendations(findings, insights)

        confidence_scores = []
        for f in findings:
            if isinstance(f, dict):
                confidence_scores.append(f.get("confidence", 0.5))
                confidence_scores.append(f.get("relevance_score", 0.5))

        avg_confidence = round(statistics.mean(confidence_scores), 2) if confidence_scores else 0.5

        return {
            "objective_id": obj_id,
            "topic": description,
            "analyzed_by": self.agent_id,
            "timestamp": time.time(),
            "sources_analyzed": len(findings),
            "patterns_found": len(patterns),
            "key_insights_count": len(insights),
            "recommendations_count": len(recommendations),
            "overall_confidence": avg_confidence,
            "patterns": patterns,
            "insights": insights,
            "recommendations": recommendations,
            "urgency_flag": req.get("urgency", False),
        }

    def _extract_patterns(self, findings: list[Any]) -> list[dict[str, Any]]:
        """Detect patterns across findings."""
        patterns = []
        keywords_seen: dict[str, int] = {}

        for f in findings:
            if isinstance(f, dict):
                kw = f.get("keywords", [])
                for k in kw:
                    keywords_seen[k] = keywords_seen.get(k, 0) + 1

        # Find recurring keywords as patterns
        for kw, count in keywords_seen.items():
            if count >= 2:
                patterns.append({
                    "type": "recurring_keyword",
                    "keyword": kw,
                    "frequency": count,
                    "significance": "high" if count >= 3 else "medium",
                })

        return patterns

    def _generate_insights(
        self,
        findings: list[Any],
        patterns: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate insights from findings and patterns."""
        insights = []

        if not findings:
            return insights

        # Insight 1: Data volume assessment
        insights.append({
            "type": "volume",
            "text": f"Analyzed {len(findings)} data sources for this objective.",
            "priority": "info",
        })

        # Insight 2: Pattern-based insight
        if patterns:
            top_pattern = max(patterns, key=lambda p: p["frequency"])
            insights.append({
                "type": "pattern",
                "text": f"Recurring theme detected: '{top_pattern['keyword']}' appears {top_pattern['frequency']} times.",
                "priority": "high" if top_pattern["significance"] == "high" else "medium",
            })

        # Insight 3: Confidence assessment
        confidences = []
        for f in findings:
            if isinstance(f, dict):
                confidences.append(f.get("confidence", 0.5))
                confidences.append(f.get("relevance_score", 0.5))

        if confidences:
            avg_c = statistics.mean(confidences)
            insights.append({
                "type": "confidence",
                "text": f"Average source confidence: {avg_c:.0%}",
                "priority": "high" if avg_c >= 0.8 else "medium" if avg_c >= 0.6 else "low",
            })

        return insights

    def _generate_recommendations(
        self,
        findings: list[Any],
        insights: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate actionable recommendations."""
        recommendations = []

        low_conf = any(i["type"] == "confidence" and i["priority"] == "low" for i in insights)
        if low_conf:
            recommendations.append({
                "action": "deep_research",
                "text": "Source confidence is low. Recommend deeper research with additional sources.",
                "priority": "high",
            })

        if len(findings) < 3:
            recommendations.append({
                "action": "expand_sources",
                "text": "Limited data sources found. Recommend expanding search scope.",
                "priority": "medium",
            })

        # Always add a generic action
        recommendations.append({
            "action": "review",
            "text": "Review synthesized findings before making strategic decisions.",
            "priority": "info",
        })

        return recommendations

    def _detect_trends(self, data: Any) -> list[dict[str, Any]]:
        """Detect trends in time-series or sequential data."""
        if not isinstance(data, list):
            return [{"type": "invalid", "text": "Trend analysis requires list data"}]
        return [{"type": "trend", "data_points": len(data), "direction": "stable"}]

    def _find_correlations(self, data: Any) -> list[dict[str, Any]]:
        """Find correlations in multi-dimensional data."""
        return [{"type": "correlation", "pairs_analyzed": 1, "strongest": "none"}]

    def _summarize(self, data: Any) -> dict[str, Any]:
        """Generate a summary of data."""
        return {"type": "summary", "data_size": len(str(data)), "overview": str(data)[:200]}

    def _general_analysis(self, data: Any) -> dict[str, Any]:
        """General-purpose analysis of any data structure."""
        return {
            "type": "general",
            "data_type": type(data).__name__,
            "size_estimate": len(str(data)),
            "has_nested": isinstance(data, (dict, list)),
        }

    async def _passive_scan(self) -> None:
        """Periodically scan for unanalyzed data."""
        # Look for research entries without corresponding analysis
        research_entries = self.memory.query(channel="research", limit=20)
        for entry in research_entries:
            existing = self.memory.query(
                pattern=f"analysis:{entry.key}",
                channel="analysis",
                limit=1,
            )
            if not existing:
                # Auto-queue for analysis
                self._analysis_queue.append({
                    "objective_id": entry.key,
                    "description": f"Auto-analysis of {entry.key}",
                    "analysis_req": {"auto": True},
                })


def register() -> None:
    """Register this agent template with the factory."""
    register_agent_template(AgentType.ANALYST, AnalystAgent)
