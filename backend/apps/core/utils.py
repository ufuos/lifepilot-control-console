"""
Core utility functions and helpers for LifePilot Control Console.

Provides shared functionality for:
- Standardized API response formatting (complementing pagination.py & exceptions.py).
- AWS Bedrock / Strands SDK tool payload sanitization and security helpers.
- LangGraph checkpoint thread generation and UUID formatting.
"""

import json
import logging
import uuid
from typing import Any, Dict, Optional
from django.utils import timezone

logger = logging.getLogger("lifepilot.core.utils")


def format_success_response(
    data: Any,
    message: str = "Success",
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Constructs a standardized success payload format across all LifePilot REST API endpoints.

    Args:
        data: Primary response content (dict, list, or primitive).
        message: Human-readable status message.
        status_code: HTTP status code.
        meta: Optional contextual metadata (e.g., timing, execution trace IDs).

    Returns:
        Structured envelope dict.
    """
    payload = {
        "success": True,
        "message": message,
        "status_code": status_code,
        "timestamp": timezone.now().isoformat(),
        "data": data,
    }
    if meta:
        payload["meta"] = meta
    return payload


def generate_langgraph_thread_id(prefix: str = "thread") -> str:
    """
    Generates a unique thread identifier for LangGraph state checkpoint tracking.

    Args:
        prefix: Namespace prefix for thread (e.g., 'aws_agent', 'hitl_approval').

    Returns:
        Formatted string: '{prefix}_{uuid4_hex}'
    """
    unique_suffix = uuid.uuid4().hex
    return f"{prefix}_{unique_suffix}"


def sanitize_payload_for_logging(payload: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
    """
    Redacts sensitive keys (credentials, authorization tokens, API keys) from proposed tool 
    payloads or log outputs to prevent secret leaks in audit trails.
    """
    SENSITIVE_KEYS = {
        "password",
        "secret",
        "token",
        "access_key",
        "secret_key",
        "authorization",
        "api_key",
        "private_key",
    }

    if not isinstance(payload, dict):
        return payload

    sanitized = {}
    for key, value in payload.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "********"
        elif isinstance(value, dict) and max_depth > 0:
            sanitized[key] = sanitize_payload_for_logging(value, max_depth=max_depth - 1)
        elif isinstance(value, list) and max_depth > 0:
            sanitized[key] = [
                sanitize_payload_for_logging(item, max_depth=max_depth - 1)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def safe_json_loads(data: str, default: Optional[Any] = None) -> Any:
    """
    Safely parses JSON strings without raising raw exceptions. Useful when processing
    raw LLM string outputs from Strands SDK or AWS Bedrock tool calls.
    """
    try:
        return json.loads(data)
    except (TypeError, ValueError) as err:
        logger.debug("Failed to parse JSON string: %s. Returning default.", err)
        return default if default is not None else {}