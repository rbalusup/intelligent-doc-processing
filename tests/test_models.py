"""Tests for data models."""

from datetime import date
from decimal import Decimal

import pytest

from idp.models.document import (
    Document,
    DocumentPage,
    DocumentType,
    DocumentMetadata,
    DocumentStatus,
)
from idp.models.extraction import (
    Address,
    Party,
    LineItem,
    InvoiceExtraction,
    ReceiptExtraction,
)
from idp.models.workflow import (
    WorkflowState,
    WorkflowStep,
    WorkflowResult,
    StepStatus,
)


class TestDocumentModels:
    """Tests for document models."""

    def test_document_page_creation(self) -> None:
        """Test creating a document page."""
        page = DocumentPage(
            page_number=1,
            content="Test content",
        )
        assert page.page_number == 1
        assert page.content == "Test content"
        assert page.has_image is False

    def test_document_page_with_image(self) -> None:
        """Test document page with image."""
        page = DocumentPage(
            page_number=1,
            content="Test",
            image_base64="base64data",
        )
        assert page.has_image is True

    def test_document_creation(self) -> None:
        """Test creating a document."""
        doc = Document(
            id="doc-001",
            pages=[
                DocumentPage(page_number=1, content="Page 1"),
                DocumentPage(page_number=2, content="Page 2"),
            ],
        )
        assert doc.id == "doc-001"
        assert doc.page_count == 2
        assert doc.status == DocumentStatus.PENDING

    def test_document_full_text(self) -> None:
        """Test getting full document text."""
        doc = Document(
            id="doc-001",
            pages=[
                DocumentPage(page_number=1, content="First"),
                DocumentPage(page_number=2, content="Second"),
            ],
        )
        assert doc.full_text == "First\n\nSecond"

    def test_document_get_page(self) -> None:
        """Test getting a specific page."""
        doc = Document(
            id="doc-001",
            pages=[
                DocumentPage(page_number=1, content="Page 1"),
                DocumentPage(page_number=2, content="Page 2"),
            ],
        )
        page = doc.get_page(2)
        assert page is not None
        assert page.content == "Page 2"

        assert doc.get_page(99) is None


class TestExtractionModels:
    """Tests for extraction models."""

    def test_address_is_complete(self) -> None:
        """Test address completeness check."""
        incomplete = Address(street="123 Main St")
        assert incomplete.is_complete is False

        complete = Address(city="New York", state="NY")
        assert complete.is_complete is True

    def test_line_item_calculate_total(self) -> None:
        """Test line item total calculation."""
        item = LineItem(
            description="Service",
            quantity=Decimal("10"),
            unit_price=Decimal("100"),
        )
        assert item.calculate_total() == Decimal("1000")

        item_with_total = LineItem(
            description="Service",
            total=Decimal("500"),
        )
        assert item_with_total.calculate_total() == Decimal("500")

    def test_invoice_extraction(self) -> None:
        """Test invoice extraction model."""
        invoice = InvoiceExtraction(
            invoice_number="INV-001",
            invoice_date=date(2024, 1, 15),
            total_amount=Decimal("1000.00"),
            currency="USD",
            line_items=[
                LineItem(description="Item 1", total=Decimal("500")),
                LineItem(description="Item 2", total=Decimal("500")),
            ],
        )
        assert invoice.invoice_number == "INV-001"
        assert invoice.calculate_subtotal() == Decimal("1000")

    def test_receipt_extraction(self) -> None:
        """Test receipt extraction model."""
        receipt = ReceiptExtraction(
            merchant_name="Coffee Shop",
            transaction_date=date(2024, 1, 20),
            total_amount=Decimal("9.99"),
            payment_method="VISA",
        )
        assert receipt.merchant_name == "Coffee Shop"
        assert receipt.total_amount == Decimal("9.99")


class TestWorkflowModels:
    """Tests for workflow models."""

    def test_workflow_step_creation(self) -> None:
        """Test creating a workflow step."""
        step = WorkflowStep(name="classify")
        assert step.name == "classify"
        assert step.status == StepStatus.PENDING
        assert step.duration_ms is None

    def test_workflow_state_add_step(self) -> None:
        """Test adding steps to workflow state."""
        state = WorkflowState(
            workflow_id="wf-001",
            document_id="doc-001",
        )
        step = state.add_step("classify")
        assert step.name == "classify"
        assert len(state.steps) == 1
        assert state.get_step("classify") is not None

    def test_workflow_result_from_state(self) -> None:
        """Test creating result from state."""
        state = WorkflowState(
            workflow_id="wf-001",
            document_id="doc-001",
            status=StepStatus.COMPLETED,
        )
        state.add_step("classify")

        result = WorkflowResult.from_state(state)
        assert result.success is True
        assert result.metrics["step_count"] == 1
