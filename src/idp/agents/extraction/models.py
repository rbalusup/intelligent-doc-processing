"""Extraction agent data models."""

from typing import Any

from pydantic import BaseModel, Field

from idp.models.document import Document, DocumentType
from idp.models.extraction import (
    BaseExtraction,
    ContractExtraction,
    FormExtraction,
    InvoiceExtraction,
    ReceiptExtraction,
)


class ExtractionInput(BaseModel):
    """Input for the extraction agent."""

    document: Document
    document_type: DocumentType
    custom_schema: dict[str, Any] | None = Field(
        default=None,
        description="Optional custom schema for extraction (overrides default)",
    )


class ExtractionOutput(BaseModel):
    """Output from the extraction agent."""

    document_type: DocumentType
    extraction: BaseExtraction
    raw_response: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw extraction response before normalization",
    )
    field_count: int = Field(
        default=0,
        description="Number of fields successfully extracted",
    )

    @classmethod
    def from_invoice(cls, extraction: InvoiceExtraction, raw: dict[str, Any]) -> "ExtractionOutput":
        """Create output from invoice extraction."""
        field_count = sum(
            1 for v in [
                extraction.invoice_number,
                extraction.invoice_date,
                extraction.due_date,
                extraction.vendor,
                extraction.customer,
                extraction.total_amount,
            ]
            if v is not None
        ) + len(extraction.line_items)

        return cls(
            document_type=DocumentType.INVOICE,
            extraction=extraction,
            raw_response=raw,
            field_count=field_count,
        )

    @classmethod
    def from_receipt(cls, extraction: ReceiptExtraction, raw: dict[str, Any]) -> "ExtractionOutput":
        """Create output from receipt extraction."""
        field_count = sum(
            1 for v in [
                extraction.merchant_name,
                extraction.transaction_date,
                extraction.total_amount,
                extraction.payment_method,
            ]
            if v is not None
        ) + len(extraction.line_items)

        return cls(
            document_type=DocumentType.RECEIPT,
            extraction=extraction,
            raw_response=raw,
            field_count=field_count,
        )

    @classmethod
    def from_contract(cls, extraction: ContractExtraction, raw: dict[str, Any]) -> "ExtractionOutput":
        """Create output from contract extraction."""
        field_count = sum(
            1 for v in [
                extraction.contract_title,
                extraction.effective_date,
                extraction.expiration_date,
                extraction.governing_law,
            ]
            if v is not None
        ) + len(extraction.parties)

        return cls(
            document_type=DocumentType.CONTRACT,
            extraction=extraction,
            raw_response=raw,
            field_count=field_count,
        )

    @classmethod
    def from_form(cls, extraction: FormExtraction, raw: dict[str, Any]) -> "ExtractionOutput":
        """Create output from form extraction."""
        field_count = len(extraction.fields) + len(extraction.checkboxes)
        if extraction.form_title:
            field_count += 1

        return cls(
            document_type=DocumentType.FORM,
            extraction=extraction,
            raw_response=raw,
            field_count=field_count,
        )
