"""Workflow definitions for document processing."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from idp.models.workflow import WorkflowState


@dataclass
class StepDefinition:
    """Definition of a workflow step."""

    name: str
    description: str
    handler: str  # Fully qualified name of handler function/method
    required: bool = True
    depends_on: list[str] = field(default_factory=list)
    condition: Callable[[WorkflowState], bool] | None = None
    on_error: str = "fail"  # "fail", "skip", "continue"
    timeout_ms: int | None = None

    def should_run(self, state: WorkflowState) -> bool:
        """Check if this step should run based on condition."""
        if self.condition is None:
            return True
        return self.condition(state)


@dataclass
class WorkflowDefinition:
    """Definition of a complete workflow."""

    name: str
    description: str
    steps: list[StepDefinition]
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_step(self, name: str) -> StepDefinition | None:
        """Get a step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None


def _classification_needed(state: WorkflowState) -> bool:
    """Check if classification is needed."""
    return state.context.get("document_type") is None


def _extraction_possible(state: WorkflowState) -> bool:
    """Check if extraction is possible."""
    doc_type = state.context.get("document_type")
    return doc_type is not None and doc_type != "unknown"


# Standard document processing workflow
StandardDocumentWorkflow = WorkflowDefinition(
    name="standard_document_processing",
    description="Standard workflow: Classify → Extract → Validate",
    steps=[
        StepDefinition(
            name="classify",
            description="Classify the document type",
            handler="classification",
            required=True,
            condition=_classification_needed,
        ),
        StepDefinition(
            name="extract",
            description="Extract structured data from the document",
            handler="extraction",
            required=True,
            depends_on=["classify"],
            condition=_extraction_possible,
        ),
        StepDefinition(
            name="validate",
            description="Validate the extracted data",
            handler="validation",
            required=False,
            depends_on=["extract"],
            on_error="continue",
        ),
    ],
)
