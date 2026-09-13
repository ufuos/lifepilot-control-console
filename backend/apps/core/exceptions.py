"""
Custom Exception Handling for LifePilot Core API & Agent Engine.

Standardizes error responses across Django REST Framework, Strands SDK errors,
LangGraph workflow exceptions, and AWS Bedrock API integration failures.
"""

import logging
from typing import Any, Dict, Optional
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("lifepilot.core.exceptions")


class BaseLifePilotException(APIException):
    """Base exception for domain-specific LifePilot errors."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An unexpected error occurred within the LifePilot agent platform."
    default_code = "lifepilot_error"


class AgentExecutionException(BaseLifePilotException):
    """Raised when a Strands SDK agent or LangGraph node encounters an unrecoverable execution failure."""
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Agent execution failed while processing the workflow node."
    default_code = "agent_execution_failed"


class HITLWorkflowException(BaseLifePilotException):
    """Raised when an operation on a Human-in-the-Loop gate fails or is in an invalid state."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Human-in-the-Loop (HITL) authorization state transition failed."
    default_code = "hitl_workflow_error"


class ExternalIntegrationException(BaseLifePilotException):
    """Raised when an external third-party tool or AWS Bedrock / AgentCore API call fails."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "External service integration failed or timed out."
    default_code = "external_integration_error"


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    """
    Custom DRF exception handler that guarantees unified error response payloads.

    Payload Structure:
    {
        "error": {
            "code": "error_code_identifier",
            "message": "Human-readable description",
            "details": {...} | [...],
            "status_code": 400
        }
    }
    """
    # Convert Django native exceptions to DRF APIExceptions
    if isinstance(exc, Http404):
        exc = APIException(detail="Resource not found.", code="not_found")
        exc.status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, PermissionDenied):
        exc = APIException(detail="Permission denied.", code="permission_denied")
        exc.status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            exc = DRFValidationError(detail=exc.message_dict)
        else:
            exc = DRFValidationError(detail=exc.messages)

    # Let DRF handle standard APIException formatting first
    response = exception_handler(exc, context)

    # Extract view context for logging
    view = context.get("view")
    view_name = view.__class__.__name__ if view else "UnknownView"

    if response is not None:
        error_code = getattr(exc, "default_code", "api_error")
        if isinstance(exc, DRFValidationError):
            error_code = "validation_error"

        status_code = response.status_code
        detail = response.data

        # Standardize message and details fields
        if isinstance(detail, dict) and "detail" in detail:
            message = str(detail.pop("detail"))
            details = detail if detail else None
        elif isinstance(detail, (dict, list)):
            message = "Validation failed for input data."
            details = detail
        else:
            message = str(detail)
            details = None

        formatted_response = {
            "error": {
                "code": str(error_code),
                "message": message,
                "details": details,
                "status_code": status_code,
            }
        }

        response.data = formatted_response
        logger.warning(
            "Handled exception [%s] in view [%s]: %s (Status %s)",
            error_code,
            view_name,
            message,
            status_code,
        )
        return response

    # Unhandled server exceptions (500)
    logger.exception("Unhandled exception in view [%s]: %s", view_name, str(exc))

    return Response(
        {
            "error": {
                "code": "internal_server_error",
                "message": "An unhandled internal server error occurred. Please contact system support.",
                "details": None,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )