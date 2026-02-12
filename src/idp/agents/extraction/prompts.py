"""Prompt templates for extraction agent."""

from idp.models.document import DocumentType

EXTRACTION_SYSTEM_PROMPTS = {
    DocumentType.INVOICE: """You are an expert invoice data extractor. Your task is to extract structured data from invoice documents.

Extract the following information:
- Invoice number, date, and due date
- Vendor information (name, address, contact)
- Customer/billing information
- Line items with descriptions, quantities, prices
- Subtotal, tax, and total amounts
- Payment terms and any reference numbers

For dates, use YYYY-MM-DD format. For amounts, use numeric values without currency symbols.
If a field is not found in the document, use null.""",

    DocumentType.RECEIPT: """You are an expert receipt data extractor. Your task is to extract structured data from receipt documents.

Extract the following information:
- Merchant name and address
- Transaction date and time
- Line items with descriptions and prices
- Subtotal, tax, tip, and total amounts
- Payment method and card details

For dates, use YYYY-MM-DD format. For amounts, use numeric values without currency symbols.
If a field is not found in the document, use null.""",

    DocumentType.CONTRACT: """You are an expert contract data extractor. Your task is to extract structured data from contract documents.

Extract the following information:
- Contract title and type
- Effective and expiration dates
- Parties involved
- Governing law and jurisdiction
- Key terms and obligations
- Total value if applicable

For dates, use YYYY-MM-DD format. For amounts, use numeric values.
If a field is not found in the document, use null.""",

    DocumentType.FORM: """You are an expert form data extractor. Your task is to extract structured data from form documents.

Extract the following information:
- Form title and type
- Form date
- Person submitting the form
- All form fields and their values
- Checkbox states (checked or unchecked)
- Signatures

For dates, use YYYY-MM-DD format.
If a field is not found in the document, use null.""",
}

EXTRACTION_USER_PROMPT_TEMPLATE = """Extract structured data from the following {document_type} document:

---
{document_text}
---

Extract all relevant fields and return the data as JSON."""


def get_extraction_prompt(document_type: DocumentType) -> str:
    """Get the system prompt for a document type."""
    return EXTRACTION_SYSTEM_PROMPTS.get(
        document_type,
        EXTRACTION_SYSTEM_PROMPTS[DocumentType.FORM]
    )
