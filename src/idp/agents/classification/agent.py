"""Classification agent implementation."""

import json

from idp.agents.base import BaseAgent
from idp.agents.classification.models import ClassificationInput, ClassificationOutput
from idp.agents.classification.prompts import (
    CLASSIFICATION_JSON_SCHEMA,
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_PROMPT_TEMPLATE,
)
from idp.core.exceptions import LLMError
from idp.llm.client import LLMMessage, MessageRole
from idp.models.document import DocumentType


class ClassificationAgent(BaseAgent[ClassificationInput, ClassificationOutput]):
    """Agent for classifying document types."""

    @property
    def name(self) -> str:
        """Get the agent name."""
        return "ClassificationAgent"

    def _get_document_text(self, input_data: ClassificationInput) -> tuple[str, int]:
        """Extract text from document pages up to the limit."""
        pages = input_data.document.pages[: input_data.max_pages]
        text_parts = []

        for page in pages:
            text_parts.append(f"[Page {page.page_number}]\n{page.content}")

        return "\n\n".join(text_parts), len(pages)

    async def _execute(self, input_data: ClassificationInput) -> ClassificationOutput:
        """Execute the classification."""
        document_text, analyzed_pages = self._get_document_text(input_data)

        self._logger.debug(
            "Classifying document",
            document_id=input_data.document.id,
            analyzed_pages=analyzed_pages,
            text_length=len(document_text),
        )

        # Build messages
        messages = [
            LLMMessage(
                role=MessageRole.USER,
                content=CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
                    document_text=document_text
                ),
            ),
        ]

        # Get classification from LLM
        response = await self._llm_client.generate_json(
            messages=messages,
            schema=CLASSIFICATION_JSON_SCHEMA,
            system=CLASSIFICATION_SYSTEM_PROMPT,
            temperature=0.0,  # Deterministic for classification
        )

        # Parse response
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as e:
            raise LLMError(
                "Failed to parse classification response",
                details={"content": response.content, "error": str(e)},
            ) from e

        # Map to DocumentType
        doc_type_str = result.get("document_type", "unknown").lower()
        try:
            document_type = DocumentType(doc_type_str)
        except ValueError:
            self._logger.warning(
                "Unknown document type returned",
                document_type=doc_type_str,
            )
            document_type = DocumentType.UNKNOWN

        return ClassificationOutput(
            document_type=document_type,
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", "No reasoning provided"),
            analyzed_pages=analyzed_pages,
        )
