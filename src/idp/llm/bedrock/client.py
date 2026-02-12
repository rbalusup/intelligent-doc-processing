"""AWS Bedrock LLM client implementation."""

import asyncio
import json
import time
from typing import Any

import boto3
from botocore.config import Config

from idp.core.config import Settings, get_settings
from idp.core.exceptions import LLMError
from idp.core.logging import get_logger
from idp.llm.client import BaseLLMClient, LLMMessage, LLMResponse, MessageRole

logger = get_logger(__name__)


class BedrockClient(BaseLLMClient):
    """AWS Bedrock LLM client with async wrapper."""

    def __init__(
        self,
        settings: Settings | None = None,
        model_id: str | None = None,
    ) -> None:
        """Initialize Bedrock client.

        Args:
            settings: Application settings
            model_id: Override model ID
        """
        self._settings = settings or get_settings()
        self._model_id = model_id or self._settings.bedrock_model_id

        # Configure boto3 client
        boto_config = Config(
            region_name=self._settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )

        client_kwargs: dict[str, Any] = {"config": boto_config}

        if self._settings.aws_profile:
            session = boto3.Session(profile_name=self._settings.aws_profile)
            self._client = session.client("bedrock-runtime", **client_kwargs)
        else:
            if self._settings.aws_endpoint_url:
                client_kwargs["endpoint_url"] = self._settings.aws_endpoint_url
            self._client = boto3.client("bedrock-runtime", **client_kwargs)

        logger.info(
            "Initialized Bedrock client",
            model_id=self._model_id,
            region=self._settings.aws_region,
        )

    @property
    def model_id(self) -> str:
        """Get the model identifier."""
        return self._model_id

    def _build_messages(
        self,
        messages: list[LLMMessage],
    ) -> list[dict[str, Any]]:
        """Build messages for Bedrock API."""
        result = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # System messages are handled separately
                continue
            result.append({
                "role": msg.role.value,
                "content": [{"type": "text", "text": msg.content}],
            })
        return result

    def _extract_system_prompt(
        self,
        messages: list[LLMMessage],
        system: str | None,
    ) -> str | None:
        """Extract system prompt from messages or parameter."""
        if system:
            return system
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                return msg.content
        return None

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        system: str | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        """Generate a response using Bedrock."""
        max_tokens = max_tokens or self._settings.bedrock_max_tokens
        temperature = temperature if temperature is not None else self._settings.bedrock_temperature

        system_prompt = self._extract_system_prompt(messages, system)
        api_messages = self._build_messages(messages)

        request_body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": api_messages,
        }

        if temperature is not None:
            request_body["temperature"] = temperature

        if system_prompt:
            request_body["system"] = system_prompt

        if stop_sequences:
            request_body["stop_sequences"] = stop_sequences

        logger.debug(
            "Calling Bedrock",
            model_id=self._model_id,
            message_count=len(api_messages),
        )

        start_time = time.perf_counter()

        try:
            # Run synchronous boto3 call in thread pool
            response = await asyncio.to_thread(
                self._client.invoke_model,
                modelId=self._model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )
        except self._client.exceptions.ThrottlingException as e:
            raise LLMError(
                "Rate limited by Bedrock",
                details={"error": str(e)},
                retryable=True,
            ) from e
        except self._client.exceptions.ModelTimeoutException as e:
            raise LLMError(
                "Bedrock model timed out",
                details={"error": str(e)},
                retryable=True,
            ) from e
        except Exception as e:
            raise LLMError(
                f"Bedrock API error: {e}",
                details={"error": str(e)},
                retryable=False,
            ) from e

        latency_ms = (time.perf_counter() - start_time) * 1000

        response_body = json.loads(response["body"].read())

        # Extract content from response
        content = ""
        if response_body.get("content"):
            for block in response_body["content"]:
                if block.get("type") == "text":
                    content += block.get("text", "")

        usage = response_body.get("usage", {})

        logger.debug(
            "Bedrock response received",
            latency_ms=latency_ms,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )

        return LLMResponse(
            content=content,
            model=self._model_id,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=latency_ms,
            stop_reason=response_body.get("stop_reason"),
            raw_response=response_body,
        )

    async def generate_json(
        self,
        messages: list[LLMMessage],
        schema: dict[str, Any],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Generate a JSON response using Bedrock."""
        # Build system prompt with JSON schema
        schema_str = json.dumps(schema, indent=2)
        json_system = f"""You must respond with valid JSON matching this schema:

{schema_str}

Respond ONLY with the JSON object, no additional text or markdown formatting."""

        if system:
            json_system = f"{system}\n\n{json_system}"

        # Ensure we don't duplicate system from messages
        filtered_messages = [m for m in messages if m.role != MessageRole.SYSTEM]

        response = await self.generate(
            filtered_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=json_system,
            stop_sequences=None,
        )

        # Validate JSON response
        content = response.content.strip()

        # Handle potential markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            content = content.strip()

        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(
                "Invalid JSON response from LLM",
                content=content[:200],
                error=str(e),
            )
            raise LLMError(
                "LLM returned invalid JSON",
                details={"content": content[:500], "error": str(e)},
                retryable=True,
            ) from e

        return LLMResponse(
            content=content,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
            stop_reason=response.stop_reason,
            raw_response=response.raw_response,
        )
