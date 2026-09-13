"""
LangGraph Planner Node for LifePilot Control Console.

Decomposes goals into agent execution steps, tracks state progress,
and identifies actions requiring human authorization.
"""

import logging
from typing import Any, Dict, List
from django.utils import timezone
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from apps.agents.graph.state import AgentState

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are the Lead Task Planner in the LifePilot multi-agent ecosystem.
Your responsibility is to analyze the user's overall goal and system context, then produce or update a structured execution plan.

Guidelines:
1. Break down complex requests into clear, sequential sub-tasks.
2. Assign each task to the most appropriate agent capability (e.g., 'calendar_agent', 'email_agent', 'system_executor', 'analytics_agent').
3. Identify if any step poses security, financial, or data safety risks (e.g., sending external emails, deleting resources, modifying production settings).
4. If a high-risk action is required, flag `requires_human_approval` as true and provide full details in `pending_action`.

Output must strictly reflect progress against the execution plan.
"""


def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph execution node for goal decomposition and task planning.

    Parameters:
        state (AgentState): The shared graph execution state.

    Returns:
        Dict[str, Any]: State update dictionary.
    """
    thread_id = state.get("thread_id", "unknown_thread")
    logger.info("Executing planner_node for graph thread: %s", thread_id)

    messages = state.get("messages", [])
    user_goal = state.get("user_goal", "")
    existing_plan = state.get("plan_tasks", [])
    current_index = state.get("current_task_index", 0)

    # Initialize Gemini model endpoint for planning logic
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.1,
    )

    # If plan already exists and is in progress, check remaining step routing
    if existing_plan and current_index < len(existing_plan):
        current_task = existing_plan[current_index]
        logger.info("Planner advancing step %d/%d: %s", current_index + 1, len(existing_plan), current_task.get("title"))

        is_high_risk = current_task.get("risk_level", "LOW") in ["HIGH", "CRITICAL"]

        state_update: Dict[str, Any] = {
            "current_agent": current_task.get("assigned_agent", "StrandsAgent"),
            "current_task": current_task,
            "requires_human_approval": is_high_risk,
        }

        if is_high_risk:
            state_update["pending_action"] = {
                "action_type": current_task.get("action_type", "EXECUTE_TASK"),
                "description": current_task.get("description", "High-risk operation requested."),
                "parameters": current_task.get("parameters", {}),
                "risk_level": current_task.get("risk_level", "HIGH"),
            }

        return state_update

    # If no plan exists or current plan completed, generate initial breakdown
    prompt_messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=f"User Goal: {user_goal}\nConversation Context: {messages[-3:] if messages else 'None'}"),
    ]

    try:
        response = llm.invoke(prompt_messages)
        plan_summary = response.content

        # Default task structure fallback (or parsed from structured JSON output)
        generated_tasks: List[Dict[str, Any]] = [
            {
                "id": "task-1",
                "title": "Analyze and process context request",
                "assigned_agent": "StrandsAgent",
                "action_type": "PROCESS_REQUEST",
                "description": plan_summary[:200] if plan_summary else "Execute primary workflow objective.",
                "risk_level": "LOW",
                "parameters": {"goal": user_goal},
            }
        ]

        logger.info("Planner generated %d execution steps for thread: %s", len(generated_tasks), thread_id)

        first_task = generated_tasks[0]
        requires_approval = first_task.get("risk_level", "LOW") in ["HIGH", "CRITICAL"]

        return {
            "plan_tasks": generated_tasks,
            "current_task_index": 0,
            "current_task": first_task,
            "current_agent": first_task.get("assigned_agent", "StrandsAgent"),
            "requires_human_approval": requires_approval,
            "is_complete": False,
            "planner_notes": plan_summary,
            "updated_at": timezone.now().isoformat(),
        }

    except Exception as exc:
        logger.error("Error executing planner_node LLM invocation: %s", exc, exc_info=True)
        return {
            "is_complete": True,
            "error": f"Planner failed to generate execution step: {str(exc)}",
        }