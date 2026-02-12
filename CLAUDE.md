# CLAUDE.md - Intelligent Document Processing

## Project Overview

Production-grade multi-agent document processing system using Python 3.12+ and AWS Bedrock. Classifies documents (invoices, receipts, contracts, forms), extracts structured data via LLM-powered agents, validates results with rule-based checks, and orchestrates the pipeline using LangGraph.

## Tech Stack

- **Language**: Python 3.12+ (async-first)
- **Package Manager**: uv (lockfile: `uv.lock`)
- **Build**: hatchling
- **LLM**: AWS Bedrock (Claude) via boto3, langchain-aws, langchain-core
- **Orchestration**: LangGraph
- **Data Models**: Pydantic 2.0+ / pydantic-settings
- **CLI**: Typer + Rich
- **Logging**: structlog (structured)
- **Retries**: tenacity (exponential backoff)
- **Testing**: pytest, pytest-asyncio, moto (AWS mocking)
- **Linting**: ruff
- **Type Checking**: mypy (strict mode)

## Common Commands

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_agents.py

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Format
uv run ruff format src/

# Run evaluation
uv run python scripts/run_evaluation.py

# CLI usage
uv run idp process document.pdf
uv run idp classify document.pdf
uv run idp extract document.pdf --type invoice
```

## Project Structure

```
src/idp/                    # Main package
├── agents/                 # Multi-agent implementations
│   ├── base.py            # BaseAgent[InputT, OutputT] abstract class
│   ├── classification/    # Document type classification (LLM-based)
│   ├── extraction/        # Structured data extraction (LLM-based)
│   └── validation/        # Rule-based validation
├── core/                   # Infrastructure
│   ├── config.py          # Settings via pydantic-settings (IDP_ env prefix)
│   ├── exceptions.py      # Custom exception hierarchy (IDPError base)
│   ├── logging.py         # Structured logging setup
│   └── retry.py           # Retry with tenacity
├── llm/                    # LLM client abstraction
│   ├── client.py          # BaseLLMClient abstract class
│   ├── bedrock/client.py  # AWS Bedrock async implementation
│   └── mock/client.py     # MockLLMClient for testing
├── models/                 # Pydantic data models
│   ├── document.py        # Document, DocumentPage, DocumentType, DocumentStatus
│   ├── extraction.py      # InvoiceExtraction, ReceiptExtraction, etc.
│   └── workflow.py        # WorkflowState, WorkflowStep, WorkflowResult
├── orchestration/          # Workflow orchestration
│   ├── engine.py          # WorkflowEngine (LangGraph wrapper)
│   ├── graph.py           # DocumentProcessingGraph (LangGraph state graph)
│   └── workflows.py       # WorkflowDefinition & StepDefinition
├── storage/                # Storage backends (local, memory, S3-ready)
├── services/bedrock.py     # BedrockService for retrieval
├── evaluation/             # Evaluation framework & metrics
└── cli.py                  # Typer CLI (entry point: `idp`)
tests/                      # Test suite (pytest-asyncio, auto mode)
scripts/                    # Evaluation runner
datasets/                   # Test datasets
```

## Architecture

The system follows a pipeline: **Classification -> Retrieval -> Extraction -> Validation**

- **LangGraph** orchestrates the workflow as a state graph with conditional edges (e.g., skip extraction for unknown document types)
- **BaseAgent** is a generic abstract class (`Generic[InputT, OutputT]`) with built-in retry, error handling, and metrics
- **LLM calls** use JSON schema enforcement for structured output
- All I/O operations are **async**

## Key Conventions

- **Configuration**: Environment variables with `IDP_` prefix (see `core/config.py`)
- **Error handling**: Custom exception hierarchy rooted at `IDPError`; `LLMError` has a `retryable` flag
- **Type safety**: Strict mypy mode enabled; all functions must have type annotations
- **Ruff config**: Line length 100, target Python 3.12, isort with `idp` as first-party
- **Tests**: `asyncio_mode = "auto"` — async test functions auto-detected, no decorator needed
- **Prompts**: Separated into `prompts.py` files within each agent module
- **Agents**: Each agent has its own `models.py` for input/output types and `agent.py` for logic
- **Mock LLM**: Use `MockLLMClient` with regex pattern matching for deterministic tests

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IDP_ENVIRONMENT` | development | Environment mode |
| `IDP_AWS_REGION` | us-east-1 | AWS region for Bedrock |
| `IDP_BEDROCK_MODEL_ID` | anthropic.claude-3-5-sonnet-20241022-v2:0 | Bedrock model |
| `IDP_STORAGE_BACKEND` | local | Storage: local/s3/memory |
| `IDP_LOG_LEVEL` | INFO | Log level |
| `IDP_RETRY_MAX_ATTEMPTS` | 3 | Max retry attempts |

## Known Issues

- Evaluation framework shows 0% pass rate on extraction (classification works) — mock responses may not match extraction schemas
- LangGraph graph nodes have placeholder TODOs for full agent integration
- `verify_implementation.py` uses outdated Document API (content/mime_type fields vs current pages-based model)
- `.github/workflows/aws.yml` is a template with placeholder env vars for ECS deployment
