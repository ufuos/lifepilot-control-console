"""
Models for LifePilot Connected Integrations and Credential Management.

Stores integration metadata, OAuth token configurations, webhook secrets,
and connection status for external tools (e.g., Slack, Google Workspace, GitHub).
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class IntegrationCategory(models.TextChoices):
    COMMUNICATION = "COMMUNICATION", _("Communication & Messaging")
    CALENDAR = "CALENDAR", _("Calendar & Scheduling")
    PRODUCTIVITY = "PRODUCTIVITY", _("Productivity & Workspace")
    DEVELOPMENT = "DEVELOPMENT", _("Development & DevOps")
    INFRASTRUCTURE = "INFRASTRUCTURE", _("Cloud & Infrastructure")


class ConnectionStatus(models.TextChoices):
    CONNECTED = "CONNECTED", _("Connected & Active")
    DISCONNECTED = "DISCONNECTED", _("Disconnected")
    EXPIRED = "EXPIRED", _("Credentials Expired")
    ERROR = "ERROR", _("Configuration Error")
    PENDING_OAUTH = "PENDING_OAUTH", _("Pending OAuth Authorization")


class IntegrationProvider(models.Model):
    """
    Registry of supported external integrations available in LifePilot.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(
        unique=True,
        max_length=50,
        help_text=_("Unique identifier slug (e.g., 'google-calendar', 'slack', 'github')."),
    )
    name = models.CharField(max_length=100, help_text=_("Display name of the integration provider."))
    category = models.CharField(
        max_length=30,
        choices=IntegrationCategory.choices,
        default=IntegrationCategory.PRODUCTIVITY,
    )
    description = models.TextField(blank=True, help_text=_("Short description of tool capabilities."))
    icon_url = models.URLField(blank=True, null=True, help_text=_("URL or path to service icon asset."))
    
    # Provider capabilities & authentication settings
    auth_type = models.CharField(
        max_length=20,
        choices=[
            ("OAUTH2", "OAuth 2.0"),
            ("API_KEY", "API Key / Token"),
            ("WEBHOOK", "Webhook Secret"),
        ],
        default="OAUTH2",
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Controls whether this integration is selectable by users."),
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Integration Provider")
        verbose_name_plural = _("Integration Providers")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_display()})"


class ConnectedIntegration(models.Model):
    """
    Represents an active or configured connection between a LifePilot user
    and an external provider, holding status and auth configurations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integrations",
        help_text=_("Owner of the connected integration."),
    )
    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.PROTECT,
        related_name="connections",
    )
    status = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.PENDING_OAUTH,
    )
    
    # Connection account metadata (e.g., connected email or workspace name)
    account_identifier = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("External account identifier (e.g., 'user@gmail.com' or Slack workspace ID)."),
    )
    
    # Credential & Token Storage (Expected to be encrypted at rest or via Vault)
    access_token = models.TextField(blank=True, null=True, help_text=_("OAuth access token or API key."))
    refresh_token = models.TextField(blank=True, null=True, help_text=_("OAuth refresh token if applicable."))
    token_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Additional integration settings & scopes
    granted_scopes = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of OAuth permissions/scopes authorized by the user."),
    )
    config_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Service-specific configurations (e.g., default channels, sync intervals)."),
    )
    
    # Sync and telemetry timestamps
    last_synced_at = models.DateTimeField(blank=True, null=True)
    last_error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Connected Integration")
        verbose_name_plural = _("Connected Integrations")
        unique_together = ["user", "provider", "account_identifier"]
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.provider.name} - {self.account_identifier or 'Configured'} ({self.user.username})"

    @property
    def is_token_expired(self) -> bool:
        """Checks whether the stored OAuth token is past its expiration date."""
        if not self.token_expires_at:
            return False
        return timezone.now() >= self.token_expires_at


class IntegrationWebhookLog(models.Model):
    """
    Audit log for inbound webhook signals received from external integrations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        ConnectedIntegration,
        on_delete=models.CASCADE,
        related_name="webhook_logs",
    )
    event_type = models.CharField(max_length=100, help_text=_("Event type received (e.g., 'calendar.event_updated')."))
    payload = models.JSONField(default=dict)
    processed_successfully = models.BooleanField(default=True)
    error_log = models.TextField(blank=True, null=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Integration Webhook Log")
        verbose_name_plural = _("Integration Webhook Logs")
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.event_type} - {self.integration.provider.name} ({self.received_at.strftime('%Y-%m-%d %H:%M')})"
