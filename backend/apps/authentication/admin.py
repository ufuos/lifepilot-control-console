"""
Django Admin configuration for LifePilot Authentication models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from apps.authentication.models import Organization, User, UserAPIToken


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin view for Organization workspaces."""

    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin configuration for LifePilot CustomUser model."""

    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "organization",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("role", "is_active", "is_staff", "is_mfa_enabled", "organization")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal Info"), {"fields": ("first_name", "last_name", "avatar_url", "phone_number")}),
        (
            _("LifePilot Workspace & Permissions"),
            {
                "fields": (
                    "role",
                    "organization",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_mfa_enabled",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "created_at", "updated_at", "date_joined", "last_login")


@admin.register(UserAPIToken)
class UserAPITokenAdmin(admin.ModelAdmin):
    """Admin view for User API Tokens."""

    list_display = ("name", "user", "is_active", "expires_at", "last_used_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "user__email", "key")
    readonly_fields = ("id", "created_at", "last_used_at")
