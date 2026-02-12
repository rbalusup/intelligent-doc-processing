"""Base agent definitions and protocols."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from idp.core.config import Settings, get_settings
from idp.core.exceptions import AgentError
from idp.core.logging import get_logger
from idp.core.retry import RetryConfig, retry_async
from idp.llm.client import BaseLLMClient

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@dataclass
class AgentResult(Generic[OutputT]):
    """Result from an agent execution."""

    success: bool
    output: OutputT | None = None
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success_result(
        cls,
        output: OutputT,
        metrics: dict[str, Any] | None = None,
    ) -> "AgentResult[OutputT]":
        """Create a successful result."""
        return cls(success=True, output=output, metrics=metrics or {})

    @classmethod
    def failure_result(
        cls,
        error: str,
        metrics: dict[str, Any] | None = None,
    ) -> "AgentResult[OutputT]":
        """Create a failed result."""
        return cls(success=False, error=error, metrics=metrics or {})


@runtime_checkable
class AgentProtocol(Protocol[InputT, OutputT]):
    """Protocol for agent implementations."""

    @property
    def name(self) -> str:
        """Agent name."""
        ...

    async def process(self, input_data: InputT) -> AgentResult[OutputT]:
        """Process input and return result."""
        ...


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Abstract base class for agents with common functionality."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        settings: Settings | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            llm_client: LLM client for generating responses
            settings: Application settings
            retry_config: Retry configuration
        """
        self._llm_client = llm_client
        self._settings = settings or get_settings()
        self._retry_config = retry_config or RetryConfig(
            max_attempts=self._settings.retry_max_attempts,
            base_delay=self._settings.retry_base_delay,
            max_delay=self._settings.retry_max_delay,
        )
        self._logger = get_logger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the agent name."""
        ...

    @abstractmethod
    async def _execute(self, input_data: InputT) -> OutputT:
        """Execute the agent logic. Implemented by subclasses."""
        ...

    async def process(self, input_data: InputT) -> AgentResult[OutputT]:
        """Process input with retry and error handling."""
        import time

        start_time = time.perf_counter()
        metrics: dict[str, Any] = {"agent": self.name}

        self._logger.info("Starting agent execution", agent=self.name)

        try:
            output = await retry_async(
                lambda: self._execute(input_data),
                self._retry_config,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000
            metrics["duration_ms"] = duration_ms
            metrics["success"] = True

            self._logger.info(
                "Agent execution completed",
                agent=self.name,
                duration_ms=duration_ms,
            )

            return AgentResult.success_result(output, metrics)

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            metrics["duration_ms"] = duration_ms
            metrics["success"] = False
            metrics["error_type"] = type(e).__name__

            self._logger.error(
                "Agent execution failed",
                agent=self.name,
                error=str(e),
                duration_ms=duration_ms,
            )

            raise AgentError(
                f"Agent {self.name} failed: {e}",
                agent_name=self.name,
                details={"error": str(e), "metrics": metrics},
            ) from e
