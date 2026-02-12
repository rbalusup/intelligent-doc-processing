"""Base LLM client interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MessageRole(StrEnum):
    """Message role in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """A message in the LLM conversation."""

    role: MessageRole
    content: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary format."""
        return {"role": self.role.value, "content": self.content}


@dataclass
class LLMResponse:
    """Response from an LLM call."""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    stop_reason: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "stop_reason": self.stop_reason,
        }


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        system: str | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            messages: Conversation messages
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system: System prompt
            stop_sequences: Stop sequences

        Returns:
            LLM response with content and metadata
        """
        ...

    @abstractmethod
    async def generate_json(
        self,
        messages: list[LLMMessage],
        schema: dict[str, Any],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Generate a JSON response matching the given schema.

        Args:
            messages: Conversation messages
            schema: JSON schema for the response
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system: System prompt

        Returns:
            LLM response with JSON content
        """
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Get the model identifier."""
        ...
