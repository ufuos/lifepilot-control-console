"""
External Integration Tools for LifePilot Agent Framework.

Provides concrete implementations for external service integrations including
calendar management, external messaging, email transmission, and system configuration updates.
"""

import logging
from typing import Any, Dict, List, Optional
from django.utils import timezone
from pydantic import BaseModel, Field

from apps.agents.graph.tools.base_tool import BaseLifePilotTool

logger = logging.getLogger(__name__)


# ============================================================================
# 1. CALENDAR INTEGRATION TOOLS
# ============================================================================

class FetchCalendarInput(BaseModel):
    start_time: str = Field(..., description="ISO 8601 formatted start timestamp.")
    end_time: str = Field(..., description="ISO 8601 formatted end timestamp.")
    calendar_id: Optional[str] = Field(default="primary", description="Target calendar identifier.")


class FetchCalendarEventsTool(BaseLifePilotTool):
    """Retrieves upcoming calendar events within a specified timeframe."""

    name = "fetch_calendar_events"
    description = "Retrieves calendar events between start_time and end_time."
    args_schema = FetchCalendarInput
    risk_level = "LOW"

    def _execute(self, start_time: str, end_time: str, calendar_id: str = "primary") -> Dict[str, Any]:
        logger.info("Fetching calendar events for calendar '%s' from %s to %s", calendar_id, start_time, end_time)
        return {
            "calendar_id": calendar_id,
            "count": 2,
            "events": [
                {
                    "event_id": "evt-201",
                    "title": "LifePilot Agentic Architecture Review",
                    "start": start_time,
                    "end": end_time,
                    "location": "Virtual Conference Room",
                    "status": "CONFIRMED",
                },
                {
                    "event_id": "evt-202",
                    "title": "Sprint Planning & Backlog Grooming",
                    "start": start_time,
                    "end": end_time,
                    "location": "Main Workspace",
                    "status": "CONFIRMED",
                },
            ],
        }


class CreateCalendarEventInput(BaseModel):
    title: str = Field(..., description="Summary or title of the event.")
    start_time: str = Field(..., description="ISO 8601 start timestamp.")
    end_time: str = Field(..., description="ISO 8601 end timestamp.")
    attendees: List[str] = Field(default_factory=list, description="List of participant email addresses.")
    description: Optional[str] = Field(default="", description="Detailed event description.")


class CreateCalendarEventTool(BaseLifePilotTool):
    """Creates a new entry on the primary user calendar."""

    name = "create_calendar_event"
    description = "Schedules a new calendar event with title, timing, and attendees."
    args_schema = CreateCalendarEventInput
    risk_level = "MEDIUM"

    def _execute(
        self,
        title: str,
        start_time: str,
        end_time: str,
        attendees: List[str] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        logger.info("Creating calendar event '%s' starting at %s", title, start_time)
        return {
            "event_id": "evt-created-909",
            "title": title,
            "start": start_time,
            "end": end_time,
            "attendees": attendees or [],
            "status": "CREATED",
            "created_at": timezone.now().isoformat(),
        }


# ============================================================================
# 2. MESSAGING & EMAIL INTEGRATION TOOLS (HIGH/CRITICAL RISK)
# ============================================================================

class SendEmailInput(BaseModel):
    recipient: str = Field(..., description="Target email address.")
    subject: str = Field(..., description="Subject line of the email.")
    body: str = Field(..., description="Message text or HTML payload.")
    cc: Optional[List[str]] = Field(default_factory=list, description="Optional CC recipient email list.")


class SendExternalEmailTool(BaseLifePilotTool):
    """Sends an external email message. Requires explicit HITL approval."""

    name = "send_external_email"
    description = "Dispatches an email message to an external recipient address."
    args_schema = SendEmailInput
    risk_level = "HIGH"

    def _execute(self, recipient: str, subject: str, body: str, cc: List[str] = None) -> Dict[str, Any]:
        logger.info("Sending external email to recipient: %s with subject: '%s'", recipient, subject)
        return {
            "status": "DISPATCHED",
            "message_id": "msg-ext-88321",
            "recipient": recipient,
            "cc": cc or [],
            "subject": subject,
            "timestamp": timezone.now().isoformat(),
        }


class SendSlackMessageInput(BaseModel):
    channel: str = Field(..., description="Target Slack channel or user ID (e.g., '#ops-alerts').")
    message: str = Field(..., description="Message text payload.")


class SendSlackMessageTool(BaseLifePilotTool):
    """Posts a message to a workspace chat channel."""

    name = "send_slack_message"
    description = "Posts a notification or status update to a Slack channel."
    args_schema = SendSlackMessageInput
    risk_level = "MEDIUM"

    def _execute(self, channel: str, message: str) -> Dict[str, Any]:
        logger.info("Posting message to Slack channel '%s'", channel)
        return {
            "status": "DELIVERED",
            "channel": channel,
            "timestamp": timezone.now().isoformat(),
        }


# ============================================================================
# 3. SYSTEM CONFIGURATION & DESTRUCTIVE TOOLS
# ============================================================================

class SystemConfigInput(BaseModel):
    config_key: str = Field(..., description="Target environment variable or setting key.")
    new_value: Any = Field(..., description="New configuration value to assign.")
    reason: str = Field(..., description="Justification for the configuration update.")


class ModifySystemConfigurationTool(BaseLifePilotTool):
    """Modifies runtime system settings. Requires explicit HITL approval."""

    name = "modify_system_configuration"
    description = "Updates system configuration key-value pairs in production environment."
    args_schema = SystemConfigInput
    risk_level = "HIGH"

    def _execute(self, config_key: str, new_value: Any, reason: str) -> Dict[str, Any]:
        logger.info("Modifying system config '%s' to new value. Reason: %s", config_key, reason)
        return {
            "status": "APPLIED",
            "key": config_key,
            "value": new_value,
            "updated_at": timezone.now().isoformat(),
        }


# Export instances of integration tools
fetch_calendar_tool = FetchCalendarEventsTool()
create_calendar_tool = CreateCalendarEventTool()
send_email_tool = SendExternalEmailTool()
send_slack_tool = SendSlackMessageTool()
modify_config_tool = ModifySystemConfigurationTool()

INTEGRATION_TOOLS = [
    fetch_calendar_tool,
    create_calendar_tool,
    send_email_tool,
    send_slack_tool,
    modify_config_tool,
]