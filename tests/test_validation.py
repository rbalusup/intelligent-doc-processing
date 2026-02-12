"""Tests for validation agent."""

from datetime import date
from decimal import Decimal

import pytest

from idp.agents.validation import (
    ValidationAgent,
    ValidationInput,
    ValidationOutput,
    ValidationIssue,
    IssueSeverity,
    ValidationRuleRegistry,
)
from idp.agents.validation.rules import (
    RequiredFieldRule,
    DateOrderRule,
    PositiveAmountRule,
    TotalMatchesSubtotalPlusTaxRule,
)
from idp.models.document import Document, DocumentPage, DocumentType
from idp.models.extraction import InvoiceExtraction, ReceiptExtraction, LineItem


class TestValidationIssue:
    """Tests for ValidationIssue model."""

    def test_issue_creation(self) -> None:
        """Test creating a validation issue."""
        issue = ValidationIssue(
            field="invoice_number",
            severity=IssueSeverity.ERROR,
            message="Missing invoice number",
            rule="required_invoice_number",
        )
        assert issue.field == "invoice_number"
        assert issue.severity == IssueSeverity.ERROR

    def test_issue_to_dict(self) -> None:
        """Test converting issue to dictionary."""
        issue = ValidationIssue(
            field="amount",
            severity=IssueSeverity.WARNING,
            message="Amount seems high",
            rule="amount_range",
            expected="< 10000",
            actual=50000,
        )
        d = issue.to_dict()
        assert d["field"] == "amount"
        assert d["severity"] == "warning"
        assert d["actual"] == 50000


class TestValidationOutput:
    """Tests for ValidationOutput model."""

    def test_output_counts(self) -> None:
        """Test issue counting."""
        output = ValidationOutput(valid=False, rules_checked=5, rules_passed=2)
        output.add_issue(ValidationIssue(
            field="f1", severity=IssueSeverity.ERROR, message="Error 1", rule="r1"
        ))
        output.add_issue(ValidationIssue(
            field="f2", severity=IssueSeverity.ERROR, message="Error 2", rule="r2"
        ))
        output.add_issue(ValidationIssue(
            field="f3", severity=IssueSeverity.WARNING, message="Warning 1", rule="r3"
        ))
        output.add_issue(ValidationIssue(
            field="f4", severity=IssueSeverity.INFO, message="Info 1", rule="r4"
        ))

        assert output.error_count == 2
        assert output.warning_count == 1
        assert output.info_count == 1

    def test_get_issues_by_field(self) -> None:
        """Test filtering issues by field."""
        output = ValidationOutput(valid=False, rules_checked=2, rules_passed=0)
        output.add_issue(ValidationIssue(
            field="amount", severity=IssueSeverity.ERROR, message="E1", rule="r1"
        ))
        output.add_issue(ValidationIssue(
            field="date", severity=IssueSeverity.WARNING, message="W1", rule="r2"
        ))
        output.add_issue(ValidationIssue(
            field="amount", severity=IssueSeverity.WARNING, message="W2", rule="r3"
        ))

        amount_issues = output.get_issues_by_field("amount")
        assert len(amount_issues) == 2


class TestValidationRules:
    """Tests for individual validation rules."""

    def test_required_field_rule_missing(self) -> None:
        """Test required field rule with missing value."""
        rule = RequiredFieldRule("invoice_number", [DocumentType.INVOICE])
        extraction = InvoiceExtraction(invoice_number=None)

        issues = rule.validate(extraction)

        assert len(issues) == 1
        assert issues[0].field == "invoice_number"
        assert issues[0].severity == IssueSeverity.ERROR

    def test_required_field_rule_present(self) -> None:
        """Test required field rule with present value."""
        rule = RequiredFieldRule("invoice_number", [DocumentType.INVOICE])
        extraction = InvoiceExtraction(invoice_number="INV-001")

        issues = rule.validate(extraction)

        assert len(issues) == 0

    def test_date_order_rule_valid(self) -> None:
        """Test date order rule with valid order."""
        rule = DateOrderRule("invoice_date", "due_date", [DocumentType.INVOICE])
        extraction = InvoiceExtraction(
            invoice_date=date(2024, 1, 1),
            due_date=date(2024, 2, 1),
        )

        issues = rule.validate(extraction)

        assert len(issues) == 0

    def test_date_order_rule_invalid(self) -> None:
        """Test date order rule with invalid order."""
        rule = DateOrderRule("invoice_date", "due_date", [DocumentType.INVOICE])
        extraction = InvoiceExtraction(
            invoice_date=date(2024, 3, 1),
            due_date=date(2024, 1, 1),
        )

        issues = rule.validate(extraction)

        assert len(issues) == 1
        assert "must be before" in issues[0].message

    def test_positive_amount_rule_valid(self) -> None:
        """Test positive amount rule with valid amount."""
        rule = PositiveAmountRule("total_amount", [DocumentType.INVOICE])
        extraction = InvoiceExtraction(total_amount=Decimal("100"))

        issues = rule.validate(extraction)

        assert len(issues) == 0

    def test_positive_amount_rule_negative(self) -> None:
        """Test positive amount rule with negative amount."""
        rule = PositiveAmountRule("total_amount", [DocumentType.INVOICE])
        extraction = InvoiceExtraction(total_amount=Decimal("-50"))

        issues = rule.validate(extraction)

        assert len(issues) == 1
        assert "must be positive" in issues[0].message

    def test_total_matches_calculation_valid(self) -> None:
        """Test total calculation rule with matching values."""
        rule = TotalMatchesSubtotalPlusTaxRule()
        extraction = InvoiceExtraction(
            subtotal=Decimal("100"),
            tax_amount=Decimal("10"),
            total_amount=Decimal("110"),
        )

        issues = rule.validate(extraction)

        assert len(issues) == 0

    def test_total_matches_calculation_invalid(self) -> None:
        """Test total calculation rule with mismatched values."""
        rule = TotalMatchesSubtotalPlusTaxRule()
        extraction = InvoiceExtraction(
            subtotal=Decimal("100"),
            tax_amount=Decimal("10"),
            total_amount=Decimal("200"),  # Wrong!
        )

        issues = rule.validate(extraction)

        assert len(issues) == 1
        assert "does not match" in issues[0].message


class TestValidationAgent:
    """Tests for ValidationAgent."""

    @pytest.fixture
    def agent(self) -> ValidationAgent:
        """Create validation agent."""
        return ValidationAgent()

    @pytest.fixture
    def sample_document(self) -> Document:
        """Create a sample document."""
        return Document(
            id="doc-001",
            pages=[DocumentPage(page_number=1, content="Test content")],
        )

    @pytest.mark.asyncio
    async def test_validate_valid_invoice(
        self, agent: ValidationAgent, sample_document: Document
    ) -> None:
        """Test validating a valid invoice."""
        extraction = InvoiceExtraction(
            invoice_number="INV-001",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            subtotal=Decimal("100"),
            tax_amount=Decimal("10"),
            total_amount=Decimal("110"),
        )
        input_data = ValidationInput(
            document=sample_document,
            document_type=DocumentType.INVOICE,
            extraction=extraction,
        )

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.valid is True
        assert result.output.error_count == 0

    @pytest.mark.asyncio
    async def test_validate_invalid_invoice(
        self, agent: ValidationAgent, sample_document: Document
    ) -> None:
        """Test validating an invalid invoice."""
        extraction = InvoiceExtraction(
            invoice_number=None,  # Missing required field
            invoice_date=date(2024, 3, 1),
            due_date=date(2024, 1, 1),  # Due before invoice date
            total_amount=Decimal("-100"),  # Negative amount
        )
        input_data = ValidationInput(
            document=sample_document,
            document_type=DocumentType.INVOICE,
            extraction=extraction,
        )

        result = await agent.process(input_data)

        assert result.success is True  # Agent completed successfully
        assert result.output is not None
        assert result.output.valid is False  # But validation failed
        assert result.output.error_count >= 2  # Multiple errors

    @pytest.mark.asyncio
    async def test_validate_receipt(
        self, agent: ValidationAgent, sample_document: Document
    ) -> None:
        """Test validating a receipt."""
        extraction = ReceiptExtraction(
            merchant_name="Coffee Shop",
            transaction_date=date(2024, 1, 20),
            subtotal=Decimal("10"),
            tax_amount=Decimal("0.80"),
            total_amount=Decimal("10.80"),
        )
        input_data = ValidationInput(
            document=sample_document,
            document_type=DocumentType.RECEIPT,
            extraction=extraction,
        )

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        assert result.output.valid is True

    @pytest.mark.asyncio
    async def test_strict_mode(
        self, agent: ValidationAgent, sample_document: Document
    ) -> None:
        """Test strict mode treats warnings as errors."""
        extraction = InvoiceExtraction(
            invoice_number="INV-001",
            subtotal=Decimal("100"),
            tax_amount=Decimal("10"),
            total_amount=Decimal("115"),  # Doesn't match (warning)
        )
        input_data = ValidationInput(
            document=sample_document,
            document_type=DocumentType.INVOICE,
            extraction=extraction,
            strict_mode=True,
        )

        result = await agent.process(input_data)

        assert result.success is True
        assert result.output is not None
        # In strict mode, warning causes failure
        assert result.output.valid is False

    @pytest.mark.asyncio
    async def test_agent_metrics(
        self, agent: ValidationAgent, sample_document: Document
    ) -> None:
        """Test that validation returns metrics."""
        extraction = InvoiceExtraction(invoice_number="INV-001")
        input_data = ValidationInput(
            document=sample_document,
            document_type=DocumentType.INVOICE,
            extraction=extraction,
        )

        result = await agent.process(input_data)

        assert result.success is True
        assert "duration_ms" in result.metrics
        assert result.metrics["agent"] == "ValidationAgent"
