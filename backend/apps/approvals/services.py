"""
Service layer for managing Human-in-the-Loop (HITL) workflow resumptions.

Integrates with:
- LangGraph Orchestration Engine (via Command(resume=...))
- Strands SDK Agent Runner
- Django Channels WebSockets notification triggers
"""

import logging
from typing import Any, Dict, Optional
from django.conf import settings
from django.utils import timezone
from langgraph.types import Command

from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.agents.models import AgentRun

logger = logging.getLogger("lifepilot.approvals.services")


def resume_agent_workflow(approval_request: ApprovalRequest) -> Dict[str, Any]:
    """
    Resumes a paused LangGraph workflow or Strands agent step following a human decision.

    Args:
        approval_request: The ApprovalRequest instance containing decision state and thread metadata.

    Returns:
        Dict containing execution summary and state outcome.
    """
    if approval_request.status not in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
        raise ValueError(
            f"Cannot resume workflow for approval '{approval_request.id}' with status '{approval_request.status}'."
        )

    thread_id = approval_request.thread_id
    if not thread_id:
        logger.warning(
            "ApprovalRequest [%s] has no thread_id associated. Unable to resume LangGraph checkpointer.",
            approval_request.id,
        )
        return {"status": "skipped", "reason": "No thread_id provided"}

    agent_run = approval_request.run

    # Formulate payload returned to the interrupted node / tool call
    resume_payload = {
        "approval_id": str(approval_request.id),
        "status": approval_request.status,
        "approved": approval_request.status == ApprovalStatus.APPROVED,
        "action_type": approval_request.action_type,
        "reviewed_by": str(approval_request.reviewed_by.id) if approval_request.reviewed_by else None,
        "rejection_reason": approval_request.rejection_reason,
        "decided_at": approval_request.decided_at.isoformat() if approval_request.decided_at else timezone.now().isoformat(),
    }

    try:
        # 1. Instantiate the compiled graph with persistent checkpointer
        from apps.agents.graph.workflow import get_compiled_graph
        graph = get_compiled_graph()

        # 2. Re-establish thread config for state resumption
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": approval_request.checkpoint_ns or "",
            }
        }

        logger.info(
            "Resuming LangGraph thread [%s] for ApprovalRequest [%s] (Decision: %s)",
            thread_id,
            approval_request.id,
            approval_request.status,
        )

        # 3. Resume graph execution via Command(resume=...)
        # Passing Command(resume=...) unblocks interrupt() in human_approval node
        result = graph.invoke(Command(resume=resume_payload), config=config)

        # 4. Update AgentRun state based on graph response
        if approval_request.status == ApprovalStatus.APPROVED:
            agent_run.status = AgentRun.Status.SUCCESS if not graph.get_state(config).next else AgentRun.Status.RUNNING
        else:
            agent_run.status = AgentRun.Status.FAILED
            agent_run.error_message = f"Execution terminated by user rejection: {approval_request.rejection_reason}"
            agent_run.completed_at = timezone.now()

        agent_run.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

        # 5. Broadcast status update over Django Channels WebSocket if available
        _notify_websocket_listeners(agent_run, approval_request)

        return {
            "status": "success",
            "thread_id": thread_id,
            "run_status": agent_run.status,
            "graph_output": result,
        }

    except Exception as exc:
        logger.exception(
            "Failed to resume LangGraph thread [%s] for ApprovalRequest [%s]: %s",
            thread_id,
            approval_request.id,
            str(exc),
        )
        agent_run.status = AgentRun.Status.FAILED
        agent_run.error_message = f"Error resuming workflow execution: {str(exc)}"
        agent_run.completed_at = timezone.now()
        agent_run.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

        raise RuntimeError(f"Workflow resumption failed: {str(exc)}") from exc


def _notify_websocket_listeners(agent_run: AgentRun, approval_request: ApprovalRequest) -> None:
    """Helper to broadcast real-time status changes to active WebSocket connections."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"agent_run_{agent_run.id}",
                {
                    "type": "approval_updated",
                    "approval_id": str(approval_request.id),
                    "status": approval_request.status,
                    "run_status": agent_run.status,
                },
            )
    except Exception as err:
        logger.debug("WebSocket broadcast skipped or failed: %s", err)