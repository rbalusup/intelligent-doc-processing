"""AWS Bedrock service wrapper for Agent Runtime and Knowledge Base interactions."""

import boto3
from botocore.config import Config
from typing import Any, AsyncGenerator

from idp.core.config import get_settings
from idp.core.logging import get_logger

logger = get_logger(__name__)


class BedrockService:
    """Service for interacting with AWS Bedrock Agents and Knowledge Bases."""

    def __init__(self) -> None:
        """Initialize Bedrock service."""
        settings = get_settings()
        
        config = Config(
            region_name=settings.aws_region,
            read_timeout=900,
            connect_timeout=900,
            retries={"max_attempts": 3}
        )

        session_kwargs = {}
        if settings.aws_profile:
            session_kwargs["profile_name"] = settings.aws_profile

        session = boto3.Session(**session_kwargs)
        
        # Initialize Agent Runtime client
        client_kwargs = {"config": config}
        if settings.aws_endpoint_url:
            client_kwargs["endpoint_url"] = settings.aws_endpoint_url

        self._agent_runtime = session.client("bedrock-agent-runtime", **client_kwargs)
        self._kb_id = settings.bedrock_kb_id
        self._agent_id = settings.bedrock_agent_id
        self._agent_alias_id = settings.bedrock_agent_alias_id

    async def retrieve(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve information from Knowledge Base.
        
        Args:
            query: Search query
            kb_id: Knowledge Base ID (overrides default)
            limit: Maximum number of results
            
        Returns:
            List of retrieved results
        """
        target_kb_id = kb_id or self._kb_id
        if not target_kb_id:
            logger.warning("No Knowledge Base ID configured")
            return []

        try:
            response = self._agent_runtime.retrieve(
                knowledgeBaseId=target_kb_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": limit
                    }
                }
            )
            return response.get("retrievalResults", [])
        except Exception as e:
            logger.error("Failed to retrieve from Knowledge Base", error=str(e))
            return []

    async def invoke_agent(
        self,
        input_text: str,
        session_id: str,
        agent_id: str | None = None,
        agent_alias_id: str | None = None,
        enable_trace: bool = False,
    ) -> AsyncGenerator[str, None]:
        """Invoke a Bedrock Agent.
        
        Args:
            input_text: Input text for the agent
            session_id: Session identifier
            agent_id: Agent ID (overrides default)
            agent_alias_id: Agent Alias ID (overrides default)
            enable_trace: Whether to enable tracing
            
        Yields:
            Chunks of the agent response
        """
        target_agent_id = agent_id or self._agent_id
        target_alias_id = agent_alias_id or self._agent_alias_id

        if not target_agent_id or not target_alias_id:
            logger.error("Agent ID or Alias ID not configured")
            raise ValueError("Agent ID and Alias ID must be provided")

        try:
            response = self._agent_runtime.invoke_agent(
                agentId=target_agent_id,
                agentAliasId=target_alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=enable_trace,
            )

            # Stream the response
            event_stream = response.get("completion")
            for event in event_stream:
                if "chunk" in event:
                    yield event["chunk"]["bytes"].decode("utf-8")
                elif "trace" in event and enable_trace:
                     logger.debug("Agent Trace", trace=event["trace"])

        except Exception as e:
            logger.error("Failed to invoke Bedrock Agent", error=str(e))
            raise
