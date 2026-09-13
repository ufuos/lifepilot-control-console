"""
Strands Agents SDK Integration Subpackage.

Provides the core engine, system prompt builders, telemetry callbacks,
and multi-tier memory management for LifePilot autonomous agents.
"""

from apps.agents.strands.agent_runner import LifePilotStrandsRunner
from apps.agents.strands.callbacks import StrandsAgentCallbackHandler
from apps.agents.strands.memory import LifePilotHybridMemory, get_agent_memory
from apps.agents.strands.system_prompts import get_agent_system_prompt, get_track_instructions

__all__ = [
    "LifePilotStrandsRunner",
    "StrandsAgentCallbackHandler",
    "LifePilotHybridMemory",
    "get_agent_memory",
    "get_agent_system_prompt",
    "get_track_instructions",
]