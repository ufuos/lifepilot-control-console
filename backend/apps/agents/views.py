"""
API Views and ViewSets for LifePilot Agents Management and Execution Engine.

Engineered for the AWS 'Agents for Humans' Hackathon:
- Django REST Framework (DRF) ViewSets with DjangoFilterBackend and SearchFilter.
- Asynchronous and background thread agent run execution.
- Human-in-the-Loop (HITL) authorization and decision resolution endpoints.
- Integration with Strands Agents SDK, AWS Bedrock, and LangGraph state persistence.
"""

import logging
import uuid
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from apps.agents.models import AgentDefinition, AgentRun, AgentThread, HITLApproval
from apps.agents.serializers import (
    AgentDefinitionSerializer,
    AgentRunCreateSerializer,
    AgentRunSerializer,
    AgentThreadSerializer,
    HITLApprovalActionSerializer,
    HITLApprovalSerializer,
)
from apps.agents.strands.agent_runner import LifePilotStrandsRunner
from apps.agents.strands.memory import get_agent_memory

logger = logging.getLogger("lifepilot.agents.views")


class AgentDefinitionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Agent Definitions across Everyday, Professional,
    and Good Neighbor hackathon tracks.
    """

    queryset = AgentDefinition.objects.all()
    serializer_class = AgentDefinitionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["track", "is_active", "model_id"]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]
    lookup_field = "slug"

    def get_queryset(self):
        """Filter definitions visible to the authenticated user or global active agents."""
        user = self.request.user
        return self.queryset.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="trigger-run")
    def trigger_run(self, request: Request, slug: str = None) -> Response:
        """
        Shortcut endpoint to trigger an execution run for a specific agent definition.
        Creates an AgentThread if not provided and dispatches the execution task.
        """
        agent_def = self.get_object()
        prompt = request.data.get("prompt")
        thread_id = request.data.get("thread_id")
        inputs = request.data.get("inputs", {})

        if not prompt:
            return Response(
                {"detail": "The 'prompt' field is required to trigger an agent run."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if thread_id:
                thread = AgentThread.objects.get(id=thread_id, user=request.user)
            else:
                thread = AgentThread.objects.create(
                    user=request.user,
                    agent_definition=agent_def,
                    title=prompt[:60] + ("..." if len(prompt) > 60 else ""),
                )

            agent_run = AgentRun.objects.create(
                thread=thread,
                agent_definition=agent_def,
                user=request.user,
                prompt=prompt,
                inputs=inputs,
                status=AgentRun.Status.PENDING,
            )

        # Dispatch async runner process
        runner = LifePilotStrandsRunner(run_id=agent_run.id)
        runner.dispatch_async()

        run_serializer = AgentRunSerializer(agent_run)
        return Response(
            {
                "message": f"Agent run triggered successfully for '{agent_def.name}'.",
                "run": run_serializer.data,
                "websocket_endpoint": f"/ws/agents/runs/{agent_run.id}/",
            },
            status=status.HTTP_201_CREATED,
        )


class AgentThreadViewSet(viewsets.ModelViewSet):
    """
    API endpoint for multi-turn agent conversation threads and memory sessions.
    """

    queryset = AgentThread.objects.all()
    serializer_class = AgentThreadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["agent_definition", "is_archived"]
    ordering_fields = ["updated_at", "created_at"]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"], url_path="memory")
    def get_memory_context(self, request: Request, pk: str = None) -> Response:
        """Fetch the hybrid session memory turns from Redis/PostgreSQL for this thread."""
        thread = self.get_object()
        memory_store = get_agent_memory(
            thread_id=str(thread.id),
            user_id=str(request.user.id),
        )
        turns = memory_store.get_conversation_context()
        return Response(
            {
                "thread_id": str(thread.id),
                "total_turns": len(turns),
                "turns": turns,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="clear-memory")
    def clear_memory(self, request: Request, pk: str = None) -> Response:
        """Purge stored memory history for this conversation thread."""
        thread = self.get_object()
        memory_store = get_agent_memory(
            thread_id=str(thread.id),
            user_id=str(request.user.id),
        )
        memory_store.clear()
        return Response(
            {"message": f"Memory context cleared for thread '{thread.id}'."},
            status=status.HTTP_200_OK,
        )


class AgentRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly API ViewSet to inspect agent execution runs, trace logs, and execution outputs.
    """

    queryset = AgentRun.objects.all()
    serializer_class = AgentRunSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "agent_definition", "thread"]
    ordering_fields = ["created_at", "started_at", "completed_at"]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_run(self, request: Request, pk: str = None) -> Response:
        """Cancel an ongoing or pending agent execution run."""
        agent_run = self.get_object()
        if agent_run.status in [AgentRun.Status.COMPLETED, AgentRun.Status.FAILED, AgentRun.Status.CANCELLED]:
            return Response(
                {"detail": f"Cannot cancel run in status '{agent_run.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agent_run.status = AgentRun.Status.CANCELLED
        agent_run.completed_at = timezone.now()
        agent_run.error_message = "Cancelled by user request."
        agent_run.save(update_fields=["status", "completed_at", "error_message"])

        logger.info("Agent run [%s] cancelled by user [%s]", agent_run.id, request.user.id)
        return Response(
            {"message": f"Run '{agent_run.id}' has been cancelled.", "status": agent_run.status},
            status=status.HTTP_200_OK,
        )


class HITLApprovalViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing Human-in-the-Loop (HITL) gatekeeper approvals.
    Allows users to review, approve, or reject autonomous agent actions with real-world side effects.
    """

    queryset = HITLApproval.objects.all()
    serializer_class = HITLApprovalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "action_type", "agent_run"]
    ordering_fields = ["created_at", "resolved_at"]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="action")
    def submit_decision(self, request: Request, pk: str = None) -> Response:
        """
        Submit an approval or rejection decision for a pending HITL authorization request.
        Resumes the LangGraph / Strands SDK execution flow if approved.
        """
        approval = self.get_object()
        serializer = HITLApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data["decision"]  # 'approve' or 'reject'
        user_notes = serializer.validated_data.get("notes", "")

        if approval.status != HITLApproval.Status.PENDING:
            return Response(
                {"detail": f"HITL Request '{approval.id}' is already resolved ({approval.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if decision == "approve":
                approval.status = HITLApproval.Status.APPROVED
            else:
                approval.status = HITLApproval.Status.REJECTED

            approval.user_notes = user_notes
            approval.resolved_at = timezone.now()
            approval.save()

            # Update associated run status back to running/resumed
            agent_run = approval.agent_run
            if decision == "approve":
                agent_run.status = AgentRun.Status.RUNNING
            else:
                agent_run.status = AgentRun.Status.FAILED
                agent_run.error_message = f"Action rejected by user: {user_notes or 'No reason provided.'}"
                agent_run.completed_at = timezone.now()
            
            agent_run.save(update_fields=["status", "error_message", "completed_at"])

        logger.info(
            "HITL approval [%s] resolved as [%s] by user [%s]",
            approval.id,
            approval.status,
            request.user.id,
        )

        # Resume agent execution asynchronously if approved
        if decision == "approve":
            runner = LifePilotStrandsRunner(run_id=agent_run.id)
            runner.dispatch_async(resume_from_hitl=True)

        return Response(
            {
                "message": f"HITL decision '{decision}' recorded successfully.",
                "approval": HITLApprovalSerializer(approval).data,
                "agent_run_status": agent_run.status,
            },
            status=status.HTTP_200_OK,
        )


# Backward-compatibility alias for URL pattern imports
HumanApprovalViewSet = HITLApprovalViewSet