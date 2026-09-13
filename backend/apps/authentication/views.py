"""
API Views for User Authentication & Profile Management.

Provides endpoints for:
- POST /api/v1/auth/register/ (Account Creation)
- POST /api/v1/auth/login/    (Session Login)
- POST /api/v1/auth/logout/   (Session Termination)
- GET/PATCH /api/v1/auth/me/  (Authenticated User Profile)
"""

from django.contrib.auth import login, logout
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import User
from apps.authentication.serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.core.utils import format_success_response


class RegisterView(generics.CreateAPIView):
    """
    Endpoint for creating new user accounts and optional organization setups.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Log the newly registered user into the session automatically
        login(request, user)

        user_data = UserSerializer(user, context={"request": request}).data
        return Response(
            format_success_response(
                data=user_data,
                message="User registered and authenticated successfully.",
                status_code=status.HTTP_201_CREATED,
            ),
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    Endpoint for authenticating an existing user and establishing a session.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        login(request, user)

        user_data = UserSerializer(user, context={"request": request}).data
        return Response(
            format_success_response(
                data=user_data,
                message="Login successful.",
                status_code=status.HTTP_200_OK,
            ),
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    Endpoint for logging out the current user and invalidating the session.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logout(request)
        return Response(
            format_success_response(
                data=None,
                message="Logout successful.",
                status_code=status.HTTP_200_OK,
            ),
            status=status.HTTP_200_OK,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint for viewing and updating the profile of the currently authenticated user.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(
            format_success_response(
                data=serializer.data,
                message="User profile retrieved successfully.",
                status_code=status.HTTP_200_OK,
            )
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            format_success_response(
                data=serializer.data,
                message="User profile updated successfully.",
                status_code=status.HTTP_200_OK,
            )
        )
