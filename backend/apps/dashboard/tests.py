from django.test import TestCase

# Create your tests here."""
Unit and Integration Tests for Dashboard Telemetry, Models, Services, and REST API Endpoints.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.agents.models import AgentThread, AgentExecution, PendingApproval
from apps.integrations.models import Integration
from apps.dashboard.models import DashboardMetricSnapshot, UserDashboardPreference
from apps.dashboard.services import DashboardService
from apps.dashboard.serializers import UserDashboardPreferenceSerializer

User = get_user_model()


class DashboardServiceTestCase(TestCase):
    """
    Tests aggregation logic in DashboardService.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="dashboard_test_user",
            email="testuser@lifepilot.ai",
            password="SecurePassword123!",
        )
        self.user_id = str(self.user.id)

        # Create active and completed agent threads
        self.active_thread = AgentThread.objects.create(
            user_id=self.user_id,
            title="Active Thread 1",
            agent_id="lifepilot_orchestrator",
            status="ACTIVE",
        )
        self.completed_thread = AgentThread.objects.create(
            user_id=self.user_id,
            title="Completed Thread 1",
            agent_id="lifepilot_orchestrator",
            status="COMPLETED",
        )

        # Create pending approval
        self.pending_approval = PendingApproval.objects.create(
            thread=self.active_thread,
            user_id=self.user_id,
            tool_name="aws_ec2_terminate",
            tool_args={"instance_id": "i-1234567890abcdef0"},
            risk_level="HIGH",
            reason="Destructive cloud operation requested.",
            status="PENDING",
        )

        # Create integration records
        self.integration_aws = Integration.objects.create(
            user_id=self.user_id,
            name="AWS Account",
            provider="aws",
            category="CLOUD_INFRASTRUCTURE",
            is_connected=True,
            health_status="HEALTHY",
        )

        # Create recent agent execution records
        self.execution = AgentExecution.objects.create(
            thread=self.active_thread,
            status="SUCCESS",
            executed_tools=["aws_ec2_describe"],
            duration_ms=450,
        )

    def test_get_summary_metrics(self):
        """Verify high-level summary KPIs aggregation."""
        metrics = DashboardService.get_summary_metrics(user_id=self.user_id)

        self.assertEqual(metrics["threads"]["active"], 1)
        self.assertEqual(metrics["threads"]["total"], 2)
        self.assertEqual(metrics["approvals"]["pending"], 1)
        self.assertEqual(metrics["integrations"]["connected_healthy"], 1)
        self.assertEqual(metrics["integrations"]["total"], 1)
        self.assertEqual(metrics["performance_24h"]["total_executions"], 1)
        self.assertEqual(metrics["performance_24h"]["successful_executions"], 1)
        self.assertEqual(metrics["performance_24h"]["success_rate_pct"], 100.0)

    def test_get_recent_active_threads(self):
        """Verify active thread listing limit and structure."""
        threads = DashboardService.get_recent_active_threads(user_id=self.user_id, limit=5)
        self.assertEqual(len(threads), 2)
        self.assertEqual(threads[0]["thread_id"], str(self.completed_thread.thread_id))

    def test_get_pending_approval_queue(self):
        """Verify pending HITL approval queue retrieval."""
        approvals = DashboardService.get_pending_approval_queue(user_id=self.user_id)
        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0]["tool_name"], "aws_ec2_terminate")
        self.assertEqual(approvals[0]["risk_level"], "HIGH")

    def test_get_system_activity_feed(self):
        """Verify chronological system activity feed generation."""
        feed = DashboardService.get_system_activity_feed(user_id=self.user_id, limit=10)
        self.assertEqual(len(feed), 1)
        self.assertEqual(feed[0]["type"], "EXECUTION")
        self.assertEqual(feed[0]["status"], "SUCCESS")


class DashboardSerializersTestCase(TestCase):
    """
    Tests serializer validation rules for user dashboard preferences.
    """

    def test_user_dashboard_preference_serializer_validation(self):
        """Ensure minimum refresh interval threshold is enforced."""
        invalid_data = {
            "auto_refresh_enabled": True,
            "refresh_interval_seconds": 2,  # Invalid: below 5s minimum
            "default_tab": "overview",
        }
        serializer = UserDashboardPreferenceSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("refresh_interval_seconds", serializer.errors)

        valid_data = {
            "auto_refresh_enabled": True,
            "refresh_interval_seconds": 15,
            "default_tab": "overview",
        }
        valid_serializer = UserDashboardPreferenceSerializer(data=valid_data)
        self.assertTrue(valid_serializer.is_valid())


class DashboardAPIViewsTestCase(TestCase):
    """
    Integration tests for Dashboard REST API views.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="api_test_user",
            email="apiuser@lifepilot.ai",
            password="SecurePassword123!",
        )
        self.client.force_authenticate(user=self.user)

    def test_dashboard_summary_endpoint(self):
        """GET /api/dashboard/summary/ should return status HTTP 200 OK."""
        url = reverse("dashboard:summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("threads", response.data)
        self.assertIn("approvals", response.data)
        self.assertIn("integrations", response.data)
        self.assertIn("performance_24h", response.data)

    def test_active_threads_overview_endpoint(self):
        """GET /api/dashboard/threads/ should return active threads list."""
        url = reverse("dashboard:threads-overview")
        response = self.client.get(f"{url}?limit=5")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("threads", response.data)

    def test_pending_approvals_queue_endpoint(self):
        """GET /api/dashboard/approvals/ should return pending approval queue."""
        url = reverse("dashboard:approvals-queue")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("pending_approvals", response.data)

    def test_system_activity_feed_endpoint(self):
        """GET /api/dashboard/activity/ should return system activity feed."""
        url = reverse("dashboard:activity-feed")
        response = self.client.get(f"{url}?limit=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("activity_feed", response.data)

    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests to dashboard APIs should return HTTP 401 Unauthorized."""
        self.client.logout()
        url = reverse("dashboard:summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
