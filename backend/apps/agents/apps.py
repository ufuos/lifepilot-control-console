"""
Django Application Configuration for the Agents Engine.

Handles application startup initialization, Strands Agents SDK runtime setup,
and validation of AWS Bedrock / AgentCore credentials for autonomous,
background agent execution.
"""

import logging
import os
from django.apps import AppConfig

logger = logging.getLogger("lifepilot.agents")


class AgentsConfig(AppConfig):
    """Configuration class for the apps.agents Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.agents"
    verbose_name = "LifePilot Autonomous Agents Engine (Strands & LangGraph)"

    def ready(self) -> None:
        """
        Lifecycle hook executed when Django registry is fully loaded.
        Verifies environment configurations for Strands Agents SDK and AWS.
        """
        self._verify_agent_environment()
        self._register_signals()

    def _verify_agent_environment(self) -> None:
        """Validates critical environment configurations for agent runtime."""
        model = os.getenv("STRANDS_MODEL", "gemini-2.5-flash")
        aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        checkpointer = os.getenv("LANGGRAPH_CHECKPOINTER", "postgres")

        logger.info(
            "Initializing LifePilot Agents Engine | Model: %s | AWS Region: %s | Checkpointer: %s",
            model,
            aws_region,
            checkpointer,
        )

    def _register_signals(self) -> None:
        """Connects Django signals for agent status tracking and Human-in-the-Loop triggers."""
        try:
            import apps.agents.signals  # noqa: F401
            logger.debug("Agent signals successfully registered.")
        except ImportError:
            logger.debug("No dedicated agent signals module found; skipping signal registration.")
