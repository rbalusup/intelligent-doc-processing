"""Command-line interface for the IDP system."""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from idp import __version__
from idp.core.config import Settings
from idp.core.logging import configure_logging
from idp.models.document import Document, DocumentPage, DocumentType

app = typer.Typer(
    name="idp",
    help="Intelligent Document Processing CLI",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"IDP version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
) -> None:
    """Intelligent Document Processing CLI."""
    settings = Settings(debug=debug, log_level="DEBUG" if debug else "INFO")
    configure_logging(settings)


@app.command()
def process(
    file_path: Path = typer.Argument(..., help="Path to document file"),
    doc_type: str | None = typer.Option(
        None, "--type", "-t", help="Document type (invoice, receipt, contract, form)"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output JSON file"),
    mock: bool = typer.Option(False, "--mock", help="Use mock LLM for testing"),
) -> None:
    """Process a document through the full workflow."""
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(1)

    # Read document content
    content = file_path.read_text()

    # Create document
    document_type = DocumentType(doc_type) if doc_type else None
    doc = Document(
        id=file_path.stem,
        pages=[DocumentPage(page_number=1, content=content)],
        document_type=document_type,
    )

    # Create engine
    if mock:
        from idp.llm.mock.client import (
            CLASSIFICATION_RESPONSES,
            EXTRACTION_RESPONSES,
            MockLLMClient,
        )
        all_responses = {**CLASSIFICATION_RESPONSES, **EXTRACTION_RESPONSES}
        client = MockLLMClient(responses=all_responses)
    else:
        from idp.llm.bedrock import BedrockClient
        client = BedrockClient()

    from idp.orchestration import WorkflowEngine
    engine = WorkflowEngine(llm_client=client)

    # Run workflow
    console.print(f"Processing: [cyan]{file_path}[/cyan]")

    result = asyncio.run(engine.process(doc))

    # Display results
    if result.success:
        console.print(Panel("[green]Processing completed successfully![/green]"))

        # Show classification
        doc_type_result = result.state.context.get("document_type", "unknown")
        confidence = result.state.context.get("classification_confidence", 0)
        console.print(f"Document Type: [cyan]{doc_type_result}[/cyan] (confidence: {confidence:.2%})")

        # Show extraction summary
        extracted = result.state.context.get("extracted_data", {})
        if extracted:
            console.print("\n[bold]Extracted Data:[/bold]")
            console.print(json.dumps(extracted, indent=2, default=str))

        # Show validation results
        issues = result.state.context.get("validation_issues", [])
        if issues:
            console.print(f"\n[yellow]Validation Issues: {len(issues)}[/yellow]")
            for issue in issues:
                severity = issue.get("severity", "info")
                color = {"error": "red", "warning": "yellow", "info": "blue"}.get(severity, "white")
                console.print(f"  [{color}]{issue.get('message')}[/{color}]")
    else:
        console.print(Panel(f"[red]Processing failed: {result.error}[/red]"))
        raise typer.Exit(1)

    # Save output if requested
    if output:
        output_data = {
            "document_id": doc.id,
            "document_type": result.state.context.get("document_type"),
            "extracted_data": result.state.context.get("extracted_data"),
            "validation_issues": result.state.context.get("validation_issues"),
            "success": result.success,
        }
        output.write_text(json.dumps(output_data, indent=2, default=str))
        console.print(f"\nOutput saved to: [cyan]{output}[/cyan]")


@app.command()
def classify(
    file_path: Path = typer.Argument(..., help="Path to document file"),
    mock: bool = typer.Option(False, "--mock", help="Use mock LLM for testing"),
) -> None:
    """Classify a document type."""
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(1)

    content = file_path.read_text()
    doc = Document(
        id=file_path.stem,
        pages=[DocumentPage(page_number=1, content=content)],
    )

    # Create client and agent
    if mock:
        from idp.llm.mock.client import create_classification_mock
        client = create_classification_mock()
    else:
        from idp.llm.bedrock import BedrockClient
        client = BedrockClient()

    from idp.agents.classification import ClassificationAgent, ClassificationInput
    agent = ClassificationAgent(llm_client=client)

    # Run classification
    console.print(f"Classifying: [cyan]{file_path}[/cyan]")

    input_data = ClassificationInput(document=doc)
    result = asyncio.run(agent.process(input_data))

    if result.success and result.output:
        table = Table(title="Classification Result")
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Document Type", result.output.document_type.value)
        table.add_row("Confidence", f"{result.output.confidence:.2%}")
        table.add_row("Reasoning", result.output.reasoning)
        table.add_row("Pages Analyzed", str(result.output.analyzed_pages))

        console.print(table)
    else:
        console.print("[red]Classification failed[/red]")
        raise typer.Exit(1)


@app.command()
def extract(
    file_path: Path = typer.Argument(..., help="Path to document file"),
    doc_type: str = typer.Option(..., "--type", "-t", help="Document type"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output JSON file"),
    mock: bool = typer.Option(False, "--mock", help="Use mock LLM for testing"),
) -> None:
    """Extract data from a document."""
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(1)

    try:
        document_type = DocumentType(doc_type)
    except ValueError:
        console.print(f"[red]Invalid document type: {doc_type}[/red]")
        console.print(f"Valid types: {[t.value for t in DocumentType]}")
        raise typer.Exit(1)

    content = file_path.read_text()
    doc = Document(
        id=file_path.stem,
        pages=[DocumentPage(page_number=1, content=content)],
        document_type=document_type,
    )

    # Create client and agent
    if mock:
        from idp.llm.mock.client import create_extraction_mock
        client = create_extraction_mock()
    else:
        from idp.llm.bedrock import BedrockClient
        client = BedrockClient()

    from idp.agents.extraction import ExtractionAgent, ExtractionInput
    agent = ExtractionAgent(llm_client=client)

    # Run extraction
    console.print(f"Extracting from: [cyan]{file_path}[/cyan] (type: {doc_type})")

    input_data = ExtractionInput(document=doc, document_type=document_type)
    result = asyncio.run(agent.process(input_data))

    if result.success and result.output:
        console.print(Panel("[green]Extraction successful![/green]"))
        console.print(f"Fields extracted: {result.output.field_count}")
        console.print("\n[bold]Extracted Data:[/bold]")
        console.print(json.dumps(result.output.raw_response, indent=2, default=str))

        if output:
            output.write_text(json.dumps(result.output.raw_response, indent=2, default=str))
            console.print(f"\nSaved to: [cyan]{output}[/cyan]")
    else:
        console.print("[red]Extraction failed[/red]")
        raise typer.Exit(1)


@app.command()
def evaluate(
    dataset_path: Path | None = typer.Option(
        None, "--dataset", "-d", help="Path to evaluation dataset"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output report file"),
    mock: bool = typer.Option(True, "--mock/--no-mock", help="Use mock LLM"),
) -> None:
    """Run evaluation on a test dataset."""
    console.print("[bold]Running Evaluation[/bold]")

    # Create mock test cases for demo
    from idp.evaluation import EvaluationFramework, TestCase
    from idp.llm.mock.client import CLASSIFICATION_RESPONSES, EXTRACTION_RESPONSES, MockLLMClient

    # Create test cases
    test_cases = [
        TestCase(
            id="test-invoice-1",
            document=Document(
                id="inv-1",
                pages=[DocumentPage(
                    page_number=1,
                    content="Invoice #INV-001\nDate: 2024-01-15\nTotal: $100.00",
                )],
            ),
            expected_type=DocumentType.INVOICE,
            expected_fields={"invoice_number": "INV-001"},
        ),
        TestCase(
            id="test-receipt-1",
            document=Document(
                id="rcpt-1",
                pages=[DocumentPage(
                    page_number=1,
                    content="Coffee Shop Receipt\nTotal: $9.99\nVISA ****1234",
                )],
            ),
            expected_type=DocumentType.RECEIPT,
            expected_fields={"merchant_name": "Coffee Shop"},
        ),
    ]

    # Create engine with mock client
    all_responses = {**CLASSIFICATION_RESPONSES, **EXTRACTION_RESPONSES}
    client = MockLLMClient(responses=all_responses)

    from idp.orchestration import WorkflowEngine
    engine = WorkflowEngine(llm_client=client)

    # Run evaluation
    framework = EvaluationFramework(engine)
    report = asyncio.run(framework.run_evaluation(test_cases))

    # Display results
    table = Table(title="Evaluation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("Total Tests", str(report.total_tests))
    table.add_row("Passed", f"[green]{report.passed_tests}[/green]")
    table.add_row("Failed", f"[red]{report.failed_tests}[/red]")
    table.add_row("Pass Rate", f"{report.pass_rate:.1%}")
    table.add_row("Classification Accuracy", f"{report.classification_accuracy:.1%}")
    table.add_row("Extraction F1", f"{report.extraction_f1:.2f}")
    table.add_row("Avg Latency", f"{report.average_latency_ms:.1f} ms")

    console.print(table)

    # Save report if requested
    if output:
        output.write_text(json.dumps(report.to_dict(), indent=2))
        console.print(f"\nReport saved to: [cyan]{output}[/cyan]")


if __name__ == "__main__":
    app()
