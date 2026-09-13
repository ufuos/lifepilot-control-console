"""
Serializers for LifePilot Connected Integrations.

Handles serialization and validation for integration providers, active user connections,
OAuth initialization payloads, authorization callbacks, and incoming webhook logs.
"""

from rest_framework import serializers
from django.utils import timezone
from apps.integrations.models import (
    IntegrationProvider,
    ConnectedIntegration,
    IntegrationWebhookLog,
    IntegrationCategory,
    ConnectionStatus,
)


class IntegrationProviderSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and retrieving supported integration providers.
    """
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = IntegrationProvider
        fields = [
            "id",
            "slug",
            "name",
            "category",
            "category_display",
            "description",
            "icon_url",
            "auth_type",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ConnectedIntegrationSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing and updating active user integration connections.
    Masks secret tokens and provides convenience status flags.
    """
    provider_name = serializers.CharField(source="provider.name", read_only=True)
    provider_slug = serializers.CharField(source="provider.slug", read_only=True)
    provider_icon = serializers.URLField(source="provider.icon_url", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_expired = serializers.BooleanField(source="is_token_expired", read_only=True)

    # Obfuscated fields to avoid exposing raw tokens over standard endpoints
    has_access_token = serializers.SerializerMethodField()
    has_refresh_token = serializers.SerializerMethodField()

    class Meta:
        model = ConnectedIntegration
        fields = [
            "id",
            "user",
            "provider",
            "provider_name",
            "provider_slug",
            "provider_icon",
            "status",
            "status_display",
            "account_identifier",
            "granted_scopes",
            "config_payload",
            "has_access_token",
            "has_refresh_token",
            "is_expired",
            "token_expires_at",
            "last_synced_at",
            "last_error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "provider_name",
            "provider_slug",
            "provider_icon",
            "status_display",
            "has_access_token",
            "has_refresh_token",
            "is_expired",
            "last_synced_at",
            "last_error_message",
            "created_at",
            "updated_at",
        ]

    def get_has_access_token(self, obj: ConnectedIntegration) -> bool:
        return bool(obj.access_token)

    def get_has_refresh_token(self, obj: ConnectedIntegration) -> bool:
        return bool(obj.refresh_token)


class OAuthInitSerializer(serializers.Serializer):
    """
    Serializer for validating OAuth flow initialization requests.
    """
    provider_slug = serializers.SlugField(required=True)
    redirect_uri = serializers.URLField(required=True)
    scopes = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )


class OAuthCallbackSerializer(serializers.Serializer):
    """
    Serializer for validating authorization code callbacks from OAuth providers.
    """
    code = serializers.CharField(required=True, write_only=True)
    state = serializers.CharField(required=True, write_only=True)
    redirect_uri = serializers.URLField(required=True, write_only=True)

    def validate_code(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Authorization code cannot be empty.")
        return value.strip()


class IntegrationApiKeyConnectSerializer(serializers.Serializer):
    """
    Serializer for connecting services that authenticate via API keys or Personal Access Tokens.
    """
    provider_id = serializers.UUIDField(required=True)
    api_key = serializers.CharField(required=True, write_only=True)
    account_identifier = serializers.CharField(max_length=255, required=False, allow_blank=True)
    config_payload = serializers.JSONField(required=False, default=dict)

    def validate_api_key(self, value: str) -> str:
        if len(value.strip()) < 8:
            raise serializers.ValidationError("Provided API key is too short.")
        return value.strip()


class IntegrationWebhookLogSerializer(serializers.ModelSerializer):
    """
    Serializer for inspecting inbound webhook audit logs.
    """
    provider_slug = serializers.CharField(source="integration.provider.slug", read_only=True)

    class Meta:
        model = IntegrationWebhookLog
        fields = [
            "id",
            "integration",
            "provider_slug",
            "event_type",
            "payload",
            "processed_successfully",
            "error_log",
            "received_at",
        ]
        read_only_fields = fields