"""
URL Routing for LifePilot Connected Integrations.

Registers endpoints for provider discovery, connection management, OAuth lifecycle,
API key setup, and inbound webhook processing.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.integrations.views import (
    ConnectedIntegrationViewSet,
    ConnectApiKeyView,
    IntegrationProviderViewSet,
    IntegrationWebhookView,
    OAuthCallbackView,
    OAuthInitView,
)

app_name = "integrations"

# Primary REST Router for resource viewsets
router = DefaultRouter()
router.register(r"providers", IntegrationProviderViewSet, basename="provider")
router.register(r"connections", ConnectedIntegrationViewSet, basename="connection")

urlpatterns = [
    # Router ViewSets (Providers & User Connections)
    path("", include(router.urls)),
    
    # OAuth Authentication Lifecycle Endpoints
    path("oauth/init/", OAuthInitView.as_view(), name="oauth-init"),
    path("oauth/callback/<slug:provider_slug>/", OAuthCallbackView.as_view(), name="oauth-callback"),
    
    # API Key & Direct Credential Authorization
    path("connect/api-key/", ConnectApiKeyView.as_view(), name="connect-api-key"),
    
    # Inbound Webhook Ingestion Point
    path("webhooks/<uuid:connection_id>/", IntegrationWebhookView.as_view(), name="webhook-ingest"),
]