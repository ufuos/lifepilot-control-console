"""
Unit and API Integration Tests for Authentication endpoints and models.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.authentication.models import Organization, UserRole

User = get_user_model()


class AuthenticationTests(APITestCase):
    """Suite testing registration, authentication, and user profile management."""

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Org",
            slug="test-org",
        )
        self.user_password = "SecurePassword123!"
        self.user = User.objects.create_user(
            email="operator@lifepilot.ai",
            password=self.user_password,
            first_name="Pilot",
            last_name="Operator",
            role=UserRole.OPERATOR,
            organization=self.organization,
        )

        self.register_url = reverse("authentication:register")
        self.login_url = reverse("authentication:login")
        self.logout_url = reverse("authentication:logout")
        self.profile_url = reverse("authentication:user-profile")

    def test_user_creation_and_str(self):
        """Verify user creation with custom fields and string representation."""
        self.assertEqual(self.user.email, "operator@lifepilot.ai")
        self.assertEqual(self.user.role, UserRole.OPERATOR)
        self.assertEqual(str(self.user), "operator@lifepilot.ai (OPERATOR)")
        self.assertEqual(self.user.full_name, "Pilot Operator")

    def test_user_registration_success(self):
        """Verify new user registration via API endpoint."""
        payload = {
            "email": "newuser@lifepilot.ai",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "first_name": "New",
            "last_name": "User",
            "organization_name": "New Pilot Org",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], "newuser@lifepilot.ai")
        self.assertTrue(User.objects.filter(email="newuser@lifepilot.ai").exists())

    def test_user_login_success(self):
        """Verify successful user authentication via login endpoint."""
        payload = {
            "email": "operator@lifepilot.ai",
            "password": self.user_password,
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], "operator@lifepilot.ai")

    def test_user_login_invalid_credentials(self):
        """Verify login failure with incorrect password."""
        payload = {
            "email": "operator@lifepilot.ai",
            "password": "WrongPassword!",
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success", False))

    def test_profile_retrieval_authenticated(self):
        """Verify profile retrieval for authenticated users."""
        self.client.force_login(self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], self.user.email)

    def test_profile_update(self):
        """Verify updating user details via profile endpoint."""
        self.client.force_login(self.user)
        payload = {"first_name": "UpdatedName", "phone_number": "+1234567890"}
        response = self.client.patch(self.profile_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "UpdatedName")
        self.assertEqual(self.user.phone_number, "+1234567890")
