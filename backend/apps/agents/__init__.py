"""
LifePilot Agents Application Package.

Engineered for the AWS 'Agents for Humans' Hackathon. Integrates the Strands Agents SDK,
AWS Bedrock / AgentCore runtime primitives, LangGraph state orchestration,
and Human-in-the-Loop (HITL) authorization workflows across Everyday, Professional,
and Good Neighbor agent tracks.
"""

# Set Django default app config module name for legacy/compatibility support
default_app_config = "apps.agents.apps.AgentsConfig"


def __getattr__(name: str):
    """
    Lazy import handler to prevent `django.core.exceptions.AppRegistryNotReady`
    during module startup before Django calls django.setup().
    """
    if name == "StrandsAgentCallbackHandler":
        from apps.agents.strands.callbacks import StrandsAgentCallbackHandler
        return StrandsAgentCallbackHandler

    if name in ("LifePilotHybridMemory", "get_agent_memory"):
        from apps.agents.strands.memory import LifePilotHybridMemory, get_agent_memory
        return LifePilotHybridMemory if name == "LifePilotHybridMemory" else get_agent_memory

    if name in (
        "BASE_AGENT_DIRECTIVE",
        "EVERYDAY_TRACK_PROMPT",
        "PROFESSIONAL_TRACK_PROMPT",
        "GOOD_NEIGHBOR_TRACK_PROMPT",
        "get_agent_system_prompt",
        "get_track_instructions",
    ):
        from apps.agents.strands import system_prompts
        return getattr(system_prompts, name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # Telemetry & Callbacks
    "StrandsAgentCallbackHandler",
    # Hybrid Session Memory
    "LifePilotHybridMemory",
    "get_agent_memory",
    # Track-Specific Prompting
    "BASE_AGENT_DIRECTIVE",
    "EVERYDAY_TRACK_PROMPT",
    "PROFESSIONAL_TRACK_PROMPT",
    "GOOD_NEIGHBOR_TRACK_PROMPT",
    "get_agent_system_prompt",
    "get_track_instructions",
]