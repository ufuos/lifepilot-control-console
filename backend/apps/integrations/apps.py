"""
Django App Config for Connected Service Integrations.
"""

from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    """
    Configuration class for the integrations application module.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations"
    verbose_name = "LifePilot Connected Integrations"

    def ready(self) -> None:
        """
        Perform app initialization logic such as registering signals or loading integrations.
        """
        try:
            import apps.integrations.signals  # noqa: F401
        except ImportError:
            pass