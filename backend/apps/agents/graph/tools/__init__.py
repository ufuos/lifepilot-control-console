"""
LangGraph and Strands SDK Tool Registry for LifePilot Control Console.

Defines, decorates, and exposes agent tools while establishing risk ratings
used by the Planner and Human Approval nodes to enforce HITL execution policies.
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ============================================================================
# 1. TOOL RISK REGISTRY & POLICY MAPPINGS
# ============================================================================

TOOL_RISK_LEVELS: Dict[str, str] = {
    # Low Risk - Read-only operations
    "fetch_calendar_events": "LOW",
    "query_system_analytics": "LOW",
    "get_user_preferences": "LOW",
    
    # Medium Risk - Non-destructive state mutations
    "create_calendar_event": "MEDIUM",
    "send_slack_message": "MEDIUM",
    
    # High / Critical Risk - External communication, financial, or destructive ops (Requires HITL)
    "send_external_email": "HIGH",
    "modify_system_configuration": "HIGH",
    "delete_user_data": "CRITICAL",
    "execute_financial_transaction": "CRITICAL",
}


def get_tool_risk_level(tool_name: str) -> str:
    """
    Returns the risk level associated with a registered tool.
    Defaults to 'HIGH' if the tool is unrecognized to enforce defensive safety.
    """
    return TOOL_RISK_LEVELS.get(tool_name, "HIGH")


# ============================================================================
# 2. DEFINITION OF PLATFORM AGENT TOOLS
# ============================================================================

@tool
def fetch_calendar_events(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Fetches scheduled calendar events within a specified date range.

    Args:
        start_date: ISO 8601 formatted start date string.
        end_date: ISO 8601 formatted end date string.

    Returns:
        List of event objects.
    """
    logger.info("Executing tool: fetch_calendar_events from %s to %s", start_date, end_date)
    # Tool stub implementation - connect to Calendar API / service
    return [
        {
            "event_id": "evt-101",
            "title": "LifePilot Architecture Review",
            "start": start_date,
            "end": end_date,
            "status": "CONFIRMED",
        }
    ]


@tool
def send_external_email(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Sends an email to an external recipient. (Requires HITL Approval)

    Args:
        recipient: Target email address.
        subject: Email subject line.
        body: Text content of the message.

    Returns:
        Execution status summary.
    """
    logger.info("Executing tool: send_external_email to %s", recipient)
    return {
        "status": "SENT",
        "recipient": recipient,
        "subject": subject,
        "timestamp": "2026-09-01T00:00:00Z",
    }


@tool
def modify_system_configuration(config_key: str, new_value: Any) -> Dict[str, Any]:
    """
    Updates core environment config settings. (Requires HITL Approval)

    Args:
        config_key: Configuration attribute key.
        new_value: New value to assign.

    Returns:
        Modification audit status.
    """
    logger.info("Executing tool: modify_system_configuration [%s = %s]", config_key, new_value)
    return {
        "status": "UPDATED",
        "key": config_key,
        "value": new_value,
    }


@tool
def query_system_analytics(metric: str, timeframe: str = "24h") -> Dict[str, Any]:
    """
    Queries execution metrics and performance telemetry for LifePilot services.

    Args:
        metric: Metric name (e.g., 'cpu_usage', 'agent_latency', 'active_threads').
        timeframe: Window duration string (e.g., '1h', '24h', '7d').

    Returns:
        Telemetry data dictionary.
    """
    logger.info("Executing tool: query_system_analytics for %s over %s", metric, timeframe)
    return {
        "metric": metric,
        "timeframe": timeframe,
        "data_points": [0.85, 0.88, 0.92, 0.89],
        "status": "OK",
    }


# ============================================================================
# 3. TOOL REGISTRY EXPORTS
# ============================================================================

# Primary list of all standard tools available to graph execution nodes
ALL_TOOLS: List[Callable] = [
    fetch_calendar_events,
    send_external_email,
    modify_system_configuration,
    query_system_analytics,
]

# Map tool names directly to callable objects for rapid agent dispatch
TOOL_MAP: Dict[str, Callable] = {tool.name: tool for tool in ALL_TOOLS}

__all__ = [
    "ALL_TOOLS",
    "TOOL_MAP",
    "TOOL_RISK_LEVELS",
    "get_tool_risk_level",
    "fetch_calendar_events",
    "send_external_email",
    "modify_system_configuration",
    "query_system_analytics",
]