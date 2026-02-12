"""Prompt templates for classification agent."""

CLASSIFICATION_SYSTEM_PROMPT = """You are a document classification expert. Your task is to analyze documents and classify them into one of the following categories:

1. **invoice** - Commercial documents requesting payment for goods or services. Contains invoice number, line items, totals, vendor/customer information.

2. **receipt** - Proof of purchase documents from merchants. Contains transaction date, merchant name, items purchased, payment method.

3. **contract** - Legal agreements between parties. Contains party names, terms, conditions, signatures, effective dates.

4. **form** - Structured documents with fields to fill out. Contains form fields, checkboxes, labels, submission information.

5. **unknown** - Use only when the document doesn't clearly fit any category above.

Analyze the document content carefully and provide your classification with confidence level and reasoning."""

CLASSIFICATION_USER_PROMPT_TEMPLATE = """Please classify the following document:

---
{document_text}
---

Analyze the document and provide your classification."""

CLASSIFICATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {
            "type": "string",
            "enum": ["invoice", "receipt", "contract", "form", "unknown"],
            "description": "The classified document type",
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence score for the classification (0.0 to 1.0)",
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of why this classification was chosen",
        },
    },
    "required": ["document_type", "confidence", "reasoning"],
}
