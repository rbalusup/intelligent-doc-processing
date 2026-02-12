"""Extraction data models for different document types."""

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class Address(BaseModel):
    """Structured address."""

    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    @property
    def is_complete(self) -> bool:
        """Check if address has minimum required fields."""
        return bool(self.city and (self.state or self.country))


class Party(BaseModel):
    """A party involved in a document (buyer, seller, etc.)."""

    name: str | None = None
    address: Address | None = None
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None


class LineItem(BaseModel):
    """Line item in an invoice or receipt."""

    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total: Decimal | None = None
    item_code: str | None = None

    def calculate_total(self) -> Decimal | None:
        """Calculate total from quantity and unit price."""
        if self.quantity is not None and self.unit_price is not None:
            return self.quantity * self.unit_price
        return self.total


class BaseExtraction(BaseModel):
    """Base class for all extraction results."""

    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Overall extraction confidence"
    )
    raw_fields: dict[str, Any] = Field(
        default_factory=dict, description="Raw extracted fields before normalization"
    )


class InvoiceExtraction(BaseExtraction):
    """Extracted data from an invoice."""

    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    vendor: Party | None = None
    customer: Party | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    tax_rate: Decimal | None = None
    total_amount: Decimal | None = None
    currency: str | None = None
    payment_terms: str | None = None
    purchase_order: str | None = None

    def calculate_subtotal(self) -> Decimal:
        """Calculate subtotal from line items."""
        return sum(
            (item.calculate_total() or Decimal(0)) for item in self.line_items
        )


class ReceiptExtraction(BaseExtraction):
    """Extracted data from a receipt."""

    merchant_name: str | None = None
    merchant_address: Address | None = None
    transaction_date: date | None = None
    transaction_time: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    tip_amount: Decimal | None = None
    total_amount: Decimal | None = None
    payment_method: str | None = None
    card_last_four: str | None = None
    currency: str | None = None


class ContractExtraction(BaseExtraction):
    """Extracted data from a contract."""

    contract_title: str | None = None
    contract_type: str | None = None
    effective_date: date | None = None
    expiration_date: date | None = None
    parties: list[Party] = Field(default_factory=list)
    governing_law: str | None = None
    jurisdiction: str | None = None
    key_terms: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    termination_clause: str | None = None
    renewal_terms: str | None = None
    total_value: Decimal | None = None
    currency: str | None = None


class FormExtraction(BaseExtraction):
    """Extracted data from a general form."""

    form_title: str | None = None
    form_type: str | None = None
    form_date: date | None = None
    submitted_by: Party | None = None
    fields: dict[str, str | None] = Field(
        default_factory=dict, description="Key-value pairs of form fields"
    )
    checkboxes: dict[str, bool] = Field(
        default_factory=dict, description="Checkbox fields and their states"
    )
    signatures: list[str] = Field(
        default_factory=list, description="Names of signatories"
    )
