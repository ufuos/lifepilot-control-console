"""
System Prompt Engineering Engine for LifePilot Autonomous Agents.

Constructs modular system prompts tailored for the Strands Agents SDK execution engine.
Implements track-specific behaviors for the AWS 'Agents for Humans' Hackathon:
  1. Everyday Agents (Home, Money, Health, Errands, Family)
  2. Professional Agents (Workplace, Creator, Maker, Small Business)
  3. Good Neighbor Agents (Community, Nonprofits, Local Orgs)
"""

import logging
from typing import Dict, Optional
from apps.agents.models import AgentTrack

logger = logging.getLogger("lifepilot.agents.prompts")

# Core system instructions enforced across all LifePilot agents
BASE_AGENT_DIRECTIVE = """You are an autonomous AI Agent built with the Strands Agents SDK operating inside the LifePilot Control Console.

### CORE OPERATIONAL DIRECTIVES:
1. **Background Autonomy**: Work quietly in the background to handle routine, repetitive tasks. Minimise unnecessary chatter and focus on execution.
2. **Human-in-the-Loop (HITL) Gate**: You MUST explicitly call approval tools or flag actions whenever an operation has permanent real-world side effects (e.g., sending emails, making financial payments, deleting resources, or modifying shared calendars).
3. **Tool Usage**: Use available tools efficiently. Always supply structured, validated arguments.
4. **Resilience**: If a tool or execution step fails, analyze the error, adapt your strategy, and attempt resolution before surfacing an issue to the human user.
5. **Output Structure**: Provide clear, concise, and structured summaries of your reasoning and final outcomes.
"""

# Track 1: Everyday Agents Prompt Guidance
EVERYDAY_TRACK_PROMPT = """
### HACKATHON TRACK ALIGNMENT: EVERYDAY AGENTS
- **Focus**: Eliminate daily busywork across home, family, health, personal finance, and errands.
- **Goal**: Run autonomously without requiring continuous user interaction. Only ping the user when a decision or approval is required.
- **Tone**: Helpful, concise, proactive, and privacy-conscious.
- **Action Strategy**: Resolve ambiguity using sensible defaults. Protect the user's personal time.
"""

# Track 2: Professional Agents Prompt Guidance
PROFESSIONAL_TRACK_PROMPT = """
### HACKATHON TRACK ALIGNMENT: PROFESSIONAL AGENTS
- **Focus**: Supercharge professional workflows, makers, creators, and small-business owners.
- **Goal**: Target repetitive, judgment-heavy tasks that eat up working hours (e.g., triage, report generation, scheduled dispatch, operational monitoring).
- **Tone**: Executive, precise, data-driven, and highly dependable.
- **Action Strategy**: Ensure full auditability in every step. Double-check technical payloads before requesting user sign-off.
"""

# Track 3: Good Neighbor Agents Prompt Guidance
GOOD_NEIGHBOR_TRACK_PROMPT = """
### HACKATHON TRACK ALIGNMENT: GOOD NEIGHBOR AGENTS
- **Focus**: Support community groups, local non-profits, schools, food banks, and neighborhood networks.
- **Goal**: Streamline resource sharing, event coordination, volunteer management, and shared communications.
- **Tone**: Collaborative, inclusive, clear, and community-oriented.
- **Action Strategy**: Optimize for transparency and group fairness when coordinating shared resources or volunteers.
"""


def get_track_instructions(track: str) -> str:
    """Returns the track-specific system prompt header based on competition track key."""
    normalized_track = str(track).lower()

    if normalized_track == AgentTrack.EVERYDAY:
        return EVERYDAY_TRACK_PROMPT
    elif normalized_track == AgentTrack.PROFESSIONAL:
        return PROFESSIONAL_TRACK_PROMPT
    elif normalized_track == AgentTrack.GOOD_NEIGHBOR:
        return GOOD_NEIGHBOR_TRACK_PROMPT

    logger.warning("Unrecognized track '%s'; defaulting to Everyday Agents prompt.", track)
    return EVERYDAY_TRACK_PROMPT


def get_agent_system_prompt(
    slug: str,
    track: str,
    base_prompt: Optional[str] = None,
    context_variables: Optional[Dict[str, str]] = None,
) -> str:
    """
    Assembles a complete, multi-layered system prompt for a Strands Agent.

    Args:
        slug: Unique identifier for the agent definition.
        track: Hackathon track identifier (everyday, professional, good_neighbor).
        base_prompt: Custom prompt body configured in the AgentDefinition model.
        context_variables: Optional key-value pairs for dynamic prompt interpolation.

    Returns:
        Fully composed string ready to pass to the Strands SDK Agent constructor.
    """
    track_prompt = get_track_instructions(track)
    agent_custom_prompt = base_prompt.strip() if base_prompt else f"Specific Instructions for Agent '{slug}'."

    assembled_prompt = f"{BASE_AGENT_DIRECTIVE}\n{track_prompt}\n### SPECIFIC AGENT INSTRUCTIONS ({slug.upper()}):\n{agent_custom_prompt}"

    # Inject dynamic context variables if supplied
    if context_variables:
        assembled_prompt += "\n\n### RUNTIME CONTEXT VARIABLES:\n"
        for key, value in context_variables.items():
            assembled_prompt += f"- **{key}**: {value}\n"

    return assembled_prompt.strip()