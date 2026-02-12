"""Document data models."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    """Supported document types."""

    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    FORM = "form"
    UNKNOWN = "unknown"


class DocumentStatus(StrEnum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentPage(BaseModel):
    """Represents a single page of a document."""

    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    content: str = Field(..., description="Text content of the page")
    width: int | None = Field(default=None, description="Page width in pixels")
    height: int | None = Field(default=None, description="Page height in pixels")
    image_base64: str | None = Field(default=None, description="Base64-encoded page image")

    @property
    def has_image(self) -> bool:
        """Check if page has an image."""
        return self.image_base64 is not None


class DocumentMetadata(BaseModel):
    """Metadata associated with a document."""

    source: str | None = Field(default=None, description="Document source (file path, S3 URI)")
    file_name: str | None = Field(default=None, description="Original file name")
    file_size: int | None = Field(default=None, description="File size in bytes")
    mime_type: str | None = Field(default=None, description="MIME type")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime | None = Field(default=None)
    custom: dict[str, Any] = Field(default_factory=dict, description="Custom metadata fields")


class Document(BaseModel):
    """Represents a document to be processed."""

    id: str = Field(..., description="Unique document identifier")
    pages: list[DocumentPage] = Field(default_factory=list, description="Document pages")
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    status: DocumentStatus = Field(default=DocumentStatus.PENDING)
    document_type: DocumentType | None = Field(
        default=None, description="Classified document type"
    )
    classification_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Classification confidence score"
    )
    extracted_data: dict[str, Any] | None = Field(
        default=None, description="Extracted structured data"
    )
    validation_issues: list[dict[str, Any]] = Field(
        default_factory=list, description="Validation issues found"
    )
    error: str | None = Field(default=None, description="Error message if processing failed")

    @property
    def full_text(self) -> str:
        """Get concatenated text from all pages."""
        return "\n\n".join(page.content for page in self.pages)

    @property
    def page_count(self) -> int:
        """Get the number of pages."""
        return len(self.pages)

    def get_page(self, page_number: int) -> DocumentPage | None:
        """Get a specific page by number (1-indexed)."""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None
