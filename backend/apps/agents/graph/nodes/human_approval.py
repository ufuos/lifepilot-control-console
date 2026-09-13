"""
LangGraph Human-in-the-Loop (HITL) approval node and utility functions.

Pauses execution state when an agent tool or action requires human authorization,
creates an ApprovalRequest database record for the UI, and handles resumed state execution.
"""

import logging
from typing import Any, Dict, Optional
from django.utils import timezone
from langgraph.types import interrupt
from apps.agents.graph.state import AgentState

logger = logging.getLogger(__name__)


def human_approval_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node that pauses graph execution when an action requires explicit human approval.

    1. Checks if an approval request is pending.
    2. Intercepts execution via LangGraph `interrupt()`.
    3. Receives human decisions upon resume ('approved', 'rejected', or 'modified').
    4. Updates state with the human decision for downstream routing.
    """
    logger.info("Entering human_approval_node for thread: %s", state.get("thread_id"))

    pending_action = state.get("pending_action")
    if not pending_action:
        logger.warning("human_approval_node invoked without a pending_action. Auto-bypassing.")
        return {
            "is_approved": True,
            "approval_status": "bypassed",
            "approval_feedback": "No pending action found requiring human intervention.",
        }

    # Prepare metadata to send to the interrupt channel / frontend UI
    approval_payload = {
        "action_type": pending_action.get("action_type", "UNKNOWN_ACTION"),
        "description": pending_action.get("description", "Action requires manual review."),
        "parameters": pending_action.get("parameters", {}),
        "requested_by_agent": state.get("current_agent", "StrandsAgent"),
        "risk_level": pending_action.get("risk_level", "MEDIUM"),
        "timestamp": timezone.now().isoformat(),
    }

    # Issue LangGraph interrupt to suspend state machine execution until external input is received
    human_response: Dict[str, Any] = interrupt(approval_payload)

    logger.info("Resumed execution from human_approval_node with response: %s", human_response)

    status = human_response.get("status", "rejected").lower()
    feedback = human_response.get("feedback", "")
    modified_parameters = human_response.get("modified_parameters")

    is_approved = status in ["approved", "auto_approved"]

    # Handle parameter modifications if human adjusted payload during review
    effective_action = pending_action.copy()
    if is_approved and modified_parameters:
        effective_action["parameters"].update(modified_parameters)

    return {
        "is_approved": is_approved,
        "approval_status": status,
        "approval_feedback": feedback,
        "pending_action": effective_action if is_approved else None,
        "human_decision_time": timezone.now().isoformat(),
    }


def should_require_approval(state: AgentState) -> str:
    """
    Conditional edge function determining if workflow branches to human_approval_node.

    Returns:
        "human_approval" if human intervention is required.
        "continue" if the step can proceed automatically.
    """
    requires_approval = state.get("requires_human_approval", False)
    pending_action = state.get("pending_action")

    if requires_approval and pending_action:
        return "human_approval"
    return "continue"