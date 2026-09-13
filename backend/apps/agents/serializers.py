"""
Django REST Framework Serializers for LifePilot Agents Engine.

Handles serialization and validation for:
- Agent Definitions (Everyday, Professional, Good Neighbor tracks)
- Execution Runs & Telemetry Metrics
- Intermediate Execution Steps & Tool Calls
- Human-in-the-Loop (HITL) Authorization Requests
"""

from rest_framework import serializers
from apps.agents.models import (
    AgentDefinition,
    AgentRun,
    AgentStep,
    AgentStatus,
    HumanApprovalRequest,
)


class AgentDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for Agent blueprints built on the Strands Agents SDK."""
    track_display = serializers.CharField(source="get_track_display", read_only=True)

    class Meta:
        model = AgentDefinition
        fields = [
            "id",
            "name",
            "slug",
            "track",
            "track_display",
            "description",
            "strands_model",
            "aws_bedrock_agent_id",
            "aws_agent_alias_id",
            "system_prompt",
            "max_iterations",
            "requires_hitl",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AgentStepSerializer(serializers.ModelSerializer):
    """Serializer for detailed execution step audit logs."""
    step_type_display = serializers.CharField(source="get_step_type_display", read_only=True)

    class Meta:
        model = AgentStep
        fields = [
            "id",
            "step_number",
            "step_type",
            "step_type_display",
            "node_name",
            "tool_name",
            "tool_input",
            "tool_output",
            "thought_process",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class HumanApprovalSerializer(serializers.ModelSerializer):
    """Serializer for Human-in-the-Loop (HITL) gatekeeper authorization requests."""
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)

    class Meta:
        model = HumanApprovalRequest
        fields = [
            "id",
            "run",
            "action_type",
            "action_description",
            "proposed_payload",
            "status",
            "status_display",
            "reviewed_by",
            "reviewed_by_email",
            "rejection_reason",
            "expires_at",
            "decided_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "run",
            "action_type",
            "action_description",
            "proposed_payload",
            "reviewed_by",
            "expires_at",
            "decided_at",
            "created_at",
        ]


class AgentRunSerializer(serializers.ModelSerializer):
    """Full serializer for inspecting an individual agent execution run and telemetry."""
    agent_name = serializers.CharField(source="agent.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    steps = AgentStepSerializer(many=True, read_only=True)
    approval_requests = HumanApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "agent",
            "agent_name",
            "user",
            "thread_id",
            "checkpoint_ns",
            "status",
            "status_display",
            "input_payload",
            "output_result",
            "error_message",
            "tokens_used",
            "execution_time_seconds",
            "started_at",
            "completed_at",
            "created_at",
            "steps",
            "approval_requests",
        ]
        read_only_fields = [
            "id",
            "user",
            "status",
            "output_result",
            "error_message",
            "tokens_used",
            "execution_time_seconds",
            "started_at",
            "completed_at",
            "created_at",
        ]


class AgentRunCreateSerializer(serializers.Serializer):
    """Payload serializer for initiating a new autonomous agent execution run."""
    agent_id = serializers.UUIDField(required=True)
    thread_id = serializers.CharField(required=False, allow_blank=True, max_length=255)
    prompt = serializers.CharField(required=True)
    context_data = serializers.JSONField(required=False, default=dict)

    def validate_agent_id(self, value):
        if not AgentDefinition.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Active AgentDefinition not found for the provided ID.")
        return value


class AgentExecutionTriggerSerializer(AgentRunCreateSerializer):
    """Explicit trigger serializer required by dashboard views."""
    pass


class HITLApprovalActionSerializer(serializers.Serializer):
    """Payload serializer for submitting user approval/rejection decisions."""
    decision = serializers.ChoiceField(choices=["approve", "reject"], required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# Backward-compatibility aliases for dashboard views and external imports
AgentExecutionSerializer = AgentRunSerializer
AgentExecutionDetailSerializer = AgentRunSerializer
AgentThreadSerializer = AgentRunSerializer
PendingApprovalSerializer = HumanApprovalSerializer
HITLApprovalSerializer = HumanApprovalSerializer
HITLDecisionSerializer = HITLApprovalActionSerializer