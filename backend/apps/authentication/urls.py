"""
URL Routing for LifePilot Authentication API endpoints.

Exposes endpoints for user registration, session authentication,
logout, and profile retrieval/updates.
"""

from django.urls import path
from apps.authentication.views import (
    LoginView,
    LogoutView,
    RegisterView,
    UserProfileView,
)

app_name = "authentication"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", UserProfileView.as_view(), name="user-profile"),
]