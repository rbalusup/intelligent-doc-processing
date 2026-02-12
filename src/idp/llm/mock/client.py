"""Mock LLM client for deterministic testing."""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from idp.llm.client import BaseLLMClient, LLMMessage, LLMResponse


@dataclass
class MockResponse:
    """A mock response configuration."""

    content: str | dict[str, Any]
    input_tokens: int = 100
    output_tokens: int = 50
    latency_ms: float = 100.0


ResponseGenerator = Callable[[list[LLMMessage]], MockResponse]


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing with deterministic responses."""

    def __init__(
        self,
        default_response: str | MockResponse | None = None,
        responses: dict[str, MockResponse] | None = None,
        response_generator: ResponseGenerator | None = None,
    ) -> None:
        """Initialize mock client.

        Args:
            default_response: Default response for any message
            responses: Map of regex patterns to responses
            response_generator: Function to generate responses dynamically
        """
        self._default_response = default_response or MockResponse(
            content="Mock response"
        )
        self._responses = responses or {}
        self._response_generator = response_generator
        self._call_history: list[dict[str, Any]] = []

    @property
    def model_id(self) -> str:
        """Get the model identifier."""
        return "mock-model"

    @property
    def call_history(self) -> list[dict[str, Any]]:
        """Get history of all calls made."""
        return self._call_history

    def add_response(self, pattern: str, response: MockResponse) -> None:
        """Add a response for a specific message pattern."""
        self._responses[pattern] = response

    def clear_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()

    def _find_response(self, messages: list[LLMMessage]) -> MockResponse:
        """Find matching response for messages."""
        # Check response generator first
        if self._response_generator:
            return self._response_generator(messages)

        # Check pattern-based responses
        last_message = messages[-1].content if messages else ""
        for pattern, response in self._responses.items():
            if re.search(pattern, last_message, re.IGNORECASE):
                return response

        # Return default
        if isinstance(self._default_response, str):
            return MockResponse(content=self._default_response)
        return self._default_response

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        system: str | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        """Generate a mock response."""
        # Record the call
        self._call_history.append({
            "messages": [m.to_dict() for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "stop_sequences": stop_sequences,
        })

        mock_resp = self._find_response(messages)
        content = mock_resp.content
        if isinstance(content, dict):
            content = json.dumps(content)

        return LLMResponse(
            content=content,
            model=self.model_id,
            input_tokens=mock_resp.input_tokens,
            output_tokens=mock_resp.output_tokens,
            latency_ms=mock_resp.latency_ms,
            stop_reason="end_turn",
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
        """Generate a mock JSON response."""
        # Record the call
        self._call_history.append({
            "messages": [m.to_dict() for m in messages],
            "schema": schema,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
        })

        mock_resp = self._find_response(messages)
        content = mock_resp.content

        # Ensure it's JSON
        if isinstance(content, dict):
            content = json.dumps(content)
        elif not content.strip().startswith("{"):
            # Wrap in JSON if not already
            content = json.dumps({"result": content})

        return LLMResponse(
            content=content,
            model=self.model_id,
            input_tokens=mock_resp.input_tokens,
            output_tokens=mock_resp.output_tokens,
            latency_ms=mock_resp.latency_ms,
            stop_reason="end_turn",
        )


# Pre-configured mock responses for common document types
# Order matters - more specific patterns should come first
CLASSIFICATION_RESPONSES: dict[str, MockResponse] = {
    # Receipt patterns - check before invoice since receipts also have totals
    r"coffee\s*shop|thank\s*you|visa\s*\*+": MockResponse(
        content=json.dumps({
            "document_type": "receipt",
            "confidence": 0.92,
            "reasoning": "Document contains merchant information and transaction details."
        })
    ),
    r"receipt|transaction|merchant|payment\s*method": MockResponse(
        content=json.dumps({
            "document_type": "receipt",
            "confidence": 0.92,
            "reasoning": "Document contains merchant information and transaction details."
        })
    ),
    # Invoice patterns
    r"invoice|inv[\-\s]|bill\s*to|payment\s*terms": MockResponse(
        content=json.dumps({
            "document_type": "invoice",
            "confidence": 0.95,
            "reasoning": "Document contains invoice number, line items, and total amount."
        })
    ),
    # Contract patterns
    r"agreement|contract|parties|hereby|governing\s*law": MockResponse(
        content=json.dumps({
            "document_type": "contract",
            "confidence": 0.90,
            "reasoning": "Document contains legal language and party definitions."
        })
    ),
    # Form patterns
    r"form|application|checkbox|\[\s*[xX]?\s*\]": MockResponse(
        content=json.dumps({
            "document_type": "form",
            "confidence": 0.88,
            "reasoning": "Document contains form fields and checkboxes."
        })
    ),
}


def create_classification_mock() -> MockLLMClient:
    """Create a mock client configured for classification."""
    return MockLLMClient(
        responses=CLASSIFICATION_RESPONSES,
        default_response=MockResponse(
            content=json.dumps({
                "document_type": "unknown",
                "confidence": 0.5,
                "reasoning": "Unable to determine document type."
            })
        ),
    )


# Pre-configured mock responses for extraction
EXTRACTION_RESPONSES: dict[str, MockResponse] = {
    # Invoice extraction
    r"invoice": MockResponse(
        content=json.dumps({
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "due_date": "2024-02-15",
            "vendor": {
                "name": "Acme Corporation",
                "address": {
                    "street": "123 Business St",
                    "city": "New York",
                    "state": "NY",
                    "postal_code": "10001",
                },
            },
            "customer": {
                "name": "Customer Inc",
                "address": {
                    "street": "456 Client Ave",
                    "city": "Los Angeles",
                    "state": "CA",
                    "postal_code": "90001",
                },
            },
            "line_items": [
                {"description": "Consulting Services", "quantity": 10, "unit_price": 150, "total": 1500},
                {"description": "Software License", "quantity": 1, "unit_price": 500, "total": 500},
            ],
            "subtotal": 2000,
            "tax_amount": 160,
            "tax_rate": 8,
            "total_amount": 2160,
            "currency": "USD",
            "payment_terms": "Net 30",
        })
    ),
    # Receipt extraction
    r"receipt|coffee|merchant": MockResponse(
        content=json.dumps({
            "merchant_name": "Coffee Shop",
            "merchant_address": {
                "street": "123 Main Street",
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94102",
            },
            "transaction_date": "2024-01-20",
            "transaction_time": "10:30 AM",
            "line_items": [
                {"description": "Latte", "total": 5.50},
                {"description": "Croissant", "total": 3.75},
            ],
            "subtotal": 9.25,
            "tax_amount": 0.74,
            "total_amount": 9.99,
            "payment_method": "VISA",
            "card_last_four": "1234",
            "currency": "USD",
        })
    ),
    # Contract extraction
    r"contract|agreement": MockResponse(
        content=json.dumps({
            "contract_title": "Service Agreement",
            "contract_type": "Service",
            "effective_date": "2024-03-01",
            "expiration_date": "2025-02-28",
            "parties": [
                {"name": "Provider Corp"},
                {"name": "Client LLC"},
            ],
            "governing_law": "Delaware",
            "key_terms": ["Monthly payment", "Service delivery"],
            "total_value": 120000,
            "currency": "USD",
        })
    ),
    # Form extraction
    r"form|application": MockResponse(
        content=json.dumps({
            "form_title": "Application Form",
            "form_type": "Application",
            "form_date": "2024-02-01",
            "submitted_by": {
                "name": "John Smith",
                "email": "john.smith@email.com",
                "phone": "(555) 123-4567",
                "address": {
                    "street": "789 Oak Lane",
                    "city": "Chicago",
                    "state": "IL",
                    "postal_code": "60601",
                },
            },
            "fields": {
                "Name": "John Smith",
                "Email": "john.smith@email.com",
                "Phone": "(555) 123-4567",
            },
            "checkboxes": {
                "terms_agreed": True,
                "newsletter": False,
            },
            "signatures": ["John Smith"],
        })
    ),
}


def create_extraction_mock() -> MockLLMClient:
    """Create a mock client configured for extraction."""
    return MockLLMClient(
        responses=EXTRACTION_RESPONSES,
        default_response=MockResponse(
            content=json.dumps({
                "form_title": "Unknown Form",
                "fields": {},
            })
        ),
    )
