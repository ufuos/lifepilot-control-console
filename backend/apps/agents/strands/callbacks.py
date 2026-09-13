"""
Strands Agents SDK Callback Telemetry Pipeline.

Implements real-time event callbacks for monitoring execution steps, tool calls,
Human-in-the-Loop (HITL) triggers, and streaming telemetry to Django Channels and CloudWatch.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

logger = logging.getLogger("lifepilot.agents.callbacks")


class StrandsAgentCallbackHandler:
    """
    Callback handler for Strands SDK agent events.
    Broadcasting live updates to WebSockets and persisting telemetry.
    """

    def __init__(self, run_id: str, thread_id: str):
        self.run_id = str(run_id)
        self.thread_id = str(thread_id)
        self.channel_layer = get_channel_layer()
        self.room_group_name = f"agent_run_{self.run_id}"
        self.step_start_time: Optional[float] = None

    def _broadcast(self, event_data: Dict[str, Any]) -> None:
        """Helper to broadcast events to Django Channels WebSocket group."""
        if self.channel_layer:
            try:
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        "type": "agent.event",
                        "payload": event_data,
                    },
                )
            except Exception as exc:
                logger.warning("Failed to broadcast callback event to group [%s]: %s", self.room_group_name, exc)

    def on_agent_start(self, agent_name: str, prompt: str, input_payload: Dict[str, Any]) -> None:
        """Triggered when Strands Agent begins autonomous execution loop."""
        logger.info("Agent [%s] started run [%s] (thread: %s)", agent_name, self.run_id, self.thread_id)
        self._broadcast(
            {
                "event": "agent_start",
                "run_id": self.run_id,
                "thread_id": self.thread_id,
                "agent_name": agent_name,
                "timestamp": timezone.now().isoformat(),
            }
        )

    def on_step_start(self, step_number: int, node_name: str = "strands_runner") -> None:
        """Triggered at the start of a reasoning or execution step."""
        self.step_start_time = time.time()
        logger.debug("Run [%s] starting step %d in node [%s]", self.run_id, step_number, node_name)
        self._broadcast(
            {
                "event": "step_start",
                "run_id": self.run_id,
                "step_number": step_number,
                "node_name": node_name,
                "timestamp": timezone.now().isoformat(),
            }
        )

    def on_thought_generated(self, step_number: int, thought: str) -> None:
        """Triggered when LLM thought / internal monologue is generated."""
        self._broadcast(
            {
                "event": "thought",
                "run_id": self.run_id,
                "step_number": step_number,
                "thought": thought,
                "timestamp": timezone.now().isoformat(),
            }
        )

    def on_tool_start(self, step_number: int, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Triggered right before executing a Strands tool call."""
        logger.info("Run [%s] invoking tool [%s] with inputs: %s", self.run_id, tool_name, json.dumps(tool_input))
        self._broadcast(
            {
                "event": "tool_start",
                "run_id": self.run_id,
                "step_number": step_number,
                "tool_name": tool_name,
                "tool_input": tool_input,
                "timestamp": timezone.now().isoformat(),
            }
        )

    def on_tool_end(self, step_number: int, tool_name: str, tool_output: Dict[str, Any]) -> None:
        """Triggered upon successful completion of a tool execution."""
        duration = round(time.time() - (self.step_start_time or time.time()), 3)
        logger.info("Run [%s] completed tool [%s] in %ss", self.run_id, tool_name, duration)
        self._broadcast(
            {
                "event": "tool_end",
                "run_id": self.run_id,
                "step_number": step_number,
                "tool_name": tool_name,
                "tool_output": tool_output,
                "duration_seconds": duration,
                "timestamp": timezone.now().isoformat(),
            }
        )

    def on_hitl_interrupt(self, step_number: int, approval_id: str, action_type: str, details: Dict[str, Any]) -> None:
        """Triggered when execution is paused for Human-in-the-Loop authorization."""
        logger.warning("Run [%s] interrupted for HITL Approval [ID: %s, Action: %s]", self.run_id, approval_id, action_type)
        self._broadcast(
            {
                "event": "hitl_required",
                "run_id": self.run_id,
                "step_number": step_number,
                "approval_id": approval_id,
                "action_type": action_type,
                "details": details,
                "timestamp": timezone.now().isoformat(),
            }
        )

    def on_agent_finish(self, output: Dict[str, Any], total_tokens: int = 0) -> None:
        """Triggered when the agent completes its run successfully."""
        logger.info("Run [%s] completed successfully. Tokens used: %d", self.run_id, total_tokens)
        self._broadcast(
            {
                "event": "agent_finish",
                "run_id": self.run_id,
                "output": output,
                "total_tokens": total_tokens,
                "timestamp": timezone.now().isoformat(),
            }
        )

    def on_agent_error(self, error: Exception) -> None:
        """Triggered when an unexpected exception occurs during execution."""
        logger.error("Run [%s] failed with error: %s", self.run_id, str(error), exc_info=True)
        self._broadcast(
            {
                "event": "agent_error",
                "run_id": self.run_id,
                "error": str(error),
                "timestamp": timezone.now().isoformat(),
            }
        )