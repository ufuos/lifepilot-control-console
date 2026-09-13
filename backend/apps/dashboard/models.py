"""
Database Models for LifePilot Dashboard Telemetry and User Preferences.

Stores aggregated metrics snapshots for performance caching and customized user
dashboard layouts, refresh intervals, and metric threshold settings.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class DashboardMetricSnapshot(models.Model):
    """
    Stores historical or cached system-wide KPI snapshots to optimize dashboard load times
    and enable trend analysis over 24-hour, 7-day, or 30-day windows.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="metric_snapshots",
        help_text="The user associated with this metric snapshot.",
    )
    
    # Aggregated KPI counters
    active_threads_count = models.IntegerField(default=0)
    pending_approvals_count = models.IntegerField(default=0)
    connected_integrations_count = models.IntegerField(default=0)
    healthy_integrations_count = models.IntegerField(default=0)
    
    # 24-hour execution performance indicators
    total_executions_24h = models.IntegerField(default=0)
    successful_executions_24h = models.IntegerField(default=0)
    failed_executions_24h = models.IntegerField(default=0)
    success_rate_pct = models.FloatField(default=100.0)
    avg_execution_time_ms = models.FloatField(default=0.0)

    # Detailed metrics breakdown payload (JSON)
    raw_telemetry_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed JSON dump of aggregated telemetry counters.",
    )

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "dashboard_metric_snapshots"
        ordering = ["-created_at"]
        verbose_name = "Dashboard Metric Snapshot"
        verbose_name_plural = "Dashboard Metric Snapshots"

    def __str__(self) -> str:
        return f"Snapshot {self.id} for User {self.user_id} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class UserDashboardPreference(models.Model):
    """
    Stores individual user interface customization settings for the LifePilot Control Console.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_preferences",
    )

    # Dashboard polling and layout options
    auto_refresh_enabled = models.BooleanField(default=True)
    refresh_interval_seconds = models.IntegerField(
        default=30,
        help_text="Telemetry auto-refresh interval in seconds (e.g., 5, 15, 30, 60).",
    )
    
    # Custom display settings (e.g., active widgets, default view tab)
    default_tab = models.CharField(
        max_length=50,
        default="overview",
        help_text="Default view tab on launch (e.g., 'overview', 'approvals', 'integrations').",
    )
    visible_widgets = models.JSONField(
        default=list,
        blank=True,
        help_text="List of enabled widget identifiers on the dashboard view.",
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dashboard_user_preferences"
        verbose_name = "User Dashboard Preference"
        verbose_name_plural = "User Dashboard Preferences"

    def __str__(self) -> str:
        return f"Preferences for User {self.user_id}"