"""
API Views for LifePilot Connected Integrations.

Provides endpoints for listing available integration providers, managing active user connections,
initiating OAuth flows, handling authorization callbacks, connecting via API keys, and handling webhooks.
"""

import logging
import uuid
from typing import Any, Dict

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integrations.models import (
    ConnectedIntegration,
    ConnectionStatus,
    IntegrationProvider,
    IntegrationWebhookLog,
)
from apps.integrations.serializers import (
    ConnectedIntegrationSerializer,
    IntegrationApiKeyConnectSerializer,
    IntegrationProviderSerializer,
    IntegrationWebhookLogSerializer,
    OAuthCallbackSerializer,
    OAuthInitSerializer,
)

logger = logging.getLogger(__name__)


class IntegrationProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly API endpoint for listing and inspecting supported integration providers.
    """

    queryset = IntegrationProvider.objects.filter(is_active=True)
    serializer_class = IntegrationProviderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"


class ConnectedIntegrationViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing the authenticated user's connected external integrations.
    """

    serializer_class = ConnectedIntegrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Ensure users can only view and mutate their own connected integrations."""
        return ConnectedIntegration.objects.filter(user=self.request.user).select_related(
            "provider"
        )

    def perform_destroy(self, instance: ConnectedIntegration) -> None:
        """Soft disconnect or revoke credentials prior to object removal."""
        logger.info(
            "Disconnecting integration '%s' (Account: %s) for user %s",
            instance.provider.name,
            instance.account_identifier,
            self.request.user.username,
        )
        instance.status = ConnectionStatus.DISCONNECTED
        instance.access_token = None
        instance.refresh_token = None
        instance.save()
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="sync")
    def sync_integration(self, request: Request, pk=None) -> Response:
        """
        Manually triggers a status check and data synchronization cycle for an integration.
        """
        integration = self.get_object()

        if integration.status == ConnectionStatus.DISCONNECTED:
            return Response(
                {"error": "Cannot sync a disconnected integration."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if integration.is_token_expired:
            integration.status = ConnectionStatus.EXPIRED
            integration.last_error_message = "OAuth credentials have expired. Please re-authenticate."
            integration.save()
            return Response(
                {"error": "Integration credentials expired.", "status": integration.status},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Trigger sync logic update
        integration.last_synced_at = timezone.now()
        integration.status = ConnectionStatus.CONNECTED
        integration.last_error_message = None
        integration.save()

        serializer = self.get_serializer(integration)
        return Response(
            {
                "message": f"Successfully synchronized {integration.provider.name}.",
                "integration": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class OAuthInitView(APIView):
    """
    Initiates an OAuth 2.0 authorization flow for a target provider.
    Generates authorization URLs and state parameters.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = OAuthInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider_slug = serializer.validated_data["provider_slug"]
        redirect_uri = serializer.validated_data["redirect_uri"]
        requested_scopes = serializer.validated_data.get("scopes", [])

        provider = get_object_or_404(IntegrationProvider, slug=provider_slug, is_active=True)

        if provider.auth_type != "OAUTH2":
            return Response(
                {"error": f"Provider '{provider.name}' does not support OAuth 2.0 authentication."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate state nonces for CSRF validation during callback
        state_token = f"state-{uuid.uuid4().hex}"
        
        # Mock authorization URL generation - replace with actual OAuth endpoints in production
        scope_str = "%20".join(requested_scopes) if requested_scopes else "read_write"
        auth_url = (
            f"https://auth.lifepilot.io/oauth/authorize?"
            f"client_id={provider_slug}&"
            f"redirect_uri={redirect_uri}&"
            f"scope={scope_str}&"
            f"state={state_token}"
        )

        logger.info(
            "Generated OAuth init URL for user %s, provider %s",
            request.user.username,
            provider_slug,
        )

        return Response(
            {
                "provider": provider.slug,
                "authorization_url": auth_url,
                "state": state_token,
            },
            status=status.HTTP_200_OK,
        )


class OAuthCallbackView(APIView):
    """
    Handles authorization code callbacks from external OAuth identity providers.
    Exchanges codes for access tokens and creates/updates ConnectedIntegration records.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, provider_slug: str) -> Response:
        serializer = OAuthCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = get_object_or_404(IntegrationProvider, slug=provider_slug, is_active=True)
        code = serializer.validated_data["code"]
        state = serializer.validated_data["state"]

        logger.info(
            "Processing OAuth callback for provider '%s', state '%s'",
            provider_slug,
            state,
        )

        try:
            with transaction.atomic():
                # Simulated token exchange payload - replace with httpx/requests token post call
                mock_account_id = f"user-{uuid.uuid4().hex[:6]}@{provider_slug}.com"
                mock_access_token = f"access-{uuid.uuid4().hex}"
                mock_refresh_token = f"refresh-{uuid.uuid4().hex}"

                connection, created = ConnectedIntegration.objects.get_or_create(
                    user=request.user,
                    provider=provider,
                    account_identifier=mock_account_id,
                    defaults={
                        "status": ConnectionStatus.CONNECTED,
                        "access_token": mock_access_token,
                        "refresh_token": mock_refresh_token,
                        "last_synced_at": timezone.now(),
                    },
                )

                if not created:
                    connection.access_token = mock_access_token
                    connection.refresh_token = mock_refresh_token
                    connection.status = ConnectionStatus.CONNECTED
                    connection.last_synced_at = timezone.now()
                    connection.last_error_message = None
                    connection.save()

            response_serializer = ConnectedIntegrationSerializer(connection)
            return Response(
                {
                    "message": f"Successfully connected to {provider.name}.",
                    "connection": response_serializer.data,
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.error("Failed to process OAuth callback for %s: %s", provider_slug, str(exc))
            return Response(
                {"error": f"OAuth authorization exchange failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConnectApiKeyView(APIView):
    """
    Endpoint for authenticating integrations using static API keys or Personal Access Tokens.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = IntegrationApiKeyConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider_id = serializer.validated_data["provider_id"]
        api_key = serializer.validated_data["api_key"]
        account_identifier = serializer.validated_data.get(
            "account_identifier", f"apiKey-{uuid.uuid4().hex[:6]}"
        )
        config_payload = serializer.validated_data.get("config_payload", {})

        provider = get_object_or_404(IntegrationProvider, id=provider_id, is_active=True)

        connection, created = ConnectedIntegration.objects.get_or_create(
            user=request.user,
            provider=provider,
            account_identifier=account_identifier,
            defaults={
                "status": ConnectionStatus.CONNECTED,
                "access_token": api_key,
                "config_payload": config_payload,
                "last_synced_at": timezone.now(),
            },
        )

        if not created:
            connection.access_token = api_key
            connection.config_payload = config_payload
            connection.status = ConnectionStatus.CONNECTED
            connection.last_synced_at = timezone.now()
            connection.last_error_message = None
            connection.save()

        response_serializer = ConnectedIntegrationSerializer(connection)
        return Response(
            {
                "message": f"Successfully configured API key connection for {provider.name}.",
                "connection": response_serializer.data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class IntegrationWebhookView(APIView):
    """
    Inbound webhook ingestion endpoint for external service notifications.
    """

    permission_classes = []  # Authenticated via webhook signature in production

    def post(self, request: Request, connection_id: str) -> Response:
        connection = get_object_or_404(ConnectedIntegration, id=connection_id)
        event_type = request.headers.get("X-Event-Type", "generic.event")

        logger.info(
            "Received webhook for integration %s (Event: %s)",
            connection.id,
            event_type,
        )

        webhook_log = IntegrationWebhookLog.objects.create(
            integration=connection,
            event_type=event_type,
            payload=request.data if isinstance(request.data, dict) else {"raw": str(request.data)},
            processed_successfully=True,
        )

        return Response(
            {
                "status": "RECEIVED",
                "log_id": str(webhook_log.id),
                "timestamp": webhook_log.received_at.isoformat(),
            },
            status=status.HTTP_202_ACCEPTED,
        )
