# Intelligent Document Processing

Production-grade multi-agent document processing system using Python and AWS Bedrock.

## Features

- **Document Classification**: Automatically classify documents as invoices, receipts, contracts, or forms
- **Field Extraction**: Extract structured data from documents using LLM-powered agents
- **Data Validation**: Validate extracted data with customizable rules
- **Workflow Orchestration**: Chain agents together with conditional logic and error handling

## Installation

```bash
# Install with UV
uv sync

# Install with pip
pip install -e .
```

## Quick Start

```python
from idp.models import Document, DocumentPage
from idp.orchestration import WorkflowEngine

# Create a document
doc = Document(
    id="doc-001",
    pages=[DocumentPage(page_number=1, content="Invoice text here...")]
)

# Process the document
engine = WorkflowEngine()
result = await engine.process(doc)

print(f"Document type: {result.state.context['document_type']}")
print(f"Extracted data: {result.state.context['extracted_data']}")
```

## CLI Usage

```bash
# Process a document
idp process document.pdf

# Classify a document
idp classify document.pdf

# Extract data from a document
idp extract document.pdf --type invoice

# Run evaluation
idp evaluate --dataset ./datasets/golden
```

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

## Configuration

Configuration is done via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `IDP_ENVIRONMENT` | Environment (development/staging/production) | development |
| `IDP_AWS_REGION` | AWS region for Bedrock | us-east-1 |
| `IDP_BEDROCK_MODEL_ID` | Bedrock model ID | anthropic.claude-3-5-sonnet-20241022-v2:0 |
| `IDP_STORAGE_BACKEND` | Storage backend (local/s3/memory) | local |
| `IDP_LOG_LEVEL` | Log level | INFO |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Workflow Engine                       │
├─────────────┬─────────────────┬─────────────────────────┤
│ Classify    │    Extract      │       Validate          │
│ Agent       │    Agent        │       Agent             │
├─────────────┴─────────────────┴─────────────────────────┤
│                    LLM Client                            │
├─────────────────────────────────────────────────────────┤
│              AWS Bedrock / Mock                          │
└─────────────────────────────────────────────────────────┘
```

## License

MIT
