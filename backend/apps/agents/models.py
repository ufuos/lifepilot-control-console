"""
Data Models for the LifePilot Autonomous Agents Engine.

Tracks agent execution runs, execution steps/tool calls, system prompt versions,
and Human-in-the-Loop (HITL) approval states integrated with Strands Agents SDK
and LangGraph Orchestration.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AgentTrack(models.TextChoices):
    """Hackathon competition tracks for LifePilot Agent instances."""
    EVERYDAY = "everyday", _("Everyday Agents (Busywork, Home, Health, Errands)")
    PROFESSIONAL = "professional", _("Professional Agents (Workplace, Creator, SMB)")
    GOOD_NEIGHBOR = "good_neighbor", _("Good Neighbor Agents (Community, Local Orgs)")


class AgentStatus(models.TextChoices):
    """Execution state machine for Strands Agents SDK & LangGraph engine."""
    IDLE = "idle", _("Idle")
    PENDING = "pending", _("Pending Queue")
    RUNNING = "running", _("Autonomous Execution Running")
    AWAITING_APPROVAL = "awaiting_approval", _("Awaiting Human Approval (HITL)")
    APPROVED = "approved", _("Approval Granted")
    REJECTED = "rejected", _("Approval Rejected")
    COMPLETED = "completed", _("Completed Successfully")
    FAILED = "failed", _("Execution Failed")
    CANCELLED = "cancelled", _("Execution Cancelled")


class AgentDefinition(models.Model):
    """
    Defines configured agent instances built using the Strands Agents SDK.
    Serves as the blueprint for background task processing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text=_("Display name of the agent."))
    slug = models.SlugField(max_length=255, unique=True, help_text=_("Unique identifier for routing."))
    track = models.CharField(
        max_length=32,
        choices=AgentTrack.choices,
        default=AgentTrack.EVERYDAY,
        help_text=_("Hackathon submission track alignment."),
    )
    description = models.TextField(help_text=_("Functional scope and background tasks handled by this agent."))
    
    # Strands & AWS Configuration
    strands_model = models.CharField(
        max_length=128,
        default="gemini-2.5-flash",
        help_text=_("Strands SDK model engine (e.g., gemini-2.5-flash, bedrock/anthropic.claude-3-5-sonnet)."),
    )
    aws_bedrock_agent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("AWS Bedrock / AgentCore deployment resource ID for production execution."),
    )
    aws_agent_alias_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("AWS Bedrock Agent Alias ID for versioned deployment."),
    )
    system_prompt = models.TextField(
        help_text=_("Base system prompt instructions defining the agent's behavior and constraints.")
    )
    max_iterations = models.PositiveIntegerField(
        default=15,
        help_text=_("Maximum autonomous reasoning/tool execution steps permitted per run."),
    )
    requires_hitl = models.BooleanField(
        default=True,
        help_text=_("If True, critical side-effect tools require explicit Human-in-the-Loop approval."),
    )
    is_active = models.BooleanField(default=True, help_text=_("Soft toggle to enable or pause agent execution."))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Agent Definition")
        verbose_name_plural = _("Agent Definitions")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} [{self.get_track_display()}]"


class AgentRun(models.Model):
    """
    Tracks an individual execution instance of an agent running through
    the LangGraph orchestrator and Strands Agents SDK.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        AgentDefinition,
        on_delete=models.CASCADE,
        related_name="runs",
        help_text=_("Parent agent definition."),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_runs",
        help_text=_("User on whose behalf the autonomous agent operates."),
    )
    
    # LangGraph & Checkpoint Orchestration
    thread_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text=_("LangGraph checkpointer thread ID for persistent state recovery."),
    )
    checkpoint_ns = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text=_("LangGraph state namespace."),
    )
    status = models.CharField(
        max_length=32,
        choices=AgentStatus.choices,
        default=AgentStatus.PENDING,
        db_index=True,
    )
    
    # Task Context & Output Data
    input_payload = models.JSONField(
        default=dict,
        help_text=_("Initial task payload, user preferences, and trigger parameters."),
    )
    output_result = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Final structured output returned by the Strands Agent execution."),
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text=_("Detailed error stack trace if execution fails."),
    )
    
    # Telemetry & Execution Metrics
    tokens_used = models.PositiveIntegerField(default=0, help_text=_("Total LLM token usage across run steps."))
    execution_time_seconds = models.FloatField(default=0.0, help_text=_("Total duration of agent execution."))
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Agent Execution Run")
        verbose_name_plural = _("Agent Execution Runs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["thread_id", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return f"Run {str(self.id)[:8]} - {self.agent.name} ({self.status})"

    def mark_completed(self, output: dict, execution_time: float = 0.0) -> None:
        """Helper to mark run completed with metrics update."""
        self.status = AgentStatus.COMPLETED
        self.output_result = output
        self.execution_time_seconds = execution_time
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "output_result", "execution_time_seconds", "completed_at"])


class AgentStep(models.Model):
    """
    Detailed audit log of each intermediate reasoning step, tool call,
    and observation generated during an agent run.
    """
    class StepType(models.TextChoices):
        REASONING = "reasoning", _("LLM Thought / Reasoning Step")
        TOOL_CALL = "tool_call", _("Tool Execution Call")
        TOOL_RESULT = "tool_result", _("Tool Observation Output")
        LANGGRAPH_NODE = "langgraph_node", _("LangGraph State Transition")
        HITL_GATE = "hitl_gate", _("Human Approval Interrupt")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        AgentRun,
        on_delete=models.CASCADE,
        related_name="steps",
        help_text=_("Associated agent execution run."),
    )
    step_number = models.PositiveIntegerField(help_text=_("Sequential step order in execution graph."))
    step_type = models.CharField(max_length=32, choices=StepType.choices, default=StepType.REASONING)
    
    node_name = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text=_("LangGraph workflow node name (e.g., 'planner', 'strands_runner', 'hitl_checker')."),
    )
    tool_name = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text=_("Name of the Strands tool invoked during this step."),
    )
    tool_input = models.JSONField(blank=True, null=True, help_text=_("Arguments passed to the tool function."))
    tool_output = models.JSONField(blank=True, null=True, help_text=_("Data payload returned by tool execution."))
    
    thought_process = models.TextField(
        blank=True,
        null=True,
        help_text=_("Agent internal monologue / reasoning behind this action."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Agent Execution Step")
        verbose_name_plural = _("Agent Execution Steps")
        ordering = ["run", "step_number"]
        unique_together = [["run", "step_number"]]

    def __str__(self) -> str:
        return f"Step {self.step_number} [{self.step_type}] for Run {str(self.run.id)[:8]}"


class HumanApprovalRequest(models.Model):
    """
    Human-in-the-Loop (HITL) approval gate records triggered when an autonomous
    agent attempts high-risk tasks (e.g., sending emails, making financial payments,
    or modifying sensitive resources).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        AgentRun,
        on_delete=models.CASCADE,
        related_name="approval_requests",
        help_text=_("Agent run currently paused awaiting human judgment."),
    )
    action_type = models.CharField(
        max_length=128,
        help_text=_("Action requiring human authorization (e.g., 'send_email', 'pay_bill', 'delete_file')."),
    )
    action_description = models.TextField(
        help_text=_("Human-readable explanation of why approval is required and what will happen.")
    )
    proposed_payload = models.JSONField(
        default=dict,
        help_text=_("The precise parameters and payload the agent plans to execute if approved."),
    )
    
    # State tracking
    status = models.CharField(
        max_length=32,
        choices=AgentStatus.choices,
        default=AgentStatus.AWAITING_APPROVAL,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_approvals",
        help_text=_("User who approved or rejected the action."),
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text=_("Optional notes provided by user upon rejection."),
    )
    
    # Timeout and Expiration
    expires_at = models.DateTimeField(
        help_text=_("Expiration timestamp after which the approval request automatically times out.")
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Human Approval Request")
        verbose_name_plural = _("Human Approval Requests")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Approval Request {str(self.id)[:8]} - {self.action_type} ({self.status})"

    def approve(self, user) -> None:
        """Approve the pending action and release the LangGraph execution lock."""
        self.status = AgentStatus.APPROVED
        self.reviewed_by = user
        self.decided_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "decided_at"])
        
        # Resume parent run status
        self.run.status = AgentStatus.RUNNING
        self.run.save(update_fields=["status"])

    def reject(self, user, reason: str = "") -> None:
        """Reject the action and abort or redirect agent execution."""
        self.status = AgentStatus.REJECTED
        self.reviewed_by = user
        self.rejection_reason = reason
        self.decided_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "rejection_reason", "decided_at"])
        
        # Update parent run status
        self.run.status = AgentStatus.REJECTED
        self.run.save(update_fields=["status"])


# Backward-compatibility aliases for dashboard views and external imports
AgentExecution = AgentRun
AgentThread = AgentRun
PendingApproval = HumanApprovalRequest
HITLApproval = HumanApprovalRequest