"""Validation agent data models."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from idp.models.document import Document, DocumentType
from idp.models.extraction import BaseExtraction


class IssueSeverity(StrEnum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """A validation issue found in the extracted data."""

    field: str = Field(..., description="Field or path with the issue")
    severity: IssueSeverity = Field(default=IssueSeverity.ERROR)
    message: str = Field(..., description="Description of the issue")
    rule: str = Field(..., description="Name of the validation rule that found the issue")
    expected: Any = Field(default=None, description="Expected value or format")
    actual: Any = Field(default=None, description="Actual value found")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "severity": self.severity.value,
            "message": self.message,
            "rule": self.rule,
            "expected": self.expected,
            "actual": self.actual,
        }


class ValidationInput(BaseModel):
    """Input for the validation agent."""

    document: Document
    document_type: DocumentType
    extraction: BaseExtraction
    strict_mode: bool = Field(
        default=False,
        description="If true, warnings are treated as errors",
    )


class ValidationOutput(BaseModel):
    """Output from the validation agent."""

    valid: bool = Field(..., description="Whether the document passed validation")
    issues: list[ValidationIssue] = Field(default_factory=list)
    rules_checked: int = Field(default=0, description="Number of validation rules checked")
    rules_passed: int = Field(default=0, description="Number of rules that passed")

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    @property
    def info_count(self) -> int:
        """Count of info-level issues."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.INFO)

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue."""
        self.issues.append(issue)

    def get_issues_by_field(self, field: str) -> list[ValidationIssue]:
        """Get all issues for a specific field."""
        return [i for i in self.issues if i.field == field]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "rules_checked": self.rules_checked,
            "rules_passed": self.rules_passed,
            "issues": [i.to_dict() for i in self.issues],
        }
