"""
Strands Agents SDK Integration Engine.

Implements the main execution runtime for autonomous agents built with the Strands Agents SDK.
Handles agent instantiation, dynamic tool registration, system prompt assembly, execution loop,
and streaming step callbacks to Django Channels / WebSockets.
"""

import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from django.conf import settings
from django.utils import timezone

from strands import Agent, tool

logger = logging.getLogger("lifepilot.agents.strands")


class LifePilotStrandsRunner:
    """
    Core executor for autonomous agent runs using the Strands Agents SDK.
    Supports real-time streaming updates, tool invocation tracking, and HITL interrupts.
    """

    def __init__(self, agent_run: Any):
        self.run = agent_run
        self.definition = agent_run.agent
        self.model_name = getattr(self.definition, "strands_model", None) or getattr(
            settings, "STRANDS_AGENT_CONFIG", {}
        ).get("DEFAULT_MODEL", "gemini-2.5-flash")
        self.max_iterations = getattr(self.definition, "max_iterations", 10)
        self.thread_id = agent_run.thread_id

    def _get_memory_backend(self) -> Optional[Any]:
        """Configures memory backend for multi-turn conversation and state persistence."""
        try:
            # Safely import memory components if exported by Strands SDK version
            from strands.memory import ConversationMemory
            return ConversationMemory(session_id=f"lifepilot:session:{self.thread_id}")
        except ImportError:
            logger.debug("Strands memory module using default internal session state for thread [%s]", self.thread_id)
            return None

    def _load_agent_tools(self) -> List[Any]:
        """Loads and compiles registered tools for the Strands Agent based on agent track."""
        from apps.agents.strands.tools.aws_tools import get_aws_tools
        from apps.agents.strands.tools.user_tools import get_user_tools

        tools: List[Any] = []
        
        # Core user tools (e.g., email notification, task queueing, calendar scheduling)
        user_tools = get_user_tools(agent_run=self.run)
        tools.extend(user_tools)

        # AWS Bedrock / AgentCore integration tools
        aws_tools = get_aws_tools(
            aws_region=getattr(settings, "AWS_DEFAULT_REGION", "us-east-1"),
            agent_id=getattr(self.definition, "aws_bedrock_agent_id", None),
        )
        tools.extend(aws_tools)

        logger.info("Loaded %d Strands tools for agent [%s]", len(tools), self.definition.name)
        return tools

    def build_agent(self) -> Agent:
        """Constructs a configured Strands Agent instance."""
        from apps.agents.strands.system_prompts import get_agent_system_prompt

        memory = self._get_memory_backend()
        tools = self._load_agent_tools()
        system_prompt = get_agent_system_prompt(
            slug=self.definition.slug,
            track=self.definition.track,
            base_prompt=self.definition.system_prompt,
        )

        agent_kwargs = {
            "name": self.definition.name,
            "model": self.model_name,
            "instructions": system_prompt,
            "tools": tools,
            "max_iterations": self.max_iterations,
        }
        if memory is not None:
            agent_kwargs["memory"] = memory

        return Agent(**agent_kwargs)

    async def execute_run_stream(
        self, prompt: str, context_payload: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes the Strands Agent asynchronously, yielding real-time step events
        and output chunks for WebSocket broadcast.
        """
        from apps.agents.models import AgentStep, AgentStatus, HumanApprovalRequest

        start_time = time.time()
        self.run.status = AgentStatus.RUNNING
        self.run.started_at = timezone.now()
        await self.run.asave(update_fields=["status", "started_at"])

        agent = self.build_agent()
        step_counter = 1

        context_payload = context_payload or self.run.input_payload
        enhanced_prompt = f"User Request: {prompt}\nContext Data: {context_payload}"

        try:
            logger.info("Starting Strands Agent execution stream for run [%s]", self.run.id)

            # Stream intermediate steps from Strands Agent execution loop
            async for step_event in agent.run_stream(enhanced_prompt):
                event_type = step_event.get("type", "reasoning")
                thought = step_event.get("thought", "")
                tool_name = step_event.get("tool_name")
                tool_input = step_event.get("tool_input")
                tool_output = step_event.get("tool_output")

                # Check if step requires Human-in-the-Loop (HITL) authorization
                if getattr(self.definition, "requires_hitl", False) and step_event.get("requires_approval"):
                    approval_req = await HumanApprovalRequest.objects.acreate(
                        run=self.run,
                        action_type=tool_name or "sensitive_operation",
                        action_description=f"Agent '{self.definition.name}' requested permission to execute '{tool_name}'.",
                        proposed_payload=tool_input or {},
                        expires_at=timezone.now() + timezone.timedelta(seconds=86400),
                    )

                    self.run.status = AgentStatus.AWAITING_APPROVAL
                    await self.run.asave(update_fields=["status"])

                    yield {
                        "type": "hitl_required",
                        "step_number": step_counter,
                        "approval_id": str(approval_req.id),
                        "action_type": approval_req.action_type,
                        "description": approval_req.action_description,
                        "payload": approval_req.proposed_payload,
                    }
                    logger.info("Run [%s] paused for Human Approval (ID: %s)", self.run.id, approval_req.id)
                    return

                # Log step to Database
                await AgentStep.objects.acreate(
                    run=self.run,
                    step_number=step_counter,
                    step_type=event_type,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=tool_output,
                    thought_process=thought,
                )

                # Yield structured payload for consumer WebSocket stream
                yield {
                    "type": "step_update",
                    "step_number": step_counter,
                    "event_type": event_type,
                    "tool_name": tool_name,
                    "thought": thought,
                    "tool_output": tool_output,
                    "timestamp": timezone.now().isoformat(),
                }

                step_counter += 1

            # Complete Run Execution
            final_output = getattr(agent, "get_last_response", lambda: {})() or {}
            execution_duration = round(time.time() - start_time, 2)

            self.run.status = AgentStatus.COMPLETED
            self.run.output_result = {"response": final_output}
            self.run.execution_time_seconds = execution_duration
            self.run.completed_at = timezone.now()
            await self.run.asave(
                update_fields=["status", "output_result", "execution_time_seconds", "completed_at"]
            )

            yield {
                "type": "run_completed",
                "run_id": str(self.run.id),
                "status": self.run.status,
                "execution_time_seconds": execution_duration,
                "result": self.run.output_result,
            }

        except Exception as exc:
            logger.exception("Error executing Strands Agent run [%s]: %s", self.run.id, str(exc))
            self.run.status = AgentStatus.FAILED
            self.run.error_message = str(exc)
            await self.run.asave(update_fields=["status", "error_message"])

            yield {
                "type": "run_failed",
                "run_id": str(self.run.id),
                "error": str(exc),
            }