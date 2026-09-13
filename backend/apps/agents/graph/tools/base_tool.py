"""
Base Tool Abstraction for LifePilot Agent Framework.

Defines the abstract base tool interface with built-in risk-level classification,
execution telemetry, parameter schema validation, and Human-in-the-Loop policy checks.
"""

import logging
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from django.utils import timezone
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolExecutionResult(BaseModel):
    """
    Standardized result payload returned by all LifePilot tools.
    """
    success: bool
    tool_name: str
    output: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: timezone.now().isoformat())


class BaseLifePilotTool(ABC):
    """
    Abstract Base Class for all LifePilot tools.

    Provides standardized interfaces for tool metadata, parameter validation,
    risk evaluation, and execution wrapping.
    """

    name: str = "base_tool"
    description: str = "Base tool description."
    args_schema: Optional[Type[BaseModel]] = None
    
    # Risk categorization: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    risk_level: str = "LOW"
    
    # Whether execution strictly requires Human-in-the-Loop (HITL) approval
    requires_approval: bool = False

    def __init__(self):
        if self.risk_level in ["HIGH", "CRITICAL"]:
            self.requires_approval = True

    def get_metadata(self) -> Dict[str, Any]:
        """
        Returns metadata representation of the tool for Planner node registration.
        """
        schema_props = {}
        if self.args_schema:
            schema_props = self.args_schema.schema().get("properties", {})

        return {
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "parameters": schema_props,
        }

    def validate_args(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates arguments against the Pydantic args_schema if provided.
        """
        if self.args_schema:
            validated = self.args_schema(**kwargs)
            return validated.dict()
        return kwargs

    def run(self, **kwargs: Any) -> ToolExecutionResult:
        """
        Executes the tool logic with safety logging and error handling wrappers.
        """
        logger.info(
            "Executing tool '%s' (Risk Level: %s, Requires Approval: %s)",
            self.name,
            self.risk_level,
            self.requires_approval,
        )

        try:
            validated_args = self.validate_args(kwargs)
            result_data = self._execute(**validated_args)

            return ToolExecutionResult(
                success=True,
                tool_name=self.name,
                output=result_data,
                metadata={
                    "risk_level": self.risk_level,
                    "requires_approval": self.requires_approval,
                },
            )

        except Exception as exc:
            error_msg = str(exc)
            logger.error(
                "Tool execution failed for '%s': %s\n%s",
                self.name,
                error_msg,
                traceback.format_exc(),
            )
            return ToolExecutionResult(
                success=False,
                tool_name=self.name,
                error=error_msg,
                metadata={
                    "risk_level": self.risk_level,
                    "exception_type": type(exc).__name__,
                },
            )

    @abstractmethod
    def _execute(self, **kwargs: Any) -> Any:
        """
        Abstract method containing actual tool execution logic to be overridden by subclasses.
        """
        pass