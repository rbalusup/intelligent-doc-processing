"""Tests for extraction agent."""

from datetime import date
from decimal import Decimal

import pytest

from idp.agents.extraction import ExtractionAgent, ExtractionInput, ExtractionOutput
from idp.llm.mock.client import create_extraction_mock, MockLLMClient
from idp.models.document import Document, DocumentPage, DocumentType
from idp.models.extraction import InvoiceExtraction, ReceiptExtraction


class TestExtractionAgent:
    """Tests for ExtractionAgent."""

    @pytest.fixture
    def mock_client(self) -> MockLLMClient:
        """Create a mock LLM client for extraction."""
        return create_extraction_mock()

    @pytest.fixture
    def agent(self, mock_client: MockLLMClient) -> ExtractionAgent:
        """Create extraction agent with mock client."""
        return ExtractionAgent(llm_client=mock_client)

    @pytest.mark.asyncio
    async def test_extract_invoice(
        self,
        agent: ExtractionAgent,
        sample_invoice_text: str,
    ) -> None:
        """Test extracting data from an invoice."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        )
        input_data = ExtractionInput(document=doc, document_type=DocumentType.INVOICE)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.document_type == DocumentType.INVOICE
        assert isinstance(result.output.extraction, InvoiceExtraction)

        extraction = result.output.extraction
        assert extraction.invoice_number == "INV-2024-001"
        assert extraction.invoice_date == date(2024, 1, 15)
        assert extraction.due_date == date(2024, 2, 15)
        assert extraction.total_amount == Decimal("2160")
        assert len(extraction.line_items) == 2

    @pytest.mark.asyncio
    async def test_extract_receipt(
        self,
        agent: ExtractionAgent,
        sample_receipt_text: str,
    ) -> None:
        """Test extracting data from a receipt."""
        doc = Document(
            id="rcpt-001",
            pages=[DocumentPage(page_number=1, content=sample_receipt_text)],
        )
        input_data = ExtractionInput(document=doc, document_type=DocumentType.RECEIPT)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.document_type == DocumentType.RECEIPT
        assert isinstance(result.output.extraction, ReceiptExtraction)

        extraction = result.output.extraction
        assert extraction.merchant_name == "Coffee Shop"
        assert extraction.transaction_date == date(2024, 1, 20)
        assert extraction.total_amount == Decimal("9.99")
        assert extraction.payment_method == "VISA"

    @pytest.mark.asyncio
    async def test_extract_contract(
        self,
        agent: ExtractionAgent,
        sample_contract_text: str,
    ) -> None:
        """Test extracting data from a contract."""
        doc = Document(
            id="contract-001",
            pages=[DocumentPage(page_number=1, content=sample_contract_text)],
        )
        input_data = ExtractionInput(document=doc, document_type=DocumentType.CONTRACT)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.document_type == DocumentType.CONTRACT

        extraction = result.output.extraction
        assert extraction.effective_date == date(2024, 3, 1)
        assert extraction.governing_law == "Delaware"

    @pytest.mark.asyncio
    async def test_extract_form(
        self,
        agent: ExtractionAgent,
        sample_form_text: str,
    ) -> None:
        """Test extracting data from a form."""
        doc = Document(
            id="form-001",
            pages=[DocumentPage(page_number=1, content=sample_form_text)],
        )
        input_data = ExtractionInput(document=doc, document_type=DocumentType.FORM)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.document_type == DocumentType.FORM

        extraction = result.output.extraction
        assert extraction.form_title == "Application Form"
        assert "Name" in extraction.fields
        assert extraction.checkboxes.get("terms_agreed") is True

    @pytest.mark.asyncio
    async def test_extraction_field_count(
        self,
        agent: ExtractionAgent,
        sample_invoice_text: str,
    ) -> None:
        """Test that field count is tracked."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        )
        input_data = ExtractionInput(document=doc, document_type=DocumentType.INVOICE)

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.field_count > 0

    @pytest.mark.asyncio
    async def test_extraction_metrics(
        self,
        agent: ExtractionAgent,
        sample_invoice_text: str,
    ) -> None:
        """Test that extraction returns metrics."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        )
        input_data = ExtractionInput(document=doc, document_type=DocumentType.INVOICE)

        result = await agent.process(input_data)

        assert result.success is True
        assert "duration_ms" in result.metrics
        assert "agent" in result.metrics
        assert result.metrics["agent"] == "ExtractionAgent"


class TestExtractionOutput:
    """Tests for ExtractionOutput."""

    def test_from_invoice(self) -> None:
        """Test creating output from invoice extraction."""
        extraction = InvoiceExtraction(
            invoice_number="INV-001",
            invoice_date=date(2024, 1, 15),
            total_amount=Decimal("100"),
        )
        raw = {"invoice_number": "INV-001"}

        output = ExtractionOutput.from_invoice(extraction, raw)

        assert output.document_type == DocumentType.INVOICE
        assert output.field_count >= 3

    def test_from_receipt(self) -> None:
        """Test creating output from receipt extraction."""
        extraction = ReceiptExtraction(
            merchant_name="Store",
            total_amount=Decimal("50"),
        )
        raw = {"merchant_name": "Store"}

        output = ExtractionOutput.from_receipt(extraction, raw)

        assert output.document_type == DocumentType.RECEIPT
        assert output.field_count >= 2
