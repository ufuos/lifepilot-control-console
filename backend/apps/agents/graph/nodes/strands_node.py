"""
Strands SDK Agent Execution Node for LifePilot Control Console.

Executes sub-tasks dispatched by the Planner node using Strands SDK agents,
processes tool invocations, handles errors, and returns updated graph state.
"""

import logging
from typing import Any, Dict, List, Optional
from django.utils import timezone
from langchain_core.messages import AIMessage, ToolMessage

from apps.agents.graph.state import AgentState

logger = logging.getLogger(__name__)


class StrandsAgentExecutionError(Exception):
    """Custom exception raised when Strands SDK agent execution encounters a fatal error."""
    pass


def execute_strands_agent_task(
    agent_name: str,
    task_data: Dict[str, Any],
    context_messages: List[Any],
) -> Dict[str, Any]:
    """
    Invokes the appropriate Strands SDK agent instance with task parameters.

    Args:
        agent_name: Name of the target Strands agent (e.g., 'calendar_agent', 'email_agent').
        task_data: Dictionary containing task parameters, action type, and descriptions.
        context_messages: Current dialogue/execution message state.

    Returns:
        Dict containing execution results, output text, and generated tool calls.
    """
    logger.info("Initializing Strands SDK agent '%s' for action: %s", agent_name, task_data.get("action_type"))

    # Placeholder for Strands SDK Client integration
    # In full deployment: from strands_sdk import StrandsAgentClient
    # agent_client = StrandsAgentClient.get_agent(agent_name)
    
    action_type = task_data.get("action_type", "GENERIC_TASK")
    parameters = task_data.get("parameters", {})
    description = task_data.get("description", "")

    try:
        # Mocking / Dispatching Strands SDK tool execution logic
        logger.info("Strands SDK Agent [%s] running tool '%s' with params: %s", agent_name, action_type, parameters)

        # Output payload returned by Strands agent after processing environment tools
        result_output = (
            f"Successfully executed task '{action_type}' via Strands Agent [{agent_name}]. "
            f"Details: {description}"
        )

        return {
            "status": "success",
            "output": result_output,
            "tool_calls": [
                {
                    "name": action_type,
                    "args": parameters,
                    "id": f"call_{int(timezone.now().timestamp())}",
                }
            ],
            "execution_metadata": {
                "agent_name": agent_name,
                "timestamp": timezone.now().isoformat(),
                "status_code": 200,
            },
        }

    except Exception as exc:
        logger.error("Strands SDK Agent [%s] execution failed: %s", agent_name, exc, exc_info=True)
        raise StrandsAgentExecutionError(f"Agent '{agent_name}' failed to execute: {str(exc)}") from exc


def strands_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph execution node for Strands SDK Agent tool invocation.

    1. Extracts the active task and assigned agent from graph state.
    2. Runs the tool via Strands SDK.
    3. Increments task index and evaluates graph completion.

    Args:
        state: Shared LangGraph state dictionary.

    Returns:
        Dict[str, Any]: State update dictionary to merge into AgentState.
    """
    thread_id = state.get("thread_id", "unknown_thread")
    current_index = state.get("current_task_index", 0)
    plan_tasks = state.get("plan_tasks", [])
    current_task = state.get("current_task") or (plan_tasks[current_index] if plan_tasks and current_index < len(plan_tasks) else None)
    assigned_agent = state.get("current_agent", "StrandsAgent")

    logger.info(
        "Entering strands_agent_node [Thread: %s] | Step %d/%d | Agent: %s",
        thread_id,
        current_index + 1,
        len(plan_tasks),
        assigned_agent,
    )

    if not current_task:
        logger.warning("strands_agent_node invoked with no active task. Marking complete.")
        return {
            "is_complete": True,
            "requires_human_approval": False,
        }

    # Execute Strands SDK Agent task
    try:
        execution_result = execute_strands_agent_task(
            agent_name=assigned_agent,
            task_data=current_task,
            context_messages=state.get("messages", []),
        )

        # Update message state with agent output
        agent_message = AIMessage(
            content=execution_result["output"],
            name=assigned_agent,
            additional_kwargs={"execution_metadata": execution_result["execution_metadata"]},
        )

        updated_messages = list(state.get("messages", []))
        updated_messages.append(agent_message)

        # Advance task index
        next_index = current_index + 1
        is_workflow_finished = next_index >= len(plan_tasks)

        next_task = plan_tasks[next_index] if not is_workflow_finished else None

        logger.info(
            "Completed task %d/%d. Workflow finished: %s",
            current_index + 1,
            len(plan_tasks),
            is_workflow_finished,
        )

        return {
            "messages": updated_messages,
            "current_task_index": next_index,
            "current_task": next_task,
            "requires_human_approval": False,
            "pending_action": None,
            "is_approved": False,
            "is_complete": is_workflow_finished,
            "last_executed_agent": assigned_agent,
            "updated_at": timezone.now().isoformat(),
        }

    except StrandsAgentExecutionError as err:
        logger.error("Strands node failed for thread %s: %s", thread_id, err)
        return {
            "error": str(err),
            "is_complete": True,
            "requires_human_approval": False,
        }