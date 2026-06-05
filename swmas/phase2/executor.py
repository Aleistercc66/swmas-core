"""
SWMAS Phase 2 — Agent Templates
executor.py — Executor Agent

Εκτελεί tasks, τρέχει simulations, παράγει concrete outputs.
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


class ExecutorAgent(BaseAgent):
    """
    Executor Agent — παράγει concrete outputs από instructions.

    Λειτουργίες:
    - Εκτελεί assigned tasks (data transform, computation, simulation)
    - Αποθηκεύει outputs στη shared memory
    - Αναφορά progress και completion
    """

    def __init__(self, agent_id, config, bus, memory) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._executed_tasks = 0
        self._pending_tasks: list[dict[str, Any]] = []

    async def _run_loop(self) -> None:
        """Process pending tasks from the queue."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                if self.status.value != "active":
                    continue
                if self._pending_tasks:
                    task = self._pending_tasks.pop(0)
                    await self._execute_task(task)

    async def _on_message(self, msg: Message) -> None:
        """Handle incoming commands."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        cmd = payload.get("command")

        if cmd == "execute_task":
            # Queue it for the run loop
            self._pending_tasks.append({"payload": payload, "sender": msg.sender_id})
            # Immediate ack
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "msg_id": msg.msg_id, "status": "queued"},
                channel=msg.channel,
                priority=Priority.LOW,
            )
        elif cmd == "run_simulation":
            await self._handle_simulation(payload, msg.sender_id)
        else:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "msg_id": msg.msg_id, "status": "unknown_command"},
                channel=msg.channel,
                priority=Priority.LOW,
            )

    async def _execute_task(self, task: dict[str, Any]) -> None:
        """Execute a queued task."""
        payload = task["payload"]
        sender = task["sender"]
        objective_id = payload.get("objective_id", "unknown")
        description = payload.get("description", "")
        analysis = payload.get("analysis", {})

        # Simulate execution based on analysis flags
        output: dict[str, Any] = {
            "objective_id": objective_id,
            "executed_by": self.agent_id,
            "started_at": time.time(),
            "description": description,
        }

        if analysis.get("needs_research"):
            # Pull related findings and compile
            findings = self.memory.query(channel="research", limit=20)
            output["research_compiled"] = len(findings)
            output["finding_keys"] = [e.key for e in findings[:10]]

        if analysis.get("needs_analysis"):
            # Pull recent analysis reports
            reports = self.memory.query(channel="analysis", limit=10)
            output["reports_consulted"] = len(reports)

        # Simulate "work" — e.g., transform data, compute summary
        output["simulated_result"] = f"processed_{objective_id}_{int(time.time())}"
        output["completed_at"] = time.time()
        output["duration"] = output["completed_at"] - output["started_at"]

        # Store output
        output_key = f"output:{objective_id}:{int(time.time())}"
        self.memory.store(
            key=output_key,
            value=output,
            agent_id=self.agent_id,
            channel="output",
            tags=["output", "execution", objective_id],
        )

        self._executed_tasks += 1
        self._metrics["tasks_completed"] += 1

        # Report completion
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id=sender,
            payload={
                "event": "task_result",
                "objective_id": objective_id,
                "agent_id": self.agent_id,
                "summary": f"Executed task; output stored at {output_key}",
                "output_key": output_key,
                "duration": output["duration"],
            },
            channel="swarm",
            priority=Priority.HIGH,
        )

    async def _handle_simulation(self, payload: dict[str, Any], sender: str) -> None:
        """Run a direct simulation and return result immediately."""
        sim_type = payload.get("sim_type", "default")
        params = payload.get("params", {})

        # Simple deterministic simulation
        iterations = params.get("iterations", 100)
        result = sum(i * 0.01 for i in range(iterations))  # dummy computation

        sim_output = {
            "sim_type": sim_type,
            "params": params,
            "result": result,
            "timestamp": time.time(),
        }

        key = f"sim:{sim_type}:{int(time.time())}"
        self.memory.store(key=key, value=sim_output, agent_id=self.agent_id, channel="simulation", tags=["sim"])

        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id=sender,
            payload={
                "event": "simulation_complete",
                "sim_key": key,
                "result": result,
            },
            channel="swarm",
            priority=Priority.NORMAL,
        )


def register() -> None:
    """Register this agent template."""
    register_agent_template(AgentType.EXECUTOR, ExecutorAgent)
