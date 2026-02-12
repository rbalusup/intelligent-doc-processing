"""Workflow-related data models."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StepStatus(StrEnum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep(BaseModel):
    """Represents a single step in a workflow."""

    name: str = Field(..., description="Step name/identifier")
    status: StepStatus = Field(default=StepStatus.PENDING)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    metrics: dict[str, Any] = Field(
        default_factory=dict, description="Step-level metrics (latency, tokens, etc.)"
    )

    @property
    def duration_ms(self) -> float | None:
        """Calculate step duration in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None


class WorkflowState(BaseModel):
    """State of a workflow execution."""

    workflow_id: str = Field(..., description="Unique workflow execution ID")
    document_id: str = Field(..., description="Document being processed")
    current_step: str | None = Field(default=None, description="Currently executing step")
    steps: list[WorkflowStep] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: StepStatus = Field(default=StepStatus.PENDING)
    context: dict[str, Any] = Field(
        default_factory=dict, description="Shared context across steps"
    )

    def get_step(self, name: str) -> WorkflowStep | None:
        """Get a step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None

    def add_step(self, name: str) -> WorkflowStep:
        """Add a new step to the workflow."""
        step = WorkflowStep(name=name)
        self.steps.append(step)
        return step

    @property
    def duration_ms(self) -> float | None:
        """Calculate total workflow duration in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None


class WorkflowResult(BaseModel):
    """Final result of a workflow execution."""

    workflow_id: str
    document_id: str
    success: bool
    state: WorkflowState
    error: str | None = None
    metrics: dict[str, Any] = Field(
        default_factory=dict, description="Aggregated workflow metrics"
    )

    @classmethod
    def from_state(cls, state: WorkflowState, error: str | None = None) -> "WorkflowResult":
        """Create a result from workflow state."""
        return cls(
            workflow_id=state.workflow_id,
            document_id=state.document_id,
            success=error is None and state.status == StepStatus.COMPLETED,
            state=state,
            error=error,
            metrics={
                "total_duration_ms": state.duration_ms,
                "step_count": len(state.steps),
                "completed_steps": sum(
                    1 for s in state.steps if s.status == StepStatus.COMPLETED
                ),
            },
        )
