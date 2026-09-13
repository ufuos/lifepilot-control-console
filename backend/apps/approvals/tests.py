"""
Integration & Unit Tests for LifePilot Human-in-the-Loop (HITL) Approvals.

Tests cover:
- Approval request API listing and retrieval
- Actioning decisions (Approve and Reject) via submit_decision action
- Expiration validation checks
- Audit log entry creation upon decision submission
"""

from unittest.mock import patch
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from apps.agents.models import AgentRun, AgentDefinition
from apps.approvals.models import ActionRiskLevel, ApprovalRequest, ApprovalStatus, AuditLog

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        email="operator@lifepilot.ai",
        password="securepassword123",
        username="operator",
    )


@pytest.fixture
def agent_definition(db, test_user):
    return AgentDefinition.objects.create(
        name="AWS Infrastructure Bot",
        slug="aws-infra-bot",
        user=test_user,
        description="Manages AWS operations with HITL gates.",
    )


@pytest.fixture
def agent_run(db, test_user, agent_definition):
    return AgentRun.objects.create(
        agent_definition=agent_definition,
        user=test_user,
        status="paused",
    )


@pytest.fixture
def approval_request(db, agent_run):
    return ApprovalRequest.objects.create(
        run=agent_run,
        risk_level=ActionRiskLevel.HIGH,
        action_type="aws:terminate_instance",
        action_description="Attempting to terminate EC2 instance i-0123456789abcdef0",
        proposed_payload={"instance_id": "i-0123456789abcdef0", "region": "us-east-1"},
        thread_id="langgraph_thread_test_1001",
        checkpoint_ns="aws_cleanup",
        status=ApprovalStatus.PENDING,
    )


@pytest.mark.django_db
class TestApprovalRequestAPI:
    """Test suite for DRF endpoints in approvals application."""

    def test_list_approvals_unauthenticated(self, api_client):
        url = reverse("approvals:approval-request-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_approvals_authenticated(self, api_client, test_user, approval_request):
        api_client.force_authenticate(user=test_user)
        url = reverse("approvals:approval-request-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == str(approval_request.id)

    def test_pending_count_endpoint(self, api_client, test_user, approval_request):
        api_client.force_authenticate(user=test_user)
        url = reverse("approvals:approval-request-pending-count")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["pending_count"] == 1

    @patch("apps.approvals.services.resume_agent_workflow")
    def test_approve_request_success(self, mock_resume, api_client, test_user, approval_request):
        mock_resume.return_value = {"status": "success", "thread_id": approval_request.thread_id}

        api_client.force_authenticate(user=test_user)
        url = reverse("approvals:approval-request-submit-decision", kwargs={"pk": approval_request.id})
        payload = {"decision": "approved", "notes": "Approved after reviewing resource metrics."}
        
        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        approval_request.refresh_from_db()
        assert approval_request.status == ApprovalStatus.APPROVED
        assert approval_request.reviewed_by == test_user
        assert AuditLog.objects.filter(approval_request=approval_request, action_taken="APPROVED").exists()
        mock_resume.assert_called_once_with(approval_request=approval_request)

    @patch("apps.approvals.services.resume_agent_workflow")
    def test_reject_request_success(self, mock_resume, api_client, test_user, approval_request):
        mock_resume.return_value = {"status": "success", "thread_id": approval_request.thread_id}

        api_client.force_authenticate(user=test_user)
        url = reverse("approvals:approval-request-submit-decision", kwargs={"pk": approval_request.id})
        payload = {"decision": "rejected", "notes": "Action rejected due to upcoming production freeze."}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        approval_request.refresh_from_db()
        assert approval_request.status == ApprovalStatus.REJECTED
        assert approval_request.rejection_reason == "Action rejected due to upcoming production freeze."
        assert AuditLog.objects.filter(approval_request=approval_request, action_taken="REJECTED").exists()

    def test_cannot_decision_expired_request(self, api_client, test_user, approval_request):
        approval_request.expires_at = timezone.now() - timezone.timedelta(minutes=5)
        approval_request.save()

        api_client.force_authenticate(user=test_user)
        url = reverse("approvals:approval-request-submit-decision", kwargs={"pk": approval_request.id})
        payload = {"decision": "approved"}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        approval_request.refresh_from_db()
        assert approval_request.status == ApprovalStatus.EXPIRED
