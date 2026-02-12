"""Validation rules and registry."""

import re
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any, TypeVar

from idp.agents.validation.models import IssueSeverity, ValidationIssue
from idp.models.document import DocumentType
from idp.models.extraction import (
    BaseExtraction,
)

T = TypeVar("T", bound=BaseExtraction)


class ValidationRule(ABC):
    """Abstract base class for validation rules."""

    def __init__(
        self,
        name: str,
        description: str,
        severity: IssueSeverity = IssueSeverity.ERROR,
        document_types: list[DocumentType] | None = None,
    ) -> None:
        """Initialize validation rule.

        Args:
            name: Rule name/identifier
            description: Human-readable description
            severity: Default severity for issues from this rule
            document_types: Document types this rule applies to (None = all)
        """
        self.name = name
        self.description = description
        self.severity = severity
        self.document_types = document_types

    def applies_to(self, document_type: DocumentType) -> bool:
        """Check if this rule applies to a document type."""
        if self.document_types is None:
            return True
        return document_type in self.document_types

    @abstractmethod
    def validate(self, extraction: BaseExtraction) -> list[ValidationIssue]:
        """Validate the extraction and return any issues found."""
        ...


class ValidationRuleRegistry:
    """Registry for validation rules."""

    _instance: "ValidationRuleRegistry | None" = None
    _rules: list[ValidationRule]

    def __new__(cls) -> "ValidationRuleRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rules = []
        return cls._instance

    def register(self, rule: ValidationRule) -> None:
        """Register a validation rule."""
        self._rules.append(rule)

    def get_rules(self, document_type: DocumentType) -> list[ValidationRule]:
        """Get all rules that apply to a document type."""
        return [r for r in self._rules if r.applies_to(document_type)]

    def clear(self) -> None:
        """Clear all registered rules (for testing)."""
        self._rules = []

    @property
    def all_rules(self) -> list[ValidationRule]:
        """Get all registered rules."""
        return self._rules.copy()


def register_rule(rule: ValidationRule) -> ValidationRule:
    """Register a rule with the global registry."""
    ValidationRuleRegistry().register(rule)
    return rule


# ============================================================
# Format Validation Rules
# ============================================================


class RequiredFieldRule(ValidationRule):
    """Validate that required fields are present."""

    def __init__(
        self,
        field_name: str,
        document_types: list[DocumentType] | None = None,
    ) -> None:
        super().__init__(
            name=f"required_{field_name}",
            description=f"Field '{field_name}' is required",
            severity=IssueSeverity.ERROR,
            document_types=document_types,
        )
        self.field_name = field_name

    def validate(self, extraction: BaseExtraction) -> list[ValidationIssue]:
        value = getattr(extraction, self.field_name, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            return [
                ValidationIssue(
                    field=self.field_name,
                    severity=self.severity,
                    message=f"Required field '{self.field_name}' is missing or empty",
                    rule=self.name,
                    expected="non-empty value",
                    actual=value,
                )
            ]
        return []


class DateFormatRule(ValidationRule):
    """Validate date fields have proper format."""

    def __init__(
        self,
        field_name: str,
        document_types: list[DocumentType] | None = None,
    ) -> None:
        super().__init__(
            name=f"date_format_{field_name}",
            description=f"Field '{field_name}' must be a valid date",
            severity=IssueSeverity.WARNING,
            document_types=document_types,
        )
        self.field_name = field_name

    def validate(self, extraction: BaseExtraction) -> list[ValidationIssue]:
        value = getattr(extraction, self.field_name, None)
        if value is None:
            return []  # Not present, handled by required rule
        if isinstance(value, date):
            return []  # Already a valid date
        return [
            ValidationIssue(
                field=self.field_name,
                severity=self.severity,
                message=f"Field '{self.field_name}' is not a valid date",
                rule=self.name,
                expected="date object",
                actual=type(value).__name__,
            )
        ]


class PositiveAmountRule(ValidationRule):
    """Validate that amount fields are positive."""

    def __init__(
        self,
        field_name: str,
        document_types: list[DocumentType] | None = None,
    ) -> None:
        super().__init__(
            name=f"positive_amount_{field_name}",
            description=f"Field '{field_name}' must be positive",
            severity=IssueSeverity.ERROR,
            document_types=document_types,
        )
        self.field_name = field_name

    def validate(self, extraction: BaseExtraction) -> list[ValidationIssue]:
        value = getattr(extraction, self.field_name, None)
        if value is None:
            return []
        if isinstance(value, (int, float, Decimal)) and value < 0:
            return [
                ValidationIssue(
                    field=self.field_name,
                    severity=self.severity,
                    message=f"Field '{self.field_name}' must be positive",
                    rule=self.name,
                    expected=">= 0",
                    actual=value,
                )
            ]
        return []


class EmailFormatRule(ValidationRule):
    """Validate email address format."""

    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def __init__(
        self,
        field_path: str,
        document_types: list[DocumentType] | None = None,
    ) -> None:
        super().__init__(
            name=f"email_format_{field_path}",
            description=f"Field '{field_path}' must be a valid email",
            severity=IssueSeverity.WARNING,
            document_types=document_types,
        )
        self.field_path = field_path

    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """Get value from nested object using dot notation."""
        parts = path.split(".")
        value = obj
        for part in parts:
            if value is None:
                return None
            value = getattr(value, part, None)
        return value

    def validate(self, extraction: BaseExtraction) -> list[ValidationIssue]:
        value = self._get_nested_value(extraction, self.field_path)
        if value is None or not isinstance(value, str):
            return []
        if not self.EMAIL_PATTERN.match(value):
            return [
                ValidationIssue(
                    field=self.field_path,
                    severity=self.severity,
                    message=f"Invalid email format in '{self.field_path}'",
                    rule=self.name,
                    expected="valid email address",
                    actual=value,
                )
            ]
        return []


# ============================================================
# Cross-Field Validation Rules
# ============================================================


class DateOrderRule(ValidationRule):
    """Validate that one date comes before another."""

    def __init__(
        self,
        earlier_field: str,
        later_field: str,
        document_types: list[DocumentType] | None = None,
    ) -> None:
        super().__init__(
            name=f"date_order_{earlier_field}_{later_field}",
            description=f"'{earlier_field}' must be before '{later_field}'",
            severity=IssueSeverity.ERROR,
            document_types=document_types,
        )
        self.earlier_field = earlier_field
        self.later_field = later_field

    def validate(self, extraction: BaseExtraction) -> list[ValidationIssue]:
        earlier = getattr(extraction, self.earlier_field, None)
        later = getattr(extraction, self.later_field, None)

        if earlier is None or later is None:
            return []
        if not isinstance(earlier, date) or not isinstance(later, date):
            return []
        if earlier > later:
            return [
                ValidationIssue(
                    field=f"{self.earlier_field},{self.later_field}",
                    severity=self.severity,
                    message=f"'{self.earlier_field}' must be before '{self.later_field}'",
                    rule=self.name,
                    expected=f"{self.earlier_field} <= {self.later_field}",
                    actual=f"{earlier} > {later}",
                )
            ]
        return []


class TotalMatchesSubtotalPlusTaxRule(ValidationRule):
    """Validate that total equals subtotal plus tax."""

    def __init__(self) -> None:
        super().__init__(
            name="total_matches_calculation",
            description="Total must equal subtotal plus tax",
            severity=IssueSeverity.WARNING,
            document_types=[DocumentType.INVOICE, DocumentType.RECEIPT],
        )

    def validate(self, extraction: BaseExtraction) -> list[ValidationIssue]:
        subtotal = getattr(extraction, "subtotal", None)
        tax = getattr(extraction, "tax_amount", None)
        total = getattr(extraction, "total_amount", None)

        if subtotal is None or total is None:
            return []

        tax_value = tax if tax is not None else Decimal(0)

        expected_total = Decimal(str(subtotal)) + Decimal(str(tax_value))
        actual_total = Decimal(str(total))

        # Allow small tolerance for floating point
        if abs(expected_total - actual_total) > Decimal("0.01"):
            return [
                ValidationIssue(
                    field="total_amount",
                    severity=self.severity,
                    message="Total does not match subtotal plus tax",
                    rule=self.name,
                    expected=float(expected_total),
                    actual=float(actual_total),
                )
            ]
        return []


class LineItemsTotalRule(ValidationRule):
    """Validate that line items sum to subtotal."""

    def __init__(self) -> None:
        super().__init__(
            name="line_items_total",
            description="Line items must sum to subtotal",
            severity=IssueSeverity.INFO,
            document_types=[DocumentType.INVOICE, DocumentType.RECEIPT],
        )

    def validate(self, extraction: BaseExtraction) -> list[ValidationIssue]:
        line_items = getattr(extraction, "line_items", None)
        subtotal = getattr(extraction, "subtotal", None)

        if not line_items or subtotal is None:
            return []

        items_total = Decimal(0)
        for item in line_items:
            item_total = item.calculate_total()
            if item_total is not None:
                items_total += item_total

        expected_subtotal = Decimal(str(subtotal))

        if abs(items_total - expected_subtotal) > Decimal("0.01"):
            return [
                ValidationIssue(
                    field="line_items",
                    severity=self.severity,
                    message="Line items do not sum to subtotal",
                    rule=self.name,
                    expected=float(expected_subtotal),
                    actual=float(items_total),
                )
            ]
        return []


# ============================================================
# Register Default Rules
# ============================================================


def register_default_rules() -> None:
    """Register all default validation rules."""
    registry = ValidationRuleRegistry()

    # Invoice rules
    registry.register(
        RequiredFieldRule("invoice_number", [DocumentType.INVOICE])
    )
    registry.register(
        RequiredFieldRule("total_amount", [DocumentType.INVOICE, DocumentType.RECEIPT])
    )
    registry.register(
        DateFormatRule("invoice_date", [DocumentType.INVOICE])
    )
    registry.register(
        DateOrderRule("invoice_date", "due_date", [DocumentType.INVOICE])
    )
    registry.register(
        PositiveAmountRule("total_amount", [DocumentType.INVOICE, DocumentType.RECEIPT])
    )

    # Receipt rules
    registry.register(
        RequiredFieldRule("merchant_name", [DocumentType.RECEIPT])
    )
    registry.register(
        DateFormatRule("transaction_date", [DocumentType.RECEIPT])
    )

    # Contract rules
    registry.register(
        DateOrderRule("effective_date", "expiration_date", [DocumentType.CONTRACT])
    )

    # Cross-field rules
    registry.register(TotalMatchesSubtotalPlusTaxRule())
    registry.register(LineItemsTotalRule())


# Auto-register default rules on module import
register_default_rules()
