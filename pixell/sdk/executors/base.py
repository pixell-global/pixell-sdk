"""Base executor interface for PER tools.

Canonical version — agents can import from here instead of maintaining
their own copy at app/per/executors/base.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    error_code: str | None = None
    recoverable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_content(self) -> str:
        if self.success:
            return self.output
        return f"Error: {self.error}"

    @classmethod
    def success_result(cls, output: str, **metadata: Any) -> "ToolResult":
        return cls(success=True, output=output, metadata=metadata)

    @classmethod
    def error_result(
        cls,
        error: str,
        error_code: str | None = None,
        recoverable: bool = False,
        **metadata: Any,
    ) -> "ToolResult":
        return cls(
            success=False,
            output="",
            error=error,
            error_code=error_code,
            recoverable=recoverable,
            metadata=metadata,
        )


class BaseExecutor(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]: ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult: ...

    def as_tool_schema(self) -> dict[str, Any]:
        """OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def as_anthropic_tool_schema(self) -> dict[str, Any]:
        """Anthropic tool-use format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    async def execute_with_logging(self, session_id: str = "", **kwargs: Any) -> ToolResult:
        """Execute with basic logging (no per_logger dependency)."""
        import logging
        import time

        log = logging.getLogger(f"executor.{self.name}")
        log.info("Executing %s (session=%s, args=%s)", self.name, session_id, kwargs)
        start = time.monotonic()
        try:
            result = await self.execute(**kwargs)
        except Exception:
            elapsed = (time.monotonic() - start) * 1000
            log.exception("Error in %s after %.0fms", self.name, elapsed)
            raise
        elapsed = (time.monotonic() - start) * 1000
        if result.success:
            log.info("%s succeeded in %.0fms (%d chars)", self.name, elapsed, len(result.output))
        else:
            log.warning("%s failed in %.0fms: %s", self.name, elapsed, result.error)
        return result
