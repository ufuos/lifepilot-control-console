"""
App Configuration for Authentication module.
"""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"
    verbose_name = "LifePilot User Authentication"

    def ready(self):
        """Signal setup or extension imports if needed on app startup."""
        pass
