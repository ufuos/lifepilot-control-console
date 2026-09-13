"""
App Configuration for LifePilot Approvals application.
"""

from django.apps import AppConfig


class ApprovalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.approvals"
    verbose_name = "LifePilot Human-in-the-Loop Approvals"
