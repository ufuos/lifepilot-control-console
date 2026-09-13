"""
LangGraph Workflow Orchestration Engine for LifePilot Control Console.

Assembles state transitions across Planner, Strands Agents SDK primitives, and
Human Approval nodes, persisting graph execution checkpoints via Django / Redis checkpointers.
"""

import logging
from typing import Any, Dict, Literal
from langgraph.graph import END, START, StateGraph

# Native Strands SDK Imports
from strands import Agent, tool
from strands.models import BedrockModel

from apps.agents.graph.checkpointer import get_graph_checkpointer
from apps.agents.graph.nodes.human_approval import human_approval_node
from apps.agents.graph.nodes.planner import planner_node
from apps.agents.graph.nodes.strands_node import strands_agent_node
from apps.agents.graph.state import AgentState

logger = logging.getLogger(__name__)

# ============================================================================
# 1. STRANDS AGENTS SDK TOOL DEFINITIONS & INSTANTIATION
# ============================================================================


@tool
def execute_aws_ec2_scale(action: str, count: int) -> Dict[str, Any]:
    """Scales AWS EC2 instances based on current system load or user requests."""
    logger.info("Executing Strands Tool [execute_aws_ec2_scale]: action=%s, count=%d", action, count)
    return {
        "status": "SUCCESS",
        "action": action,
        "count": count,
        "message": f"Successfully executed EC2 scale operation ({action}) for {count} instance(s).",
    }


@tool
def send_slack_notification(channel: str, message: str) -> Dict[str, Any]:
    """Sends Slack alert notification to specified team or operations channel."""
    logger.info("Executing Strands Tool [send_slack_notification]: channel=%s", channel)
    return {
        "status": "DELIVERED",
        "channel": channel,
        "message": f"Alert posted to Slack channel #{channel}.",
    }


# Initialize Strands Bedrock Model (Amazon Bedrock Integration)
bedrock_model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
    region_name="us-east-1",
)

# Instantiate Native Strands Agent Execution Unit
lifepilot_strands_agent = Agent(
    model=bedrock_model,
    tools=[execute_aws_ec2_scale, send_slack_notification],
    system_prompt=(
        "You are the LifePilot Control Console autonomous execution agent. "
        "Run routine infrastructure management, monitoring, and notification tasks using registered tools. "
        "Strictly defer high-risk actions to human approval gates."
    ),
)


# ============================================================================
# 2. STATE GRAPH ROUTING FUNCTIONS
# ============================================================================


def route_after_planner(state: AgentState) -> Literal["strands_agent", "human_approval", "end"]:
    """
    Determines next execution node following task planning.
    """
    if state.get("is_complete", False):
        return "end"

    if state.get("requires_human_approval", False) and state.get("pending_action"):
        logger.info("Planner flagged high-risk task. Routing to human_approval.")
        return "human_approval"

    return "strands_agent"


def route_after_agent_execution(state: AgentState) -> Literal["human_approval", "planner", "end"]:
    """
    Evaluates state after Strands agent tool execution.
    """
    if state.get("requires_human_approval", False) and state.get("pending_action"):
        return "human_approval"

    if state.get("is_complete", False):
        return "end"

    # Evaluate remaining tasks in active plan
    tasks = state.get("plan_tasks", [])
    current_idx = state.get("current_task_index", 0)

    if current_idx < len(tasks):
        return "planner"

    return "end"


def route_after_human_approval(state: AgentState) -> Literal["strands_agent", "planner", "end"]:
    """
    Routes graph execution after human operator submits approval or rejection.
    """
    is_approved = state.get("is_approved", False)

    if not is_approved:
        logger.info("Human rejected action for thread: %s. Terminating workflow.", state.get("thread_id"))
        return "end"

    # Action approved: proceed to Strands agent node to execute payload
    return "strands_agent"


# ============================================================================
# 3. WORKFLOW GRAPH BUILDER
# ============================================================================


def build_lifepilot_workflow() -> StateGraph:
    """
    Constructs and connects the State Graph workflow nodes and conditional branches.

    Workflow Structure:
        [START] -> planner -> (conditional) -> strands_agent -> (conditional) -> [END]
                                   │                     │
                                   └─> human_approval <──┘
    """
    builder = StateGraph(AgentState)

    # 1. Register Core Graph Execution Nodes
    builder.add_node("planner", planner_node)
    builder.add_node("strands_agent", strands_agent_node)
    builder.add_node("human_approval", human_approval_node)

    # 2. Define Entry Connection
    builder.add_edge(START, "planner")

    # 3. Add Conditional Routing Edges
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "strands_agent": "strands_agent",
            "human_approval": "human_approval",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "strands_agent",
        route_after_agent_execution,
        {
            "human_approval": "human_approval",
            "planner": "planner",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "human_approval",
        route_after_human_approval,
        {
            "strands_agent": "strands_agent",
            "planner": "planner",
            "end": END,
        },
    )

    return builder


def get_compiled_graph():
    """
    Compiles the LifePilot workflow graph with state persistence checkpointer enabled.
    """
    workflow_builder = build_lifepilot_workflow()
    checkpointer = get_graph_checkpointer()

    compiled_graph = workflow_builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"],
    )
    return compiled_graph


# Pre-compiled executable graph instance for module import
lifepilot_graph = get_compiled_graph()