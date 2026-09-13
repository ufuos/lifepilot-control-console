"""
URL Routing Configuration for LifePilot Dashboard Telemetry and Analytics Endpoints.

Maps REST endpoints for metric summaries, active thread tracking,
pending Human-in-the-Loop (HITL) approval queues, and chronological activity feeds.
"""

from django.urls import path
from apps.dashboard.views import (
    DashboardSummaryView,
    ActiveThreadsOverviewView,
    PendingApprovalsQueueView,
    SystemActivityFeedView,
)

app_name = "dashboard"

urlpatterns = [
    # Retrieves overall system KPIs and 24-hour performance counters
    path(
        "summary/",
        DashboardSummaryView.as_view(),
        name="summary",
    ),
    # Returns recent active agent threads with status and step metrics
    path(
        "threads/",
        ActiveThreadsOverviewView.as_view(),
        name="threads-overview",
    ),
    # Lists urgent pending Human-in-the-Loop authorization requests
    path(
        "approvals/",
        PendingApprovalsQueueView.as_view(),
        name="approvals-queue",
    ),
    # Provides a merged chronological feed of agent executions and system events
    path(
        "activity/",
        SystemActivityFeedView.as_view(),
        name="activity-feed",
    ),
]