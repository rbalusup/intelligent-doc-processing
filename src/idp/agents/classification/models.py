"""Classification agent data models."""

from pydantic import BaseModel, Field

from idp.models.document import Document, DocumentType


class ClassificationInput(BaseModel):
    """Input for the classification agent."""

    document: Document
    max_pages: int = Field(
        default=3,
        description="Maximum number of pages to analyze for classification",
    )


class ClassificationOutput(BaseModel):
    """Output from the classification agent."""

    document_type: DocumentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Explanation for the classification")
    analyzed_pages: int = Field(..., description="Number of pages analyzed")

    @property
    def is_confident(self) -> bool:
        """Check if classification meets confidence threshold."""
        return self.confidence >= 0.8
