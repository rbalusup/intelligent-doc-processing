#!/usr/bin/env python3
"""Run evaluation on test dataset."""

import asyncio
import json
from pathlib import Path

from idp.evaluation import EvaluationFramework, TestCase
from idp.llm.mock.client import MockLLMClient, CLASSIFICATION_RESPONSES, EXTRACTION_RESPONSES
from idp.models.document import Document, DocumentPage, DocumentType
from idp.orchestration import WorkflowEngine


def create_test_cases() -> list[TestCase]:
    """Create test cases for evaluation."""
    return [
        # Invoice test cases
        TestCase(
            id="invoice-basic-1",
            document=Document(
                id="inv-basic-1",
                pages=[DocumentPage(
                    page_number=1,
                    content="""
                    INVOICE
                    Invoice Number: INV-2024-001
                    Date: January 15, 2024
                    Due Date: February 15, 2024

                    From: Acme Corp
                    To: Customer Inc

                    Services: $1,000.00
                    Tax: $80.00
                    Total: $1,080.00
                    """,
                )],
            ),
            expected_type=DocumentType.INVOICE,
            expected_fields={
                "invoice_number": "INV-2024-001",
            },
            tags=["invoice", "basic"],
        ),
        TestCase(
            id="invoice-detailed-1",
            document=Document(
                id="inv-detailed-1",
                pages=[DocumentPage(
                    page_number=1,
                    content="""
                    INVOICE #INV-2024-002

                    Bill To: Client LLC
                    123 Main Street
                    City, State 12345

                    Item 1: Consulting - $500
                    Item 2: Support - $300

                    Subtotal: $800
                    Tax (10%): $80
                    Total Due: $880

                    Payment Terms: Net 30
                    """,
                )],
            ),
            expected_type=DocumentType.INVOICE,
            expected_fields={
                "payment_terms": "Net 30",
            },
            tags=["invoice", "detailed"],
        ),

        # Receipt test cases
        TestCase(
            id="receipt-retail-1",
            document=Document(
                id="rcpt-retail-1",
                pages=[DocumentPage(
                    page_number=1,
                    content="""
                    COFFEE SHOP
                    123 Main Street

                    Date: 01/20/2024
                    Time: 10:30 AM

                    Latte          $5.50
                    Croissant      $3.75

                    Subtotal:      $9.25
                    Tax:           $0.74
                    Total:         $9.99

                    VISA ****1234
                    Thank you!
                    """,
                )],
            ),
            expected_type=DocumentType.RECEIPT,
            expected_fields={
                "merchant_name": "Coffee Shop",
            },
            tags=["receipt", "retail"],
        ),

        # Contract test cases
        TestCase(
            id="contract-service-1",
            document=Document(
                id="contract-service-1",
                pages=[DocumentPage(
                    page_number=1,
                    content="""
                    SERVICE AGREEMENT

                    This Agreement is entered into as of March 1, 2024

                    BETWEEN:
                    Provider Corp ("Provider")
                    AND
                    Client LLC ("Client")

                    TERMS:
                    - Term: 12 months
                    - Monthly fee: $5,000

                    GOVERNING LAW: State of Delaware

                    Signatures:
                    _________________
                    Provider Corp

                    _________________
                    Client LLC
                    """,
                )],
            ),
            expected_type=DocumentType.CONTRACT,
            expected_fields={
                "governing_law": "Delaware",
            },
            tags=["contract", "service"],
        ),

        # Form test cases
        TestCase(
            id="form-application-1",
            document=Document(
                id="form-app-1",
                pages=[DocumentPage(
                    page_number=1,
                    content="""
                    APPLICATION FORM

                    Date: 02/01/2024

                    Personal Information:
                    Name: John Smith
                    Email: john@example.com
                    Phone: (555) 123-4567

                    [X] I agree to terms
                    [ ] Subscribe to newsletter

                    Signature: John Smith
                    """,
                )],
            ),
            expected_type=DocumentType.FORM,
            expected_fields={
                "form_title": "Application Form",
            },
            tags=["form", "application"],
        ),
    ]


async def main() -> None:
    """Run the evaluation."""
    print("=" * 60)
    print("IDP Evaluation Runner")
    print("=" * 60)

    # Create mock client with combined responses
    all_responses = {**CLASSIFICATION_RESPONSES, **EXTRACTION_RESPONSES}
    client = MockLLMClient(responses=all_responses)

    # Create workflow engine
    engine = WorkflowEngine(llm_client=client)

    # Create evaluation framework
    framework = EvaluationFramework(engine)

    # Get test cases
    test_cases = create_test_cases()
    print(f"\nRunning {len(test_cases)} test cases...\n")

    # Run evaluation
    report = await framework.run_evaluation(test_cases)

    # Print results
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total Tests:             {report.total_tests}")
    print(f"Passed:                  {report.passed_tests}")
    print(f"Failed:                  {report.failed_tests}")
    print(f"Pass Rate:               {report.pass_rate:.1%}")
    print(f"Classification Accuracy: {report.classification_accuracy:.1%}")
    print(f"Extraction F1:           {report.extraction_f1:.2f}")
    print(f"Average Latency:         {report.average_latency_ms:.1f} ms")
    print("=" * 60)

    # Print individual results
    print("\nIndividual Test Results:")
    print("-" * 60)
    for result in report.results:
        status = "[PASS]" if result.passed else "[FAIL]"
        print(f"{status} {result.test_case_id}")
        if not result.passed and result.errors:
            for error in result.errors:
                print(f"       Error: {error}")

    # Save report
    output_path = Path("evaluation_report.json")
    output_path.write_text(json.dumps(report.to_dict(), indent=2))
    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
