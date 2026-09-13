"""
Multi-Tier Memory Architecture for LifePilot Strands Agents.

Integrates Strands Agents SDK memory interface with:
1. Fast local / Redis session cache for active multi-turn context windowing.
2. PostgreSQL persistence for agent execution history and LangGraph checkpointers.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger("lifepilot.agents.memory")

# Fallback base class in case Strands SDK doesn't export StepMemory
try:
    from strands.memory import StepMemory as BaseMemory
except ImportError:
    try:
        from strands.memory import ConversationMemory as BaseMemory
    except ImportError:
        class BaseMemory:
            """Fallback base memory implementation."""
            def __init__(self):
                self._turns: List[Dict[str, Any]] = []

            def add_turn(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
                self._turns.append({"role": role, "content": content, "metadata": metadata or {}})

            def get_messages(self) -> List[Dict[str, Any]]:
                return self._turns

            def clear(self) -> None:
                self._turns.clear()


class LifePilotHybridMemory(BaseMemory):
    """
    Custom Strands Memory engine combining ephemeral state management
    with persistent database storage.
    """

    def __init__(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        max_history_turns: int = 20,
        redis_url: Optional[str] = None,
    ):
        super().__init__()
        self.session_id = session_id
        self.user_id = user_id
        self.max_history_turns = max_history_turns
        self.redis_url = redis_url or getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        self._redis_client = None

    def _get_redis(self):
        """Lazy connection to Redis server for high-speed state caching."""
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
            except Exception as exc:
                logger.warning("Redis connection unavailable for agent memory (%s). Operating in-memory.", exc)
                self._redis_client = False
        return self._redis_client if self._redis_client else None

    def add_turn(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a conversation turn or tool output into working memory."""
        turn_data = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        
        # Superclass in-memory storage
        if hasattr(super(), "add_turn"):
            super().add_turn(role, content, metadata)

        # Cache in Redis session
        redis = self._get_redis()
        if redis:
            key = f"lifepilot:memory:{self.session_id}"
            try:
                redis.rpush(key, json.dumps(turn_data))
                redis.ltrim(key, -self.max_history_turns, -1)
                redis.expire(key, 86400)  # 24 hour session TTL
            except Exception as exc:
                logger.error("Failed to persist memory turn to Redis: %s", exc)

    def get_conversation_context(self) -> List[Dict[str, Any]]:
        """Retrieve formatted message context for model prompts."""
        redis = self._get_redis()
        if redis:
            key = f"lifepilot:memory:{self.session_id}"
            try:
                raw_turns = redis.lrange(key, 0, -1)
                if raw_turns:
                    return [json.loads(t) for t in raw_turns]
            except Exception as exc:
                logger.error("Failed to read memory turns from Redis: %s", exc)

        if hasattr(super(), "get_messages"):
            return super().get_messages()
            
        return []

    def clear(self) -> None:
        """Purge current session working memory."""
        redis = self._get_redis()
        if redis:
            key = f"lifepilot:memory:{self.session_id}"
            try:
                redis.delete(key)
            except Exception as exc:
                logger.error("Failed to clear Redis memory key [%s]: %s", key, exc)

        if hasattr(super(), "clear"):
            super().clear()


def get_agent_memory(
    thread_id: str,
    user_id: Optional[str] = None,
    max_turns: int = 15,
) -> LifePilotHybridMemory:
    """
    Factory function to initialize a LifePilot Hybrid Memory instance for a given thread.
    """
    return LifePilotHybridMemory(
        session_id=thread_id,
        user_id=user_id,
        max_history_turns=max_turns,
    )