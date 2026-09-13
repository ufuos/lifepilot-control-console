"""
Serializers for LifePilot Dashboard Telemetry and User Preferences.

Provides data validation and serialization for metric snapshots, preference settings,
KPI summaries, and unified activity feed items.
"""

from rest_framework import serializers
from apps.dashboard.models import DashboardMetricSnapshot, UserDashboardPreference


class DashboardMetricSnapshotSerializer(serializers.ModelSerializer):
    """
    Serializer for historical/cached system-wide KPI metric snapshots.
    """
    user_id = serializers.UUIDField(source="user.id", read_only=True)

    class Meta:
        model = DashboardMetricSnapshot
        fields = [
            "id",
            "user_id",
            "active_threads_count",
            "pending_approvals_count",
            "connected_integrations_count",
            "healthy_integrations_count",
            "total_executions_24h",
            "successful_executions_24h",
            "failed_executions_24h",
            "success_rate_pct",
            "avg_execution_time_ms",
            "raw_telemetry_data",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UserDashboardPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for user dashboard configuration settings (polling intervals, active widgets).
    """
    user_id = serializers.UUIDField(source="user.id", read_only=True)

    class Meta:
        model = UserDashboardPreference
        fields = [
            "id",
            "user_id",
            "auto_refresh_enabled",
            "refresh_interval_seconds",
            "default_tab",
            "visible_widgets",
            "updated_at",
            "created_at",
        ]
        read_only_fields = ["id", "updated_at", "created_at"]

    def validate_refresh_interval_seconds(self, value: int) -> int:
        """
        Enforces a minimum refresh interval threshold to prevent system overload.
        """
        if value < 5:
            raise serializers.ValidationError("Refresh interval must be at least 5 seconds.")
        return value


class ThreadSummarySerializer(serializers.Serializer):
    """
    Serializer for active thread counters.
    """
    active = serializers.IntegerField(min_value=0)
    total = serializers.IntegerField(min_value=0)


class ApprovalSummarySerializer(serializers.Serializer):
    """
    Serializer for pending and 24-hour approval statistics.
    """
    pending = serializers.IntegerField(min_value=0)
    approved_24h = serializers.IntegerField(min_value=0)
    rejected_24h = serializers.IntegerField(min_value=0)


class IntegrationSummarySerializer(serializers.Serializer):
    """
    Serializer for integration connection health metrics.
    """
    connected_healthy = serializers.IntegerField(min_value=0)
    total = serializers.IntegerField(min_value=0)


class Performance24hSerializer(serializers.Serializer):
    """
    Serializer for 24-hour agent execution telemetry.
    """
    total_executions = serializers.IntegerField(min_value=0)
    successful_executions = serializers.IntegerField(min_value=0)
    failed_executions = serializers.IntegerField(min_value=0)
    success_rate_pct = serializers.FloatField(min_value=0.0, max_value=100.0)


class DashboardSummaryResponseSerializer(serializers.Serializer):
    """
    Serializer representing the top-level KPI summary object returned by `/api/dashboard/summary/`.
    """
    threads = ThreadSummarySerializer()
    approvals = ApprovalSummarySerializer()
    integrations = IntegrationSummarySerializer()
    performance_24h = Performance24hSerializer()


class ActivityFeedItemSerializer(serializers.Serializer):
    """
    Serializer for individual items in the system activity stream.
    """
    id = serializers.CharField()
    type = serializers.CharField()
    thread_id = serializers.CharField()
    title = serializers.CharField()
    status = serializers.CharField()
    timestamp = serializers.CharField()
    details = serializers.DictField(required=False, default=dict)