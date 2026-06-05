"""
SWMAS Phase 2 — Agent Templates
executor.py — Executor Agent

Executes concrete tasks, runs simulations, produces outputs,
and deploys actions based on orchestrator directives.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from agent_factory import BaseAgent, AgentConfig, AgentType, register_agent_template
from communication_bus import CommunicationBus, Message, Priority
from shared_memory import SharedMemory


class ExecutorAgent(BaseAgent):
    """
    Specialized agent for task execution and action deployment.

    Capabilities:
    - Executes specific tasks with concrete outputs
    - Runs simulations and validations
    - Deploys actions to external systems (simulated)
    - Tracks execution state and reports progress
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        bus: CommunicationBus,
        memory: SharedMemory,
    ) -> None:
        super().__init__(agent_id, config, bus, memory)
        self._execution_log: list[dict[str, Any]] = []
        self._current_task: dict[str, Any] = {}

    async def _run_loop(self) -> None:
        """Main execution loop — continuous mode: execute scheduled tasks."""
        continuous = self.config.context.get("continuous", False)

        while not self._stop_event.is_set():
            try:
                # Heartbeat if executing
                if self._current_task:
                    await self._send_progress()

                # In continuous mode, listen for tasks from orchestrator
                if continuous:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=6.0)
                else:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=6.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _on_message(self, msg: Message) -> None:
        """Handle incoming execution commands."""
        self._metrics["messages_received"] += 1
        payload = msg.payload
        command = payload.get("command", "")

        if command == "execute_task":
            obj_id = payload.get("objective_id", "")
            description = payload.get("description", "")
            analysis = payload.get("analysis", {})
            deadline = payload.get("deadline", time.time() + 300)
            await self._execute(obj_id, description, analysis, deadline)

        elif command == "run_simulation":
            sim_type = payload.get("simulation_type", "default")
            params = payload.get("parameters", {})
            await self._run_simulation(sim_type, params)

        elif command == "validate_output":
            output_key = payload.get("output_key", "")
            criteria = payload.get("criteria", [])
            await self._validate(output_key, criteria)

        else:
            await self.bus.send(
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                payload={"ack": True, "original_msg_id": msg.msg_id},
                channel=msg.channel,
                priority=Priority.LOW,
            )

    async def _execute(
        self,
        objective_id: str,
        description: str,
        analysis: dict[str, Any],
        deadline: float,
    ) -> None:
        """Execute a concrete task."""
        self._current_task = {
            "objective_id": objective_id,
            "description": description,
            "started_at": time.time(),
            "deadline": deadline,
            "status": "running",
            "steps": [],
        }

        # Phase 2: Simulated execution steps
        steps = self._plan_execution(description, analysis)

        for step in steps:
            step_result = await self._run_step(step)
            self._current_task["steps"].append({
                "step": step,
                "result": step_result,
                "timestamp": time.time(),
            })
            await asyncio.sleep(0.2)  # Simulate work

        # Compile output
        output = {
            "objective_id": objective_id,
            "executed_by": self.agent_id,
            "description": description,
            "started_at": self._current_task["started_at"],
            "completed_at": time.time(),
            "steps_executed": len(steps),
            "step_results": self._current_task["steps"],
            "success": all(s["result"].get("success", True) for s in self._current_task["steps"]),
        }

        # Store output
        self.memory.store(
            key=f"execution:{objective_id}:{self.agent_id}",
            value=output,
            agent_id=self.agent_id,
            channel="execution",
            tags=["execution", "output", objective_id],
        )

        # Log
        self._execution_log.append(output)

        # Send result
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id="orchestrator",
            payload={
                "event": "task_result",
                "objective_id": objective_id,
                "agent_id": self.agent_id,
                "agent_type": "executor",
                "summary": f"Executed {len(steps)} steps — {'SUCCESS' if output['success'] else 'PARTIAL'}",
                "output_key": f"execution:{objective_id}:{self.agent_id}",
                "success": output["success"],
                "duration": round(time.time() - self._current_task["started_at"], 2),
            },
            channel="swarm",
            priority=Priority.NORMAL,
        )

        self._metrics["tasks_completed"] += 1
        self._current_task = {}

    async def _run_step(self, step: dict[str, Any]) -> dict[str, Any]:
        """Run a single execution step."""
        step_type = step.get("type", "generic")
        result = {"success": True, "step_type": step_type}

        if step_type == "fetch":
            # Simulate data fetch
            result["data_size"] = len(step.get("target", "")) * 10
            result["status"] = "fetched"

        elif step_type == "process":
            # Simulate processing
            result["processed_items"] = step.get("count", 1)
            result["status"] = "processed"

        elif step_type == "deploy":
            # Simulate deployment
            result["deployed"] = True
            result["target"] = step.get("target", "unknown")
            result["status"] = "deployed"

        elif step_type == "verify":
            # Simulate verification
            result["checks_passed"] = step.get("checks", [])
            result["status"] = "verified"

        else:
            result["status"] = "completed"

        return result

    def _plan_execution(self, description: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Plan execution steps from description and analysis."""
        steps = []
        desc_lower = description.lower()

        # Determine steps based on keywords
        if any(k in desc_lower for k in ["fetch", "get", "collect", "retrieve"]):
            steps.append({"type": "fetch", "target": description[:40]})

        if any(k in desc_lower for k in ["process", "analyze", "compute", "calculate"]):
            steps.append({"type": "process", "count": 3})

        if any(k in desc_lower for k in ["deploy", "launch", "publish", "release"]):
            steps.append({"type": "deploy", "target": description[:40]})

        if any(k in desc_lower for k in ["verify", "validate", "check", "test"]):
            steps.append({"type": "verify", "checks": ["integrity", "completeness"]})

        # If no specific steps matched, add generic steps
        if not steps:
            steps = [
                {"type": "fetch", "target": description[:40]},
                {"type": "process", "count": 1},
                {"type": "verify", "checks": ["completeness"]},
            ]

        return steps

    async def _run_simulation(self, sim_type: str, params: dict[str, Any]) -> None:
        """Run a simulation task."""
        sim_result = {
            "simulation_type": sim_type,
            "parameters": params,
            "started_at": time.time(),
            "iterations": params.get("iterations", 100),
            "results": {"mean": 0.5, "std": 0.1, "success_rate": 0.95},
        }

        await asyncio.sleep(0.3)  # Simulate computation

        sim_result["completed_at"] = time.time()
        sim_result["duration"] = round(sim_result["completed_at"] - sim_result["started_at"], 3)

        self.memory.store(
            key=f"sim:{sim_type}:{int(time.time())}",
            value=sim_result,
            agent_id=self.agent_id,
            channel="simulation",
            tags=["simulation", sim_type],
        )

    async def _validate(self, output_key: str, criteria: list[str]) -> None:
        """Validate an output against criteria."""
        data = self.memory.retrieve(output_key)
        validation = {
            "output_key": output_key,
            "validated_by": self.agent_id,
            "timestamp": time.time(),
            "criteria": criteria,
            "results": {},
            "overall_pass": True,
        }

        for criterion in criteria:
            # Simulated validation
            passed = data is not None
            validation["results"][criterion] = "pass" if passed else "fail"
            if not passed:
                validation["overall_pass"] = False

        self.memory.store(
            key=f"validation:{output_key}",
            value=validation,
            agent_id=self.agent_id,
            channel="validation",
            tags=["validation", output_key],
        )

    async def _send_progress(self) -> None:
        """Send execution progress update."""
        if not self._current_task:
            return
        steps_done = len(self._current_task.get("steps", []))
        await self.bus.send(
            sender_id=self.agent_id,
            recipient_id="orchestrator",
            payload={
                "event": "status_report",
                "agent_id": self.agent_id,
                "status": "executing",
                "objective_id": self._current_task.get("objective_id", ""),
                "steps_completed": steps_done,
            },
            channel="swarm",
            priority=Priority.LOW,
        )


def register() -> None:
    """Register this agent template with the factory."""
    register_agent_template(AgentType.EXECUTOR, ExecutorAgent)
