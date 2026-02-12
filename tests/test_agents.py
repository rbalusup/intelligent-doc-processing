"""Tests for agents."""

import json
import pytest

from idp.agents.base import AgentResult, BaseAgent
from idp.agents.classification import (
    ClassificationAgent,
    ClassificationInput,
    ClassificationOutput,
)
from idp.llm.mock.client import MockLLMClient, MockResponse, create_classification_mock
from idp.models.document import Document, DocumentPage, DocumentType


class TestAgentResult:
    """Tests for AgentResult."""

    def test_success_result(self) -> None:
        """Test creating a successful result."""
        result = AgentResult.success_result(
            output={"key": "value"},
            metrics={"duration_ms": 100},
        )
        assert result.success is True
        assert result.output == {"key": "value"}
        assert result.error is None
        assert result.metrics["duration_ms"] == 100

    def test_failure_result(self) -> None:
        """Test creating a failed result."""
        result: AgentResult[str] = AgentResult.failure_result(
            error="Something went wrong",
            metrics={"attempts": 3},
        )
        assert result.success is False
        assert result.output is None
        assert result.error == "Something went wrong"


class TestClassificationAgent:
    """Tests for ClassificationAgent."""

    @pytest.fixture
    def mock_client(self) -> MockLLMClient:
        """Create a mock LLM client."""
        return create_classification_mock()

    @pytest.fixture
    def agent(self, mock_client: MockLLMClient) -> ClassificationAgent:
        """Create classification agent with mock client."""
        return ClassificationAgent(llm_client=mock_client)

    @pytest.mark.asyncio
    async def test_classify_invoice(
        self,
        agent: ClassificationAgent,
        sample_invoice_text: str,
    ) -> None:
        """Test classifying an invoice document."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        )
        input_data = ClassificationInput(document=doc)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.document_type == DocumentType.INVOICE
        assert result.output.confidence > 0.8
        assert "invoice" in result.output.reasoning.lower()

    @pytest.mark.asyncio
    async def test_classify_receipt(
        self,
        agent: ClassificationAgent,
        sample_receipt_text: str,
    ) -> None:
        """Test classifying a receipt document."""
        doc = Document(
            id="rcpt-001",
            pages=[DocumentPage(page_number=1, content=sample_receipt_text)],
        )
        input_data = ClassificationInput(document=doc)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.document_type == DocumentType.RECEIPT

    @pytest.mark.asyncio
    async def test_classify_contract(
        self,
        agent: ClassificationAgent,
        sample_contract_text: str,
    ) -> None:
        """Test classifying a contract document."""
        doc = Document(
            id="contract-001",
            pages=[DocumentPage(page_number=1, content=sample_contract_text)],
        )
        input_data = ClassificationInput(document=doc)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.document_type == DocumentType.CONTRACT

    @pytest.mark.asyncio
    async def test_classify_form(
        self,
        agent: ClassificationAgent,
        sample_form_text: str,
    ) -> None:
        """Test classifying a form document."""
        doc = Document(
            id="form-001",
            pages=[DocumentPage(page_number=1, content=sample_form_text)],
        )
        input_data = ClassificationInput(document=doc)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.document_type == DocumentType.FORM

    @pytest.mark.asyncio
    async def test_multi_page_document(
        self,
        mock_client: MockLLMClient,
    ) -> None:
        """Test classification with multiple pages."""
        agent = ClassificationAgent(llm_client=mock_client)

        doc = Document(
            id="multi-001",
            pages=[
                DocumentPage(page_number=1, content="Invoice Header"),
                DocumentPage(page_number=2, content="Invoice Line Items"),
                DocumentPage(page_number=3, content="Invoice Total"),
                DocumentPage(page_number=4, content="Terms and Conditions"),
            ],
        )
        input_data = ClassificationInput(document=doc, max_pages=2)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.analyzed_pages == 2

    @pytest.mark.asyncio
    async def test_agent_metrics(
        self,
        agent: ClassificationAgent,
        sample_invoice_text: str,
    ) -> None:
        """Test that agent returns metrics."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        )
        input_data = ClassificationInput(document=doc)

        result = await agent.process(input_data)

        assert result.success is True
        assert "duration_ms" in result.metrics
        assert "agent" in result.metrics
        assert result.metrics["agent"] == "ClassificationAgent"

    @pytest.mark.asyncio
    async def test_classification_output_properties(self) -> None:
        """Test ClassificationOutput properties."""
        confident = ClassificationOutput(
            document_type=DocumentType.INVOICE,
            confidence=0.95,
            reasoning="High confidence",
            analyzed_pages=1,
        )
        assert confident.is_confident is True

        not_confident = ClassificationOutput(
            document_type=DocumentType.UNKNOWN,
            confidence=0.5,
            reasoning="Low confidence",
            analyzed_pages=1,
        )
        assert not_confident.is_confident is False
