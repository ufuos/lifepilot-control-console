"""
Django Admin Configuration for LifePilot Dashboard Telemetry and User Preferences.
"""

from django.contrib import admin
from apps.dashboard.models import DashboardMetricSnapshot, UserDashboardPreference


@admin.register(DashboardMetricSnapshot)
class DashboardMetricSnapshotAdmin(admin.ModelAdmin):
    """
    Admin layout for historical and cached metric snapshots.
    """
    list_display = (
        "id",
        "user",
        "active_threads_count",
        "pending_approvals_count",
        "healthy_integrations_count",
        "success_rate_pct",
        "created_at",
    )
    list_filter = ("created_at", "user")
    search_fields = ("id", "user__username", "user__email")
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Snapshot Metadata",
            {
                "fields": ("id", "user", "created_at"),
            },
        ),
        (
            "Aggregated Counters",
            {
                "fields": (
                    "active_threads_count",
                    "pending_approvals_count",
                    "connected_integrations_count",
                    "healthy_integrations_count",
                ),
            },
        ),
        (
            "24-Hour Telemetry",
            {
                "fields": (
                    "total_executions_24h",
                    "successful_executions_24h",
                    "failed_executions_24h",
                    "success_rate_pct",
                    "avg_execution_time_ms",
                ),
            },
        ),
        (
            "Raw Payload Data",
            {
                "classes": ("collapse",),
                "fields": ("raw_telemetry_data",),
            },
        ),
    )


@admin.register(UserDashboardPreference)
class UserDashboardPreferenceAdmin(admin.ModelAdmin):
    """
    Admin layout for user dashboard configuration preferences.
    """
    list_display = (
        "id",
        "user",
        "auto_refresh_enabled",
        "refresh_interval_seconds",
        "default_tab",
        "updated_at",
    )
    list_filter = ("auto_refresh_enabled", "default_tab")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (
            "User Settings",
            {
                "fields": ("id", "user"),
            },
        ),
        (
            "Display & Polling Options",
            {
                "fields": (
                    "auto_refresh_enabled",
                    "refresh_interval_seconds",
                    "default_tab",
                    "visible_widgets",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
