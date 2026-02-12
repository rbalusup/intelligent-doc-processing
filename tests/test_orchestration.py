"""Tests for workflow orchestration."""

import pytest

from idp.llm.mock.client import MockLLMClient, MockResponse, create_classification_mock
from idp.models.document import Document, DocumentPage, DocumentType
from idp.models.workflow import StepStatus
from idp.orchestration import WorkflowEngine, WorkflowDefinition, StepDefinition


class TestWorkflowEngine:
    """Tests for WorkflowEngine."""

    @pytest.fixture
    def mock_client(self) -> MockLLMClient:
        """Create a mock LLM client configured for all steps."""
        # Combine classification and extraction responses
        from idp.llm.mock.client import CLASSIFICATION_RESPONSES, EXTRACTION_RESPONSES

        all_responses = {**CLASSIFICATION_RESPONSES, **EXTRACTION_RESPONSES}
        return MockLLMClient(responses=all_responses)

    @pytest.fixture
    def engine(self, mock_client: MockLLMClient) -> WorkflowEngine:
        """Create workflow engine with mock client."""
        return WorkflowEngine(llm_client=mock_client)

    @pytest.mark.asyncio
    async def test_process_invoice(
        self,
        engine: WorkflowEngine,
        sample_invoice_text: str,
    ) -> None:
        """Test processing an invoice through the full workflow."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        )

        result = await engine.process(doc)

        assert result.success is True
        assert result.state.status == StepStatus.COMPLETED

        # Check all steps completed
        classify_step = result.state.get_step("classify")
        assert classify_step is not None
        assert classify_step.status == StepStatus.COMPLETED

        extract_step = result.state.get_step("extract")
        assert extract_step is not None
        assert extract_step.status == StepStatus.COMPLETED

        validate_step = result.state.get_step("validate")
        assert validate_step is not None
        assert validate_step.status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_process_receipt(
        self,
        engine: WorkflowEngine,
        sample_receipt_text: str,
    ) -> None:
        """Test processing a receipt through the full workflow."""
        doc = Document(
            id="rcpt-001",
            pages=[DocumentPage(page_number=1, content=sample_receipt_text)],
        )

        result = await engine.process(doc)

        assert result.success is True
        assert result.state.context.get("document_type") == "receipt"

    @pytest.mark.asyncio
    async def test_process_with_preclassified(
        self,
        engine: WorkflowEngine,
        sample_invoice_text: str,
    ) -> None:
        """Test processing a pre-classified document skips classification."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
            document_type=DocumentType.INVOICE,
        )

        result = await engine.process(doc)

        assert result.success is True

        # Classification should be skipped
        classify_step = result.state.get_step("classify")
        assert classify_step is not None
        assert classify_step.status == StepStatus.SKIPPED

        # But extraction should still run
        extract_step = result.state.get_step("extract")
        assert extract_step is not None
        assert extract_step.status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_workflow_context_propagation(
        self,
        engine: WorkflowEngine,
        sample_invoice_text: str,
    ) -> None:
        """Test that context is properly propagated between steps."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        )

        result = await engine.process(doc)

        assert result.success is True

        # Check context contains expected data
        ctx = result.state.context
        assert "document_type" in ctx
        assert "extraction" in ctx
        assert "validation_valid" in ctx

    @pytest.mark.asyncio
    async def test_workflow_updates_document(
        self,
        engine: WorkflowEngine,
        sample_invoice_text: str,
    ) -> None:
        """Test that document is updated during processing."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        )

        await engine.process(doc)

        # Document should be updated
        assert doc.document_type is not None
        assert doc.extracted_data is not None

    @pytest.mark.asyncio
    async def test_workflow_metrics(
        self,
        engine: WorkflowEngine,
        sample_invoice_text: str,
    ) -> None:
        """Test that workflow collects metrics."""
        doc = Document(
            id="inv-001",
            pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
        )

        result = await engine.process(doc)

        assert result.success is True
        assert result.metrics["total_duration_ms"] is not None
        assert result.metrics["step_count"] == 3
        assert result.metrics["completed_steps"] >= 2

    @pytest.mark.asyncio
    async def test_process_batch(
        self,
        engine: WorkflowEngine,
        sample_invoice_text: str,
        sample_receipt_text: str,
    ) -> None:
        """Test batch processing multiple documents."""
        docs = [
            Document(
                id="inv-001",
                pages=[DocumentPage(page_number=1, content=sample_invoice_text)],
            ),
            Document(
                id="rcpt-001",
                pages=[DocumentPage(page_number=1, content=sample_receipt_text)],
            ),
        ]

        results = await engine.process_batch(docs)

        assert len(results) == 2
        assert all(r.success for r in results)


class TestWorkflowDefinition:
    """Tests for workflow definitions."""

    def test_step_definition(self) -> None:
        """Test creating a step definition."""
        step = StepDefinition(
            name="test_step",
            description="A test step",
            handler="test_handler",
            required=True,
        )
        assert step.name == "test_step"
        assert step.required is True

    def test_workflow_get_step(self) -> None:
        """Test getting a step by name."""
        workflow = WorkflowDefinition(
            name="test_workflow",
            description="Test workflow",
            steps=[
                StepDefinition(name="step1", description="Step 1", handler="h1"),
                StepDefinition(name="step2", description="Step 2", handler="h2"),
            ],
        )

        step1 = workflow.get_step("step1")
        assert step1 is not None
        assert step1.name == "step1"

        missing = workflow.get_step("missing")
        assert missing is None

    def test_step_condition(self) -> None:
        """Test step condition function."""
        from idp.models.workflow import WorkflowState

        step = StepDefinition(
            name="conditional",
            description="Conditional step",
            handler="handler",
            condition=lambda s: s.context.get("run_this", False),
        )

        state = WorkflowState(workflow_id="wf-1", document_id="doc-1")

        # Condition not met
        state.context = {"run_this": False}
        assert step.should_run(state) is False

        # Condition met
        state.context = {"run_this": True}
        assert step.should_run(state) is True
