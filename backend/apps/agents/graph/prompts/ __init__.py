"""
LangGraph System Prompts and Template Formatter Package for LifePilot Control Console.

Centralizes system prompts, task decomposition instructions, tool execution rules,
and security evaluation rubrics for multi-agent graph nodes.
"""

from typing import Any, Dict, List, Optional

# ============================================================================
# 1. PLANNER NODE PROMPTS
# ============================================================================

PLANNER_SYSTEM_PROMPT = """You are the Lead Task Planner in the LifePilot multi-agent ecosystem.
Your primary responsibility is to analyze the user's high-level goal, evaluate current state context,
and decompose objectives into structured, executable sub-tasks for specialized agents.

CORE RESPONSIBILITIES:
1. Decompose complex user goals into atomic, sequentially ordered sub-tasks.
2. Route tasks to the appropriate sub-agent capability (e.g., 'calendar_agent', 'email_agent', 'system_executor', 'analytics_agent').
3. Evaluate safety constraints and risk levels ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') for every task.
4. Flag actions requiring explicit Human-in-the-Loop (HITL) authorization (`requires_human_approval = True`) when tasks involve:
   - External communication (sending emails, messaging contacts).
   - Destructive operations (deleting data, revoking access, altering infrastructure).
   - Financial or transactional operations.
   - Modifying core system settings.

OUTPUT COMPLIANCE:
Maintain strict adherence to task state schema and provide unambiguous, contextual parameters for downstream agents.
"""

PLANNER_REPLAN_PROMPT = """You are re-evaluating an active plan in response to new feedback or completed steps.

Previous Plan State:
{previous_plan}

Completed Task Result / Human Feedback:
{execution_feedback}

Determine if the remaining steps require modification, re-sequencing, or if new sub-tasks must be appended to satisfy the original goal:
Goal: {user_goal}
"""


# ============================================================================
# 2. STRANDS AGENT EXECUTION PROMPTS
# ============================================================================

STRANDS_AGENT_SYSTEM_PROMPT = """You are an Execution Agent powered by the Strands SDK operating within the LifePilot platform.
You carry out specific tools and procedural sub-tasks assigned to you by the Lead Planner.

OPERATIONAL RULES:
1. Execute tools safely and deterministically according to parameter specifications.
2. Produce structured state outputs containing tool responses, execution logs, and diagnostic state updates.
3. NEVER attempt to execute destructive, external, or high-risk tools directly if marked as requiring human approval.
4. If an unexpected runtime exception or authorization boundary occurs, halt execution gracefully and return detailed error context.

Current Assigned Agent Context: {agent_name}
Available Tool Capabilities: {tool_capabilities}
"""


# ============================================================================
# 3. HUMAN APPROVAL EVALUATION PROMPTS
# ============================================================================

HUMAN_APPROVAL_SUMMARY_PROMPT = """You are the HITL Approval Evaluator. Synthesize the pending high-risk action into a clear, non-technical explanation for human operators in the LifePilot UI.

Pending Action Details:
- Action Type: {action_type}
- Target Capability / Agent: {agent_name}
- Risk Level: {risk_level}
- Parameters: {parameters}

Generate a concise summary detailing:
1. What changes will be enacted if authorized.
2. Potential side effects or risks of proceeding.
3. Recommended confirmation message for the operator dashboard.
"""


# ============================================================================
# 4. PROMPT HELPER / FORMATTER FUNCTIONS
# ============================================================================

def format_planner_prompt(
    user_goal: str,
    context_history: Optional[List[Dict[str, Any]]] = None,
    system_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Formats the context prompt for the Planner Node.

    Args:
        user_goal: The raw objective stated by the user.
        context_history: Recent conversation or execution context messages.
        system_metadata: Additional operational environment flags.

    Returns:
        Formatted context string ready for LLM invocation.
    """
    history_str = "None"
    if context_history:
        history_str = "\n".join([f"- {msg.get('role', 'user')}: {msg.get('content', '')}" for msg in context_history[-5:]])

    meta_str = "Standard Execution"
    if system_metadata:
        meta_str = ", ".join([f"{k}={v}" for k, v in system_metadata.items()])

    return (
        f"User Goal:\n{user_goal}\n\n"
        f"System Metadata Context:\n{meta_str}\n\n"
        f"Recent History Context:\n{history_str}"
    )


def format_strands_agent_prompt(
    task_title: str,
    task_description: str,
    parameters: Dict[str, Any],
    feedback_notes: Optional[str] = None,
) -> str:
    """
    Formats the target instruction prompt for Strands SDK tool execution nodes.
    """
    prompt = (
        f"Task Title: {task_title}\n"
        f"Task Description: {task_description}\n"
        f"Parameters: {parameters}"
    )
    if feedback_notes:
        prompt += f"\nHuman / Supervisor Feedback: {feedback_notes}"
    return prompt


__all__ = [
    "PLANNER_SYSTEM_PROMPT",
    "PLANNER_REPLAN_PROMPT",
    "STRANDS_AGENT_SYSTEM_PROMPT",
    "HUMAN_APPROVAL_SUMMARY_PROMPT",
    "format_planner_prompt",
    "format_strands_agent_prompt",
]