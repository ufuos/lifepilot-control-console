"""
API Views for LifePilot Control Console Dashboard & Agent Engine Integration.

Provides endpoints for telemetry analytics summaries, LangGraph workflow execution,
Human-in-the-Loop (HITL) authorization overrides, and execution thread state tracking.
"""

import logging
import uuid
from typing import Any, Dict

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from langchain_core.messages import HumanMessage
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agents.graph.workflow import lifepilot_graph
from apps.agents.models import AgentExecution, AgentRun, AgentThread, PendingApproval
from apps.agents.serializers import (
    AgentExecutionSerializer,
    AgentExecutionTriggerSerializer,
    HITLDecisionSerializer,
    PendingApprovalSerializer,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Dashboard Telemetry & Summary Views
# ==============================================================================

class DashboardSummaryView(APIView):
    """
    API Endpoint providing high-level metrics and system telemetry summaries.

    GET /api/dashboard/summary/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user

        # Aggregate run statistics
        user_runs = AgentRun.objects.filter(user=user) if hasattr(AgentRun, "user") else AgentRun.objects.all()
        total_runs = user_runs.count()
        successful_runs = user_runs.filter(status="SUCCESS").count()
        failed_runs = user_runs.filter(status="FAILED").count()

        tokens_consumed = user_runs.aggregate(total_tokens=Sum("tokens_used"))["total_tokens"] or 0
        avg_latency = user_runs.aggregate(avg_time=Avg("execution_time_seconds"))["avg_time"] or 0.0

        # Pending HITL approvals
        pending_approvals_count = PendingApproval.objects.filter(
            status="PENDING"
        ).count() if hasattr(PendingApproval, "status") else 0

        # Active threads count
        active_threads_count = AgentThread.objects.filter(
            status="ACTIVE"
        ).count() if hasattr(AgentThread, "status") else 0

        summary_payload = {
            "telemetry": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": round((successful_runs / total_runs * 100), 2) if total_runs > 0 else 100.0,
                "total_tokens_consumed": tokens_consumed,
                "average_execution_latency_sec": round(avg_latency, 2),
            },
            "control_plane": {
                "active_threads": active_threads_count,
                "pending_hitl_approvals": pending_approvals_count,
            },
            "system_status": "HEALTHY",
            "timestamp": timezone.now().isoformat(),
        }

        return Response(summary_payload, status=status.HTTP_200_OK)


class DashboardMetricsView(APIView):
    """
    API Endpoint returning detailed agent performance telemetry and metrics breakdown.

    GET /api/dashboard/metrics/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        total_executions = AgentExecution.objects.count() if hasattr(AgentExecution, "objects") else 0
        total_runs = AgentRun.objects.count() if hasattr(AgentRun, "objects") else 0

        metrics = {
            "total_executions": total_executions,
            "total_agent_runs": total_runs,
            "tokens_breakdown": AgentRun.objects.aggregate(
                total_tokens=Sum("tokens_used"),
                avg_tokens=Avg("tokens_used")
            ) if hasattr(AgentRun, "objects") else {"total_tokens": 0, "avg_tokens": 0},
            "retrieved_at": timezone.now().isoformat(),
        }

        return Response(metrics, status=status.HTTP_200_OK)


class DashboardRecentExecutionsView(APIView):
    """
    API Endpoint providing recent execution logs for dashboard display.

    GET /api/dashboard/recent-executions/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        recent_runs = AgentRun.objects.order_by("-created_at")[:10]
        serializer = AgentExecutionSerializer(recent_runs, many=True)
        return Response({"recent_executions": serializer.data}, status=status.HTTP_200_OK)


class ActiveThreadsOverviewView(APIView):
    """
    API Endpoint listing active agent execution threads for operator oversight.

    GET /api/dashboard/active-threads/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        user_id = str(request.user.id)
        active_threads = AgentThread.objects.filter(
            user_id=user_id, status="ACTIVE"
        ).order_by("-updated_at")

        threads_data = [
            {
                "thread_id": thread.thread_id,
                "title": thread.title,
                "agent_id": getattr(thread, "agent_id", "default_lifepilot_agent"),
                "has_pending_approval": thread.has_pending_approval,
                "status": thread.status,
                "created_at": thread.created_at.isoformat() if hasattr(thread, "created_at") else None,
                "updated_at": thread.updated_at.isoformat() if hasattr(thread, "updated_at") else None,
            }
            for thread in active_threads
        ]

        return Response(
            {"active_threads": threads_data, "count": len(threads_data)},
            status=status.HTTP_200_OK,
        )


class PendingApprovalsQueueView(APIView):
    """
    API Endpoint providing a queue of all pending Human-in-the-Loop approvals.

    GET /api/dashboard/pending-approvals/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        user_id = str(request.user.id)
        pending_approvals = PendingApproval.objects.filter(
            user_id=user_id, status="PENDING"
        ).order_by("-created_at") if hasattr(PendingApproval, "user_id") else PendingApproval.objects.filter(status="PENDING")

        serializer = PendingApprovalSerializer(pending_approvals, many=True)
        return Response(
            {"pending_approvals": serializer.data, "count": pending_approvals.count()},
            status=status.HTTP_200_OK,
        )


class SystemActivityFeedView(APIView):
    """
    API Endpoint providing a unified activity feed of system events and agent executions.

    GET /api/dashboard/activity-feed/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        user_id = str(request.user.id)
        recent_executions = AgentExecution.objects.select_related("thread").order_by("-created_at")[:20]

        activity_feed = [
            {
                "id": str(execution.id),
                "thread_id": execution.thread.thread_id if execution.thread else None,
                "status": execution.status,
                "error_message": execution.error_message,
                "executed_tools": execution.executed_tools,
                "created_at": execution.created_at.isoformat() if hasattr(execution, "created_at") else None,
            }
            for execution in recent_executions
        ]

        return Response(
            {"activities": activity_feed, "count": len(activity_feed)},
            status=status.HTTP_200_OK,
        )


# ==============================================================================
# Agent Workflow & Human-in-the-Loop Views
# ==============================================================================

class AgentGraphExecutionView(APIView):
    """
    API Endpoint to initiate or resume a LangGraph workflow execution thread.

    POST /api/agents/graph/execute/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = AgentExecutionTriggerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = str(request.user.id)
        data = serializer.validated_data
        thread_id = data.get("thread_id") or f"thread-{uuid.uuid4().hex[:12]}"
        prompt = data.get("prompt")
        agent_id = data.get("agent_id", "default_lifepilot_agent")

        logger.info(
            "Initiating agent graph execution for user: %s, thread_id: %s",
            user_id,
            thread_id,
        )

        # Get or create local DB Thread tracker
        thread_obj, _ = AgentThread.objects.get_or_create(
            thread_id=thread_id,
            user_id=user_id,
            defaults={"title": prompt[:50] if prompt else "New Execution Session", "agent_id": agent_id},
        )

        # Build initial LangGraph state inputs
        input_state: Dict[str, Any] = {
            "messages": [HumanMessage(content=prompt)] if prompt else [],
            "user_id": user_id,
            "thread_id": thread_id,
            "agent_id": agent_id,
            "session_metadata": data.get("session_metadata", {}),
        }

        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Execute LangGraph engine up to terminal state or HITL interrupt
            result_state = lifepilot_graph.invoke(input_state, config=config)

            # Check if execution paused for HITL approval
            pending_appr = result_state.get("pending_approval")
            if pending_appr and not result_state.get("approval_granted"):
                approval_id = pending_appr.get("approval_id")

                # Record pending approval in database
                PendingApproval.objects.update_or_create(
                    approval_id=approval_id,
                    defaults={
                        "thread": thread_obj,
                        "user_id": user_id,
                        "tool_name": pending_appr.get("tool_name"),
                        "tool_args": pending_appr.get("tool_args", {}),
                        "risk_level": pending_appr.get("risk_level", "HIGH"),
                        "reason": pending_appr.get("reason", ""),
                        "status": "PENDING",
                    },
                )

                thread_obj.has_pending_approval = True
                thread_obj.save(update_fields=["has_pending_approval", "updated_at"])

                return Response(
                    {
                        "thread_id": thread_id,
                        "status": "PAUSED_FOR_APPROVAL",
                        "pending_approval": pending_appr,
                        "message": "Workflow execution paused pending Human-in-the-Loop authorization.",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            # Record completed execution record
            AgentExecution.objects.create(
                thread=thread_obj,
                status="FAILED" if result_state.get("error") else "SUCCESS",
                error_message=result_state.get("error"),
                executed_tools=result_state.get("executed_tools", []),
            )

            thread_obj.has_pending_approval = False
            thread_obj.status = "COMPLETED" if result_state.get("is_complete") else "ACTIVE"
            thread_obj.save(update_fields=["has_pending_approval", "status", "updated_at"])

            return Response(
                {
                    "thread_id": thread_id,
                    "status": "COMPLETED" if result_state.get("is_complete") else "ACTIVE",
                    "executed_tools": result_state.get("executed_tools", []),
                    "messages": [msg.content for msg in result_state.get("messages", []) if hasattr(msg, "content")],
                    "error": result_state.get("error"),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.error("Error running LangGraph for thread %s: %s", thread_id, str(exc), exc_info=True)
            return Response(
                {"error": f"Failed to execute workflow: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class HITLApprovalDecisionView(APIView):
    """
    API Endpoint to approve or reject a pending Human-in-the-Loop tool execution.

    POST /api/agents/approvals/decide/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = HITLDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = str(request.user.id)
        approval_id = serializer.validated_data["approval_id"]
        decision = serializer.validated_data["decision"].upper()  # 'APPROVED' or 'REJECTED'

        try:
            approval_obj = PendingApproval.objects.select_related("thread").get(
                approval_id=approval_id, user_id=user_id, status="PENDING"
            )
        except PendingApproval.DoesNotExist:
            return Response(
                {"error": "Pending approval request not found or already processed."},
                status=status.HTTP_404_NOT_FOUND,
            )

        thread_obj = approval_obj.thread
        thread_id = str(thread_obj.thread_id)

        # Update database approval status
        approval_obj.status = decision
        approval_obj.decided_at = timezone.now()
        approval_obj.save(update_fields=["status", "decided_at"])

        thread_obj.has_pending_approval = False
        thread_obj.save(update_fields=["has_pending_approval", "updated_at"])

        config = {"configurable": {"thread_id": thread_id}}

        if decision == "APPROVED":
            logger.info("HITL Approval GRANTED for thread %s (Approval: %s)", thread_id, approval_id)

            # Resume LangGraph execution with updated state
            resume_state = {
                "approval_granted": True,
                "pending_approval": None,
            }

            try:
                result_state = lifepilot_graph.invoke(resume_state, config=config)
                return Response(
                    {
                        "approval_id": approval_id,
                        "thread_id": thread_id,
                        "status": "RESUMED_AND_EXECUTED",
                        "executed_tools": result_state.get("executed_tools", []),
                        "is_complete": result_state.get("is_complete", False),
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception as exc:
                logger.error("Failed to resume execution after approval for thread %s: %s", thread_id, str(exc))
                return Response(
                    {"error": f"Failed to resume execution: {str(exc)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        else:
            logger.warning("HITL Approval REJECTED for thread %s (Approval: %s)", thread_id, approval_id)

            # Resume LangGraph execution with rejection signal
            rejection_state = {
                "approval_granted": False,
                "error": "Human operator rejected the execution of this action.",
                "is_complete": True,
            }
            lifepilot_graph.invoke(rejection_state, config=config)

            return Response(
                {
                    "approval_id": approval_id,
                    "thread_id": thread_id,
                    "status": "REJECTED",
                    "message": "Execution canceled per human operator instruction.",
                },
                status=status.HTTP_200_OK,
            )


class AgentThreadStateView(APIView):
    """
    API Endpoint to fetch active checkpoint state for a specific thread.

    GET /api/agents/threads/<thread_id>/state/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request, thread_id: str) -> Response:
        user_id = str(request.user.id)

        try:
            thread_obj = AgentThread.objects.get(thread_id=thread_id, user_id=user_id)
        except AgentThread.DoesNotExist:
            return Response({"error": "Thread not found."}, status=status.HTTP_404_NOT_FOUND)

        config = {"configurable": {"thread_id": thread_id}}
        current_state = lifepilot_graph.get_state(config)

        return Response(
            {
                "thread_id": thread_id,
                "title": thread_obj.title,
                "status": thread_obj.status,
                "has_pending_approval": thread_obj.has_pending_approval,
                "next_nodes": current_state.next if current_state else [],
                "values": current_state.values if current_state else {},
                "updated_at": thread_obj.updated_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )