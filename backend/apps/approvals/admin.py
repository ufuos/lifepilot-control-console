"""
Django Admin Configuration for LifePilot Human-in-the-Loop (HITL) Approvals.

Provides administrative interfaces to inspect approval requests and review immutable compliance audit logs.
"""

from django.contrib import admin
from apps.approvals.models import ApprovalRequest, AuditLog


class AuditLogInline(admin.TabularInline):
    """Inline view for audit log history within an approval request admin page."""

    model = AuditLog
    extra = 0
    readonly_fields = ("id", "actor", "action_taken", "payload_snapshot", "notes", "timestamp")
    can_delete = False


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    """Admin configuration for managing and reviewing ApprovalRequest records."""

    list_display = (
        "id",
        "action_type",
        "risk_level",
        "status",
        "run",
        "reviewed_by",
        "created_at",
        "expires_at",
    )
    list_filter = ("status", "risk_level", "created_at", "action_type")
    search_fields = ("id", "action_type", "action_description", "run__id", "thread_id")
    readonly_fields = (
        "id",
        "run",
        "created_at",
        "updated_at",
        "decided_at",
        "thread_id",
        "checkpoint_ns",
    )
    inlines = [AuditLogInline]
    ordering = ("-created_at",)
    fieldsets = (
        (
            "Request Overview",
            {
                "fields": (
                    "id",
                    "run",
                    "status",
                    "risk_level",
                    "action_type",
                    "action_description",
                )
            },
        ),
        (
            "LangGraph Checkpoint Context",
            {
                "fields": ("thread_id", "checkpoint_ns", "proposed_payload"),
                "classes": ("collapse",),
            },
        ),
        (
            "Human Review Details",
            {
                "fields": ("reviewed_by", "rejection_reason", "decided_at", "expires_at"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for inspecting immutable HITL AuditLog entries."""

    list_display = ("id", "approval_request", "actor", "action_taken", "timestamp")
    list_filter = ("action_taken", "timestamp")
    search_fields = ("approval_request__id", "actor__email", "notes")
    readonly_fields = (
        "id",
        "approval_request",
        "actor",
        "action_taken",
        "payload_snapshot",
        "notes",
        "timestamp",
    )
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        """Prevent manually adding audit logs via Django admin interface."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs are immutable and cannot be deleted from admin."""
        return False
