"""
URL Configuration for LifePilot Approvals REST API endpoints.

Exposes endpoints under /api/v1/approvals/:
- GET  /requests/              - List approval requests with filtering
- GET  /requests/<id>/         - Retrieve approval request details & audit logs
- POST /requests/<id>/decision/ - Submit approval or rejection decision
- GET  /requests/pending-count/ - Get total count of pending reviews
- GET  /audit-logs/            - List immutable audit logs for compliance
- GET  /audit-logs/<id>/       - Retrieve specific audit log record
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.approvals.views import ApprovalRequestViewSet, AuditLogViewSet

app_name = "approvals"

router = DefaultRouter()
router.register(r"requests", ApprovalRequestViewSet, basename="approval-request")
router.register(r"audit-logs", AuditLogViewSet, basename="approval-audit-log")

urlpatterns = [
    path("", include(router.urls)),
]