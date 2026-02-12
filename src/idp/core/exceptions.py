"""Custom exceptions for the IDP system."""

from typing import Any


class IDPError(Exception):
    """Base exception for all IDP errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ConfigurationError(IDPError):
    """Raised when there's a configuration problem."""

    pass


class LLMError(IDPError):
    """Raised when LLM operations fail."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message, details)
        self.retryable = retryable


class AgentError(IDPError):
    """Raised when an agent operation fails."""

    def __init__(
        self,
        message: str,
        agent_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.agent_name = agent_name


class ValidationError(IDPError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.field = field


class StorageError(IDPError):
    """Raised when storage operations fail."""

    pass


class WorkflowError(IDPError):
    """Raised when workflow execution fails."""

    def __init__(
        self,
        message: str,
        workflow_id: str | None = None,
        step_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.workflow_id = workflow_id
        self.step_name = step_name
