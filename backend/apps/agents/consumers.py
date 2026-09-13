"""
WebSocket Consumers for LifePilot Agents Engine.

Provides bi-directional, async WebSockets via Django Channels for:
- Live streaming agent thoughts, execution events, and step logs.
- Real-time HITL (Human-in-the-Loop) authorization requests and responses.
- Active execution interruption and user cancellation triggers.
"""

import json
import logging
from typing import Any, Dict, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from apps.agents.models import AgentRun, AgentStatus, HumanApprovalRequest

logger = logging.getLogger(__name__)


class AgentRunConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer handling real-time telemetry streaming for an ongoing AgentRun.

    Endpoint pattern: ws/agents/runs/<run_id>/
    Channel Group:    agent_run_<run_id>
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.run_id: Optional[str] = None
        self.room_group_name: Optional[str] = None
        self.user = None

    async def connect(self) -> None:
        """Establishes WebSocket connection and registers client to run room channel group."""
        self.user = self.scope.get("user", AnonymousUser())

        # Unauthenticated sockets rejected immediately
        if self.user.is_anonymous:
            logger.warning("Rejected unauthenticated WebSocket attempt on AgentRun Consumer.")
            await self.close(code=4401)
            return

        self.run_id = self.scope["url_route"]["kwargs"].get("run_id")
        if not self.run_id:
            await self.close(code=4400)
            return

        # Ensure the requested AgentRun exists and belongs to/is accessible by user
        run_exists = await self._verify_run_access(self.run_id, self.user.id)
        if not run_exists:
            logger.warning(
                f"Unauthorized WebSocket connection attempt for Run ID {self.run_id} by User ID {self.user.id}."
            )
            await self.close(code=4403)
            return

        self.room_group_name = f"agent_run_{self.run_id}"

        # Join run channel group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()
        logger.info(f"User {self.user.id} connected to WebSocket channel for AgentRun {self.run_id}.")

        # Send connection confirmation payload
        await self.send_json(
            {
                "type": "connection_established",
                "run_id": str(self.run_id),
                "message": f"Connected to telemetry stream for run {self.run_id}",
            }
        )

    async def disconnect(self, close_code: int) -> None:
        """Cleans up group subscription upon socket disconnection."""
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )
            logger.info(f"WebSocket client disconnected from group {self.room_group_name} (Code: {close_code})")

    async def receive_json(self, content: Dict[str, Any], **kwargs: Any) -> None:
        """
        Handles incoming JSON frames sent from the client (e.g. client cancellation or HITL response).
        """
        action = content.get("action")

        if action == "cancel_run":
            await self._handle_cancel_run()

        elif action == "submit_approval":
            approval_id = content.get("approval_id")
            decision = content.get("decision")  # "approve" or "reject"
            notes = content.get("notes", "")

            if approval_id and decision in ["approve", "reject"]:
                await self._handle_hitl_decision(approval_id, decision, notes)
            else:
                await self.send_json(
                    {
                        "type": "error",
                        "message": "Invalid submit_approval payload. Requires approval_id and valid decision.",
                    }
                )
        else:
            await self.send_json(
                {
                    "type": "error",
                    "message": f"Unknown action '{action}'",
                }
            )

    # ------------------------------------------------------------------
    # Channel Layer Event Handlers (Triggered by backend background nodes)
    # ------------------------------------------------------------------

    async def agent_step_event(self, event: Dict[str, Any]) -> None:
        """Broadcasts a newly executed agent step (thought, tool input/output) to client."""
        await self.send_json(
            {
                "type": "agent_step",
                "step_number": event.get("step_number"),
                "step_type": event.get("step_type"),
                "node_name": event.get("node_name"),
                "tool_name": event.get("tool_name"),
                "tool_input": event.get("tool_input"),
                "tool_output": event.get("tool_output"),
                "thought_process": event.get("thought_process"),
                "timestamp": event.get("timestamp"),
            }
        )

    async def hitl_approval_required(self, event: Dict[str, Any]) -> None:
        """Notifies the client that human approval is required to proceed with an execution step."""
        await self.send_json(
            {
                "type": "hitl_approval_required",
                "approval_id": event.get("approval_id"),
                "action_type": event.get("action_type"),
                "action_description": event.get("action_description"),
                "proposed_payload": event.get("proposed_payload"),
                "expires_at": event.get("expires_at"),
            }
        )

    async def agent_status_update(self, event: Dict[str, Any]) -> None:
        """Pushes run state changes (RUNNING, WAITING_APPROVAL, COMPLETED, FAILED, CANCELLED)."""
        await self.send_json(
            {
                "type": "status_update",
                "status": event.get("status"),
                "error_message": event.get("error_message"),
                "execution_time_seconds": event.get("execution_time_seconds"),
                "tokens_used": event.get("tokens_used"),
            }
        )

    async def agent_run_completed(self, event: Dict[str, Any]) -> None:
        """Emits final output payload when the LangGraph workflow finishes execution."""
        await self.send_json(
            {
                "type": "run_completed",
                "output_result": event.get("output_result"),
                "tokens_used": event.get("tokens_used"),
                "execution_time_seconds": event.get("execution_time_seconds"),
            }
        )

    # ------------------------------------------------------------------
    # Database Helper Operations (Sync-to-Async)
    # ------------------------------------------------------------------

    @database_sync_to_async
    def _verify_run_access(self, run_id: str, user_id: int) -> bool:
        """Validates that the given AgentRun exists and belongs to the specified user."""
        return AgentRun.objects.filter(id=run_id, user_id=user_id).exists()

    @database_sync_to_async
    def _cancel_agent_run(self, run_id: str) -> bool:
        """Marks active AgentRun as CANCELLED in DB."""
        try:
            run = AgentRun.objects.get(id=run_id)
            if run.status in [AgentStatus.RUNNING, AgentStatus.WAITING_APPROVAL, AgentStatus.PENDING]:
                run.status = AgentStatus.CANCELLED
                run.save(update_fields=["status", "completed_at"])
                return True
        except AgentRun.DoesNotExist:
            pass
        return False

    @database_sync_to_async
    def _process_approval_decision(self, approval_id: str, decision: str, notes: str) -> Optional[Dict[str, Any]]:
        """Updates HumanApprovalRequest record in DB according to user input."""
        try:
            approval = HumanApprovalRequest.objects.select_related("run").get(id=approval_id)
            if approval.status != "pending":
                return None

            approval.status = "approved" if decision == "approve" else "rejected"
            approval.reviewed_by = self.user
            approval.rejection_reason = notes if decision == "reject" else ""
            approval.save()

            # Resume or transition agent status
            if decision == "approve":
                approval.run.status = AgentStatus.RUNNING
            else:
                approval.run.status = AgentStatus.FAILED
                approval.run.error_message = f"Execution rejected by user: {notes}"
            
            approval.run.save()

            return {
                "approval_id": str(approval.id),
                "status": approval.status,
                "run_status": approval.run.status,
            }
        except HumanApprovalRequest.DoesNotExist:
            return None

    async def _handle_cancel_run(self) -> None:
        """Triggers execution cancellation for the run."""
        cancelled = await self._cancel_agent_run(self.run_id)
        if cancelled:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "agent_status_update",
                    "status": AgentStatus.CANCELLED,
                    "error_message": "Run cancelled by client over WebSocket.",
                },
            )
        else:
            await self.send_json({"type": "error", "message": "Failed to cancel run (invalid state or run ID)."})

    async def _handle_hitl_decision(self, approval_id: str, decision: str, notes: str) -> None:
        """Processes HITL action and broadcasts state shift."""
        result = await self._process_approval_decision(approval_id, decision, notes)
        if result:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "agent_status_update",
                    "status": result["run_status"],
                },
            )
        else:
            await self.send_json(
                {
                    "type": "error",
                    "message": "Approval request not found or already processed.",
                }
            )