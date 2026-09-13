"""
Django settings for LifePilot Control Console.

Combines Base, Local Development, and Production AWS / Container configurations.
Supports Async/ASGI WebSockets for Agent Streaming, Strands SDK, LangGraph,
PostgreSQL database, and Redis channel layers.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

# ==============================================================================
# 1. BASE PATHS & ENVIRONMENT SETUP
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security & Debug Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "0").lower() in ("true", "1", "t", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]


# ==============================================================================
# 2. APPLICATION DEFINITION
# ==============================================================================
INSTALLED_APPS = [
    # ASGI / WebSockets engine (must be loaded before django.contrib.staticfiles)
    "daphne",
    
    # Standard Django Apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third-Party Extensions
    "rest_framework",
    "django_filters",
    "corsheaders",
    "channels",
    
    # LifePilot Custom Domain Applications
    "apps.core.apps.CoreConfig",
    "apps.authentication.apps.AuthenticationConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.approvals.apps.ApprovalsConfig",
    "apps.integrations.apps.IntegrationsConfig",
    "apps.agents.apps.AgentsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS management
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Primary ASGI application entry point for Daphne / WebSockets
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ==============================================================================
# 3. DATABASE CONFIGURATION (PostgreSQL / SQLite Fallback)
# ==============================================================================
DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.postgresql")
DB_NAME = os.getenv("DB_NAME", "lifepilot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

if os.getenv("USE_SQLITE", "0").lower() in ("true", "1") and DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "CONN_MAX_AGE": 600,
        }
    }


# ==============================================================================
# 4. CHANNELS & REDIS CONFIGURATION (WebSockets & Async Streaming)
# ==============================================================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# In-memory fallback if Redis is unavailable during local standalone testing
if DEBUG and os.getenv("USE_IN_MEMORY_CHANNEL_LAYER", "0") == "1":
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }


# ==============================================================================
# 5. AUTHENTICATION & PASSWORD VALIDATION
# ==============================================================================
# Explicitly set custom user model to prevent auth.User vs authentication.User system checks
AUTH_USER_MODEL = "authentication.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ==============================================================================
# 6. INTERNATIONALIZATION & LOCALIZATION
# ==============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ==============================================================================
# 7. STATIC & MEDIA FILES
# ==============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ==============================================================================
# 8. DJANGO REST FRAMEWORK & CORS CONFIGURATION
# ==============================================================================
REST_FRAMEWORK = {
    # Default Authentication & Permissions
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    # Standardized Pagination
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,

    # Custom Error Payload Formatting across Strands SDK / LangGraph exceptions
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",

    # Search, Ordering, and Filtering Backends
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],

    # Date and Time Formatting
    "DATETIME_FORMAT": "iso-8601",
    "DATE_FORMAT": "iso-8601",
}

# Cross-Origin Resource Sharing (CORS) rules
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True


# ==============================================================================
# 9. AGENT ENGINE CONFIGURATION (Strands SDK & LangGraph Orchestration)
# ==============================================================================
STRANDS_AGENT_CONFIG = {
    "DEFAULT_MODEL": os.getenv("STRANDS_MODEL", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"),
    "MAX_ITERATIONS": int(os.getenv("STRANDS_MAX_ITERATIONS", "15")),
    "MEMORY_BACKEND": os.getenv("STRANDS_MEMORY_BACKEND", "dynamodb"),
    "AWS_REGION": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
}

LANGGRAPH_ORCHESTRATOR_CONFIG = {
    "CHECKPOINTER_TYPE": os.getenv("LANGGRAPH_CHECKPOINTER", "postgres"),
    "CHECKPOINT_DB_URL": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    "HUMAN_IN_THE_LOOP_TIMEOUT": int(os.getenv("HITL_TIMEOUT_SECONDS", "86400")),
}


# ==============================================================================
# 10. PRODUCTION SECURITY & OVERRIDES (AWS App Runner / Cloud Deployments)
# ==============================================================================
if not DEBUG:
    # Strict Production Security Headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    
    # Proxy SSL Header configuration for Nginx / AWS App Runner
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    
    # Cookie Security Settings
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "1") == "1"
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "1") == "1"
    
    # Logging Configuration
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"