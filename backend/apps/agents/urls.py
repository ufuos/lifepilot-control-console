"""
URL Routing for LifePilot Agents Engine.

Registers DRF ViewSets for:
- Agent Definitions (/api/v1/agents/definitions/)
- Agent Runs (/api/v1/agents/runs/)
- Human-in-the-Loop Approvals (/api/v1/agents/approvals/)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.agents.views import (
    AgentDefinitionViewSet,
    AgentRunViewSet,
    HumanApprovalViewSet,
)

app_name = "agents"

router = DefaultRouter()
router.register(r"definitions", AgentDefinitionViewSet, basename="agent-definition")
router.register(r"runs", AgentRunViewSet, basename="agent-run")
router.register(r"approvals", HumanApprovalViewSet, basename="agent-approval")

urlpatterns = [
    path("", include(router.urls)),
]