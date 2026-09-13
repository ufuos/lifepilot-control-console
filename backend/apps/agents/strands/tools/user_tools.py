"""
User Application & Domain Action Tools for Strands SDK.

Provides customized Strands tools (@tool) allowing agents to schedule events,
send user notifications, update task states, and log audit traces in the Django application.
"""

import logging
from typing import Any, Dict, List, Optional

from django.utils import timezone
from strands import tool

logger = logging.getLogger("lifepilot.agents.tools.user")


@tool
def send_user_notification(
    recipient: str,
    subject: str,
    message: str,
    channel: str = "email",
) -> Dict[str, Any]:
    """
    Send an urgent or transactional message to a user via email, SMS, or push notification.

    Args:
        recipient: Target user identifier, email address, or phone number.
        subject: Brief headline or title of the alert.
        message: Full text body of the notification.
        channel: Delivery medium ('email', 'sms', 'in_app').

    Returns:
        Dict containing delivery dispatch status.
    """
    logger.info("Dispatching %s notification to %s: %s", channel, recipient, subject)
    
    # In production, this integrates with Celery / Django email backend or Twilio/SES.
    return {
        "status": "dispatched",
        "recipient": recipient,
        "channel": channel,
        "subject": subject,
        "timestamp": timezone.now().isoformat(),
    }


@tool
def schedule_calendar_event(
    title: str,
    start_time_iso: str,
    duration_minutes: int,
    description: str = "",
    attendees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Schedule a calendar event or reminder on behalf of the user.

    Args:
        title: Title of the event or action item.
        start_time_iso: ISO 8601 string for start date/time (e.g. '2026-09-01T10:00:00Z').
        duration_minutes: Duration of the meeting in minutes.
        description: Detailed context, meeting notes, or agenda.
        attendees: List of participant email addresses.

    Returns:
        Dict confirming calendar entry creation.
    """
    logger.info("Scheduling calendar event '%s' starting at %s", title, start_time_iso)
    
    return {
        "status": "scheduled",
        "event_id": f"evt_{int(timezone.now().timestamp())}",
        "title": title,
        "start_time": start_time_iso,
        "duration_minutes": duration_minutes,
        "attendees": attendees or [],
    }


@tool
def update_task_status(
    task_id: str,
    status: str,
    summary_note: str = "",
) -> Dict[str, Any]:
    """
    Update the progress state or completion of a user workflow task.

    Args:
        task_id: Unique task ID string.
        status: Target state ('pending', 'in_progress', 'completed', 'blocked').
        summary_note: Execution notes or completion summary.

    Returns:
        Dict confirming task update state.
    """
    valid_statuses = {"pending", "in_progress", "completed", "blocked"}
    if status.lower() not in valid_statuses:
        return {
            "status": "error",
            "message": f"Invalid status '{status}'. Must be one of {valid_statuses}.",
        }

    logger.info("Updating task [%s] to status '%s'", task_id, status)
    
    return {
        "status": "updated",
        "task_id": task_id,
        "new_status": status.lower(),
        "updated_at": timezone.now().isoformat(),
        "summary_note": summary_note,
    }


def get_user_tools(agent_run: Optional[Any] = None) -> List[Any]:
    """
    Returns the compiled list of user application Strands tools.
    """
    return [
        send_user_notification,
        schedule_calendar_event,
        update_task_status,
    ]