"""JSON schemas for extraction by document type."""

from idp.models.document import DocumentType

INVOICE_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": ["string", "null"]},
        "invoice_date": {
            "type": ["string", "null"],
            "description": "Date in YYYY-MM-DD format",
        },
        "due_date": {
            "type": ["string", "null"],
            "description": "Date in YYYY-MM-DD format",
        },
        "vendor": {
            "type": ["object", "null"],
            "properties": {
                "name": {"type": ["string", "null"]},
                "address": {
                    "type": ["object", "null"],
                    "properties": {
                        "street": {"type": ["string", "null"]},
                        "city": {"type": ["string", "null"]},
                        "state": {"type": ["string", "null"]},
                        "postal_code": {"type": ["string", "null"]},
                        "country": {"type": ["string", "null"]},
                    },
                },
                "email": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
                "tax_id": {"type": ["string", "null"]},
            },
        },
        "customer": {
            "type": ["object", "null"],
            "properties": {
                "name": {"type": ["string", "null"]},
                "address": {
                    "type": ["object", "null"],
                    "properties": {
                        "street": {"type": ["string", "null"]},
                        "city": {"type": ["string", "null"]},
                        "state": {"type": ["string", "null"]},
                        "postal_code": {"type": ["string", "null"]},
                        "country": {"type": ["string", "null"]},
                    },
                },
            },
        },
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": ["number", "null"]},
                    "unit_price": {"type": ["number", "null"]},
                    "total": {"type": ["number", "null"]},
                },
                "required": ["description"],
            },
        },
        "subtotal": {"type": ["number", "null"]},
        "tax_amount": {"type": ["number", "null"]},
        "tax_rate": {"type": ["number", "null"]},
        "total_amount": {"type": ["number", "null"]},
        "currency": {"type": ["string", "null"]},
        "payment_terms": {"type": ["string", "null"]},
        "purchase_order": {"type": ["string", "null"]},
    },
}

RECEIPT_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "merchant_name": {"type": ["string", "null"]},
        "merchant_address": {
            "type": ["object", "null"],
            "properties": {
                "street": {"type": ["string", "null"]},
                "city": {"type": ["string", "null"]},
                "state": {"type": ["string", "null"]},
                "postal_code": {"type": ["string", "null"]},
            },
        },
        "transaction_date": {
            "type": ["string", "null"],
            "description": "Date in YYYY-MM-DD format",
        },
        "transaction_time": {"type": ["string", "null"]},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": ["number", "null"]},
                    "unit_price": {"type": ["number", "null"]},
                    "total": {"type": ["number", "null"]},
                },
                "required": ["description"],
            },
        },
        "subtotal": {"type": ["number", "null"]},
        "tax_amount": {"type": ["number", "null"]},
        "tip_amount": {"type": ["number", "null"]},
        "total_amount": {"type": ["number", "null"]},
        "payment_method": {"type": ["string", "null"]},
        "card_last_four": {"type": ["string", "null"]},
        "currency": {"type": ["string", "null"]},
    },
}

CONTRACT_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "contract_title": {"type": ["string", "null"]},
        "contract_type": {"type": ["string", "null"]},
        "effective_date": {
            "type": ["string", "null"],
            "description": "Date in YYYY-MM-DD format",
        },
        "expiration_date": {
            "type": ["string", "null"],
            "description": "Date in YYYY-MM-DD format",
        },
        "parties": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "address": {
                        "type": ["object", "null"],
                        "properties": {
                            "street": {"type": ["string", "null"]},
                            "city": {"type": ["string", "null"]},
                            "state": {"type": ["string", "null"]},
                        },
                    },
                },
            },
        },
        "governing_law": {"type": ["string", "null"]},
        "jurisdiction": {"type": ["string", "null"]},
        "key_terms": {
            "type": "array",
            "items": {"type": "string"},
        },
        "obligations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "termination_clause": {"type": ["string", "null"]},
        "renewal_terms": {"type": ["string", "null"]},
        "total_value": {"type": ["number", "null"]},
        "currency": {"type": ["string", "null"]},
    },
}

FORM_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "form_title": {"type": ["string", "null"]},
        "form_type": {"type": ["string", "null"]},
        "form_date": {
            "type": ["string", "null"],
            "description": "Date in YYYY-MM-DD format",
        },
        "submitted_by": {
            "type": ["object", "null"],
            "properties": {
                "name": {"type": ["string", "null"]},
                "email": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
                "address": {
                    "type": ["object", "null"],
                    "properties": {
                        "street": {"type": ["string", "null"]},
                        "city": {"type": ["string", "null"]},
                        "state": {"type": ["string", "null"]},
                        "postal_code": {"type": ["string", "null"]},
                    },
                },
            },
        },
        "fields": {
            "type": "object",
            "description": "Key-value pairs of form field labels and their values",
            "additionalProperties": {"type": ["string", "null"]},
        },
        "checkboxes": {
            "type": "object",
            "description": "Checkbox fields and their checked state",
            "additionalProperties": {"type": "boolean"},
        },
        "signatures": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


def get_schema_for_document_type(doc_type: DocumentType) -> dict:
    """Get the extraction schema for a document type."""
    schemas = {
        DocumentType.INVOICE: INVOICE_EXTRACTION_SCHEMA,
        DocumentType.RECEIPT: RECEIPT_EXTRACTION_SCHEMA,
        DocumentType.CONTRACT: CONTRACT_EXTRACTION_SCHEMA,
        DocumentType.FORM: FORM_EXTRACTION_SCHEMA,
    }
    return schemas.get(doc_type, FORM_EXTRACTION_SCHEMA)
