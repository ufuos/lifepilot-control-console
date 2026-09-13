"""
Dashboard Analytics & Telemetry Aggregation Service.

Compiles system-wide health indicators, agent execution statistics,
pending Human-in-the-Loop (HITL) approval queues, and integration connectivity states.
"""

import logging
from typing import Any, Dict, List
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q, Avg

from apps.agents.models import AgentThread, AgentExecution, PendingApproval
from apps.integrations.models import Integration

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service responsible for building unified status payloads for the LifePilot Control Console.
    """

    @classmethod
    def get_summary_metrics(cls, user_id: str) -> Dict[str, Any]:
        """
        Calculates high-level KPI cards and summary counters for the dashboard header.
        """
        now = timezone.now()
        last_24h = now - timedelta(hours=24)

        # Thread statistics
        active_threads = AgentThread.objects.filter(
            user_id=user_id, status="ACTIVE"
        ).count()
        total_threads = AgentThread.objects.filter(user_id=user_id).count()

        # Approval statistics
        pending_approvals = PendingApproval.objects.filter(
            user_id=user_id, status="PENDING"
        ).count()
        approvals_24h = PendingApproval.objects.filter(
            user_id=user_id,
            updated_at__gte=last_24h,
            status__in=["APPROVED", "REJECTED"],
        ).aggregate(
            approved=Count("id", filter=Q(status="APPROVED")),
            rejected=Count("id", filter=Q(status="REJECTED")),
        )

        # Integration status breakdown
        integrations = Integration.objects.filter(user_id=user_id)
        total_integrations = integrations.count()
        healthy_integrations = integrations.filter(
            is_connected=True, health_status="HEALTHY"
        ).count()

        # Agent execution stats in last 24 hours
        recent_executions = AgentExecution.objects.filter(
            thread__user_id=user_id, created_at__gte=last_24h
        )
        total_runs = recent_executions.count()
        successful_runs = recent_executions.filter(status="SUCCESS").count()
        failed_runs = recent_executions.filter(status="FAILED").count()

        success_rate = (
            round((successful_runs / total_runs) * 100, 1) if total_runs > 0 else 100.0
        )

        return {
            "threads": {
                "active": active_threads,
                "total": total_threads,
            },
            "approvals": {
                "pending": pending_approvals,
                "approved_24h": approvals_24h["approved"] or 0,
                "rejected_24h": approvals_24h["rejected"] or 0,
            },
            "integrations": {
                "connected_healthy": healthy_integrations,
                "total": total_integrations,
            },
            "performance_24h": {
                "total_executions": total_runs,
                "successful_executions": successful_runs,
                "failed_executions": failed_runs,
                "success_rate_pct": success_rate,
            },
        }

    @classmethod
    def get_recent_active_threads(
        cls, user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent active agent threads with step counts and last activity timestamps.
        """
        threads = AgentThread.objects.filter(user_id=user_id).order_by(
            "-updated_at"
        )[:limit]

        return [
            {
                "thread_id": str(thread.thread_id),
                "title": thread.title or "Untitled Session",
                "agent_id": thread.agent_id,
                "status": thread.status,
                "current_step": thread.current_step,
                "has_pending_approval": thread.has_pending_approval,
                "last_activity": thread.updated_at.isoformat(),
                "created_at": thread.created_at.isoformat(),
            }
            for thread in threads
        ]

    @classmethod
    def get_pending_approval_queue(cls, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all urgent pending HITL approval requests requiring user intervention.
        """
        approvals = PendingApproval.objects.filter(
            user_id=user_id, status="PENDING"
        ).order_by("-created_at")

        return [
            {
                "approval_id": str(appr.approval_id),
                "thread_id": str(appr.thread.thread_id),
                "tool_name": appr.tool_name,
                "tool_args": appr.tool_args,
                "risk_level": appr.risk_level,
                "reason": appr.reason,
                "requested_at": appr.created_at.isoformat(),
            }
            for appr in approvals
        ]

    @classmethod
    def get_system_activity_feed(
        cls, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Combines recent agent executions and approval decisions into a chronological activity stream.
        """
        recent_executions = (
            AgentExecution.objects.filter(thread__user_id=user_id)
            .select_related("thread")
            .order_by("-created_at")[:limit]
        )

        feed = []
        for exec_item in recent_executions:
            feed.append(
                {
                    "id": str(exec_item.id),
                    "type": "EXECUTION",
                    "thread_id": str(exec_item.thread.thread_id),
                    "title": f"Executed tool '{exec_item.tool_name}'",
                    "status": exec_item.status,
                    "timestamp": exec_item.created_at.isoformat(),
                    "details": {
                        "execution_time_ms": exec_item.duration_ms,
                        "error": exec_item.error_message,
                    },
                }
            )

        # Sort merged activity chronologically
        feed.sort(key=lambda item: item["timestamp"], reverse=True)
        return feed[:limit]