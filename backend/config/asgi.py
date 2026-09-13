"""
ASGI config for LifePilot Control Console project.

It exposes the ASGI callable as a module-level variable named ``application``.
Supports HTTP and WebSocket protocols using Django Channels.
"""

import os
from django.core.asgi import get_asgi_application

# 1. Initialize Django ASGI application early to ensure settings & apps are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi_app = get_asgi_application()

# 2. Imports dependent on Django setup must occur after get_asgi_application()
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

from apps.agents.consumers import AgentRunConsumer


# WebSocket URL patterns for the agents application
websocket_urlpatterns = [
    path("ws/agents/runs/<uuid:run_id>/", AgentRunConsumer.as_asgi()),
]


# Root ASGI application handling both HTTP and WebSocket traffic
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    }
)