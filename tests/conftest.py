"""Pytest configuration and fixtures."""

import pytest

from idp.core.config import Settings
from idp.models.document import Document, DocumentPage, DocumentType


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        environment="development",
        debug=True,
        log_level="DEBUG",
        storage_backend="memory",
    )


@pytest.fixture
def sample_invoice_text() -> str:
    """Sample invoice text for testing."""
    return """
    INVOICE

    Invoice Number: INV-2024-001
    Date: January 15, 2024
    Due Date: February 15, 2024

    From:
    Acme Corporation
    123 Business St
    New York, NY 10001

    Bill To:
    Customer Inc
    456 Client Ave
    Los Angeles, CA 90001

    Items:
    1. Consulting Services - 10 hours @ $150/hr = $1,500.00
    2. Software License - 1 year @ $500/yr = $500.00

    Subtotal: $2,000.00
    Tax (8%): $160.00
    Total: $2,160.00

    Payment Terms: Net 30
    """


@pytest.fixture
def sample_receipt_text() -> str:
    """Sample receipt text for testing."""
    return """
    COFFEE SHOP
    123 Main Street
    San Francisco, CA 94102

    Date: 01/20/2024
    Time: 10:30 AM

    Latte           $5.50
    Croissant       $3.75

    Subtotal:       $9.25
    Tax:            $0.74
    Total:          $9.99

    VISA ****1234
    Thank you!
    """


@pytest.fixture
def sample_contract_text() -> str:
    """Sample contract text for testing."""
    return """
    SERVICE AGREEMENT

    This Agreement is entered into as of March 1, 2024

    BETWEEN:
    Provider Corp ("Provider")
    AND
    Client LLC ("Client")

    1. SERVICES
    Provider agrees to provide consulting services as described in Exhibit A.

    2. TERM
    This Agreement shall commence on March 1, 2024 and continue until
    February 28, 2025, unless terminated earlier.

    3. COMPENSATION
    Client shall pay Provider $10,000 per month for services rendered.

    4. GOVERNING LAW
    This Agreement shall be governed by the laws of the State of Delaware.

    IN WITNESS WHEREOF, the parties have executed this Agreement.

    _______________________
    Provider Corp

    _______________________
    Client LLC
    """


@pytest.fixture
def sample_form_text() -> str:
    """Sample form text for testing."""
    return """
    APPLICATION FORM

    Date: 02/01/2024

    Personal Information:
    Name: John Smith
    Email: john.smith@email.com
    Phone: (555) 123-4567

    Address:
    Street: 789 Oak Lane
    City: Chicago
    State: IL
    ZIP: 60601

    [X] I agree to the terms and conditions
    [ ] Subscribe to newsletter

    Signature: John Smith
    Date: 02/01/2024
    """


@pytest.fixture
def sample_document(sample_invoice_text: str) -> Document:
    """Create a sample document for testing."""
    return Document(
        id="doc-001",
        pages=[
            DocumentPage(
                page_number=1,
                content=sample_invoice_text,
            )
        ],
    )


@pytest.fixture
def sample_invoice_document(sample_invoice_text: str) -> Document:
    """Create a sample invoice document."""
    return Document(
        id="inv-001",
        pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        document_type=DocumentType.INVOICE,
    )


@pytest.fixture
def sample_receipt_document(sample_receipt_text: str) -> Document:
    """Create a sample receipt document."""
    return Document(
        id="rcpt-001",
        pages=[DocumentPage(page_number=1, content=sample_receipt_text)],
        document_type=DocumentType.RECEIPT,
    )
