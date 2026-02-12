"""Extraction agent implementation."""

import json
from datetime import date
from decimal import Decimal
from typing import Any

from idp.agents.base import BaseAgent
from idp.agents.extraction.models import ExtractionInput, ExtractionOutput
from idp.agents.extraction.prompts import EXTRACTION_USER_PROMPT_TEMPLATE, get_extraction_prompt
from idp.agents.extraction.schemas import get_schema_for_document_type
from idp.core.exceptions import LLMError
from idp.llm.client import LLMMessage, MessageRole
from idp.models.document import DocumentType
from idp.models.extraction import (
    Address,
    ContractExtraction,
    FormExtraction,
    InvoiceExtraction,
    LineItem,
    Party,
    ReceiptExtraction,
)


class ExtractionAgent(BaseAgent[ExtractionInput, ExtractionOutput]):
    """Agent for extracting structured data from documents."""

    @property
    def name(self) -> str:
        """Get the agent name."""
        return "ExtractionAgent"

    def _parse_date(self, value: str | None) -> date | None:
        """Parse a date string to a date object."""
        if not value:
            return None
        try:
            # Try YYYY-MM-DD format
            return date.fromisoformat(value)
        except ValueError:
            self._logger.warning("Failed to parse date", value=value)
            return None

    def _parse_decimal(self, value: Any) -> Decimal | None:
        """Parse a value to Decimal."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            self._logger.warning("Failed to parse decimal", value=value)
            return None

    def _parse_address(self, data: dict[str, Any] | None) -> Address | None:
        """Parse address data."""
        if not data:
            return None
        return Address(
            street=data.get("street"),
            city=data.get("city"),
            state=data.get("state"),
            postal_code=data.get("postal_code"),
            country=data.get("country"),
        )

    def _parse_party(self, data: dict[str, Any] | None) -> Party | None:
        """Parse party data."""
        if not data:
            return None
        return Party(
            name=data.get("name"),
            address=self._parse_address(data.get("address")),
            email=data.get("email"),
            phone=data.get("phone"),
            tax_id=data.get("tax_id"),
        )

    def _parse_line_items(self, items: list[dict[str, Any]] | None) -> list[LineItem]:
        """Parse line items."""
        if not items:
            return []
        result = []
        for item in items:
            result.append(LineItem(
                description=item.get("description", ""),
                quantity=self._parse_decimal(item.get("quantity")),
                unit_price=self._parse_decimal(item.get("unit_price")),
                total=self._parse_decimal(item.get("total")),
                item_code=item.get("item_code"),
            ))
        return result

    def _build_invoice_extraction(self, data: dict[str, Any]) -> InvoiceExtraction:
        """Build invoice extraction from raw data."""
        return InvoiceExtraction(
            invoice_number=data.get("invoice_number"),
            invoice_date=self._parse_date(data.get("invoice_date")),
            due_date=self._parse_date(data.get("due_date")),
            vendor=self._parse_party(data.get("vendor")),
            customer=self._parse_party(data.get("customer")),
            line_items=self._parse_line_items(data.get("line_items")),
            subtotal=self._parse_decimal(data.get("subtotal")),
            tax_amount=self._parse_decimal(data.get("tax_amount")),
            tax_rate=self._parse_decimal(data.get("tax_rate")),
            total_amount=self._parse_decimal(data.get("total_amount")),
            currency=data.get("currency"),
            payment_terms=data.get("payment_terms"),
            purchase_order=data.get("purchase_order"),
            raw_fields=data,
        )

    def _build_receipt_extraction(self, data: dict[str, Any]) -> ReceiptExtraction:
        """Build receipt extraction from raw data."""
        return ReceiptExtraction(
            merchant_name=data.get("merchant_name"),
            merchant_address=self._parse_address(data.get("merchant_address")),
            transaction_date=self._parse_date(data.get("transaction_date")),
            transaction_time=data.get("transaction_time"),
            line_items=self._parse_line_items(data.get("line_items")),
            subtotal=self._parse_decimal(data.get("subtotal")),
            tax_amount=self._parse_decimal(data.get("tax_amount")),
            tip_amount=self._parse_decimal(data.get("tip_amount")),
            total_amount=self._parse_decimal(data.get("total_amount")),
            payment_method=data.get("payment_method"),
            card_last_four=data.get("card_last_four"),
            currency=data.get("currency"),
            raw_fields=data,
        )

    def _build_contract_extraction(self, data: dict[str, Any]) -> ContractExtraction:
        """Build contract extraction from raw data."""
        parties = []
        for party_data in data.get("parties", []):
            party = self._parse_party(party_data)
            if party:
                parties.append(party)

        return ContractExtraction(
            contract_title=data.get("contract_title"),
            contract_type=data.get("contract_type"),
            effective_date=self._parse_date(data.get("effective_date")),
            expiration_date=self._parse_date(data.get("expiration_date")),
            parties=parties,
            governing_law=data.get("governing_law"),
            jurisdiction=data.get("jurisdiction"),
            key_terms=data.get("key_terms", []),
            obligations=data.get("obligations", []),
            termination_clause=data.get("termination_clause"),
            renewal_terms=data.get("renewal_terms"),
            total_value=self._parse_decimal(data.get("total_value")),
            currency=data.get("currency"),
            raw_fields=data,
        )

    def _build_form_extraction(self, data: dict[str, Any]) -> FormExtraction:
        """Build form extraction from raw data."""
        return FormExtraction(
            form_title=data.get("form_title"),
            form_type=data.get("form_type"),
            form_date=self._parse_date(data.get("form_date")),
            submitted_by=self._parse_party(data.get("submitted_by")),
            fields=data.get("fields", {}),
            checkboxes=data.get("checkboxes", {}),
            signatures=data.get("signatures", []),
            raw_fields=data,
        )

    async def _execute(self, input_data: ExtractionInput) -> ExtractionOutput:
        """Execute the extraction."""
        document = input_data.document
        doc_type = input_data.document_type

        self._logger.debug(
            "Extracting from document",
            document_id=document.id,
            document_type=doc_type.value,
        )

        # Get schema
        schema = input_data.custom_schema or get_schema_for_document_type(doc_type)

        # Build messages
        document_text = document.full_text
        messages = [
            LLMMessage(
                role=MessageRole.USER,
                content=EXTRACTION_USER_PROMPT_TEMPLATE.format(
                    document_type=doc_type.value,
                    document_text=document_text,
                ),
            ),
        ]

        # Get extraction from LLM
        response = await self._llm_client.generate_json(
            messages=messages,
            schema=schema,
            system=get_extraction_prompt(doc_type),
            temperature=0.0,
        )

        # Parse response
        try:
            raw_data = json.loads(response.content)
        except json.JSONDecodeError as e:
            raise LLMError(
                "Failed to parse extraction response",
                details={"content": response.content, "error": str(e)},
            ) from e

        # Build typed extraction based on document type
        if doc_type == DocumentType.INVOICE:
            extraction = self._build_invoice_extraction(raw_data)
            return ExtractionOutput.from_invoice(extraction, raw_data)
        elif doc_type == DocumentType.RECEIPT:
            extraction = self._build_receipt_extraction(raw_data)
            return ExtractionOutput.from_receipt(extraction, raw_data)
        elif doc_type == DocumentType.CONTRACT:
            extraction = self._build_contract_extraction(raw_data)
            return ExtractionOutput.from_contract(extraction, raw_data)
        else:
            extraction = self._build_form_extraction(raw_data)
            return ExtractionOutput.from_form(extraction, raw_data)
