"""
URL Configuration for LifePilot Control Console backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """
    Simple health check endpoint for AWS App Runner, Nginx, and load balancers.
    """
    return JsonResponse(
        {
            "status": "healthy",
            "service": "lifepilot-backend",
            "version": "1.0.0",
        },
        status=200,
    )


# Versioned API Router Patterns
api_v1_patterns = [
    path("auth/", include("apps.authentication.urls", namespace="auth")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("approvals/", include("apps.approvals.urls", namespace="approvals")),
    path("integrations/", include("apps.integrations.urls", namespace="integrations")),
    path("agents/", include("apps.agents.urls", namespace="agents")),
]

urlpatterns = [
    # Health Check Endpoint
    path("health/", health_check, name="health-check"),
    
    # Django Admin Panel
    path("admin/", admin.site.urls),
    
    # API v1 Endpoint Router
    path("api/v1/", include((api_v1_patterns, "api-v1"))),
]

# Serve media files in local development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)