"""Workflow engine for orchestrating document processing."""

import uuid
from datetime import datetime
from typing import Any

from idp.agents.classification import ClassificationAgent, ClassificationInput
from idp.agents.extraction import ExtractionAgent, ExtractionInput
from idp.agents.validation import ValidationAgent, ValidationInput
from idp.core.config import Settings, get_settings
from idp.core.exceptions import WorkflowError
from idp.core.logging import get_logger
from idp.llm.client import BaseLLMClient
from idp.models.document import Document, DocumentType
from idp.models.workflow import StepStatus, WorkflowResult, WorkflowState, WorkflowStep
from idp.orchestration.workflows import StandardDocumentWorkflow, WorkflowDefinition

logger = get_logger(__name__)


class WorkflowEngine:
    """Engine for executing document processing workflows."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        settings: Settings | None = None,
        workflow: WorkflowDefinition | None = None,
    ) -> None:
        """Initialize the workflow engine.

        Args:
            llm_client: LLM client for agents
            settings: Application settings
            workflow: Workflow definition to use
        """
        self._llm_client = llm_client
        self._settings = settings or get_settings()
        self._workflow = workflow or StandardDocumentWorkflow

        # Initialize agents
        self._classification_agent = ClassificationAgent(llm_client, settings)
        self._extraction_agent = ExtractionAgent(llm_client, settings)
        self._validation_agent = ValidationAgent(settings=settings)

        logger.info(
            "Initialized workflow engine",
            workflow=self._workflow.name,
            steps=[s.name for s in self._workflow.steps],
        )

    def _create_state(self, document: Document) -> WorkflowState:
        """Create initial workflow state."""
        state = WorkflowState(
            workflow_id=str(uuid.uuid4()),
            document_id=document.id,
            status=StepStatus.PENDING,
            context={
                "document": document,
                "document_type": document.document_type.value if document.document_type else None,
            },
        )

        # Add step placeholders
        for step_def in self._workflow.steps:
            state.add_step(step_def.name)

        return state

    async def _run_classification(
        self,
        state: WorkflowState,
        step: WorkflowStep,
    ) -> None:
        """Run the classification step."""
        document: Document = state.context["document"]

        input_data = ClassificationInput(document=document)
        result = await self._classification_agent.process(input_data)

        if not result.success or result.output is None:
            raise WorkflowError(
                "Classification failed",
                workflow_id=state.workflow_id,
                step_name=step.name,
                details={"error": result.error},
            )

        # Update context with classification result
        state.context["document_type"] = result.output.document_type.value
        state.context["classification_confidence"] = result.output.confidence
        state.context["classification_reasoning"] = result.output.reasoning

        # Update document
        document.document_type = result.output.document_type
        document.classification_confidence = result.output.confidence

        step.output_data = {
            "document_type": result.output.document_type.value,
            "confidence": result.output.confidence,
        }
        step.metrics = result.metrics

    async def _run_extraction(
        self,
        state: WorkflowState,
        step: WorkflowStep,
    ) -> None:
        """Run the extraction step."""
        document: Document = state.context["document"]
        doc_type_str = state.context.get("document_type", "unknown")

        try:
            doc_type = DocumentType(doc_type_str)
        except ValueError:
            doc_type = DocumentType.UNKNOWN

        if doc_type == DocumentType.UNKNOWN:
            raise WorkflowError(
                "Cannot extract from unknown document type",
                workflow_id=state.workflow_id,
                step_name=step.name,
            )

        input_data = ExtractionInput(document=document, document_type=doc_type)
        result = await self._extraction_agent.process(input_data)

        if not result.success or result.output is None:
            raise WorkflowError(
                "Extraction failed",
                workflow_id=state.workflow_id,
                step_name=step.name,
                details={"error": result.error},
            )

        # Update context with extraction result
        state.context["extraction"] = result.output.extraction
        state.context["extracted_data"] = result.output.raw_response

        # Update document
        document.extracted_data = result.output.raw_response

        step.output_data = {
            "field_count": result.output.field_count,
            "raw_response": result.output.raw_response,
        }
        step.metrics = result.metrics

    async def _run_validation(
        self,
        state: WorkflowState,
        step: WorkflowStep,
    ) -> None:
        """Run the validation step."""
        document: Document = state.context["document"]
        extraction = state.context.get("extraction")
        doc_type_str = state.context.get("document_type", "unknown")

        if extraction is None:
            raise WorkflowError(
                "No extraction data to validate",
                workflow_id=state.workflow_id,
                step_name=step.name,
            )

        try:
            doc_type = DocumentType(doc_type_str)
        except ValueError:
            doc_type = DocumentType.UNKNOWN

        input_data = ValidationInput(
            document=document,
            document_type=doc_type,
            extraction=extraction,
        )
        result = await self._validation_agent.process(input_data)

        if not result.success or result.output is None:
            raise WorkflowError(
                "Validation failed",
                workflow_id=state.workflow_id,
                step_name=step.name,
                details={"error": result.error},
            )

        # Update context with validation result
        state.context["validation_valid"] = result.output.valid
        state.context["validation_issues"] = [i.to_dict() for i in result.output.issues]

        # Update document
        document.validation_issues = [i.to_dict() for i in result.output.issues]

        step.output_data = result.output.to_dict()
        step.metrics = result.metrics

    async def _run_step(
        self,
        state: WorkflowState,
        step_def: Any,
        step: WorkflowStep,
    ) -> None:
        """Run a single workflow step."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.utcnow()
        state.current_step = step.name

        logger.info(
            "Running workflow step",
            workflow_id=state.workflow_id,
            step=step.name,
        )

        try:
            # Route to appropriate handler
            if step_def.handler == "classification":
                await self._run_classification(state, step)
            elif step_def.handler == "extraction":
                await self._run_extraction(state, step)
            elif step_def.handler == "validation":
                await self._run_validation(state, step)
            else:
                raise WorkflowError(
                    f"Unknown handler: {step_def.handler}",
                    workflow_id=state.workflow_id,
                    step_name=step.name,
                )

            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.utcnow()

            logger.info(
                "Step completed",
                workflow_id=state.workflow_id,
                step=step.name,
                duration_ms=step.duration_ms,
            )

        except Exception as e:
            step.status = StepStatus.FAILED
            step.completed_at = datetime.utcnow()
            step.error = str(e)

            logger.error(
                "Step failed",
                workflow_id=state.workflow_id,
                step=step.name,
                error=str(e),
            )

            # Handle error based on step configuration
            if step_def.on_error == "fail":
                raise
            elif step_def.on_error == "skip":
                step.status = StepStatus.SKIPPED

    async def process(self, document: Document) -> WorkflowResult:
        """Process a document through the workflow.

        Args:
            document: Document to process

        Returns:
            Workflow result with state and any errors
        """
        state = self._create_state(document)
        state.status = StepStatus.RUNNING

        logger.info(
            "Starting workflow",
            workflow_id=state.workflow_id,
            document_id=document.id,
            workflow=self._workflow.name,
        )

        error_message: str | None = None

        try:
            for step_def in self._workflow.steps:
                step = state.get_step(step_def.name)
                if step is None:
                    continue

                # Check if step should run
                if not step_def.should_run(state):
                    step.status = StepStatus.SKIPPED
                    logger.debug(
                        "Skipping step (condition not met)",
                        step=step_def.name,
                    )
                    continue

                # Check dependencies
                for dep_name in step_def.depends_on:
                    dep_step = state.get_step(dep_name)
                    if dep_step is None or dep_step.status not in (
                        StepStatus.COMPLETED,
                        StepStatus.SKIPPED,
                    ):
                        if step_def.required:
                            raise WorkflowError(
                                f"Dependency '{dep_name}' not satisfied",
                                workflow_id=state.workflow_id,
                                step_name=step_def.name,
                            )
                        else:
                            step.status = StepStatus.SKIPPED
                            continue

                await self._run_step(state, step_def, step)

            state.status = StepStatus.COMPLETED

        except Exception as e:
            state.status = StepStatus.FAILED
            error_message = str(e)
            logger.error(
                "Workflow failed",
                workflow_id=state.workflow_id,
                error=error_message,
            )

        state.completed_at = datetime.utcnow()
        state.current_step = None

        result = WorkflowResult.from_state(state, error_message)

        logger.info(
            "Workflow finished",
            workflow_id=state.workflow_id,
            success=result.success,
            duration_ms=state.duration_ms,
        )

        return result

    async def process_batch(
        self,
        documents: list[Document],
    ) -> list[WorkflowResult]:
        """Process multiple documents.

        Args:
            documents: Documents to process

        Returns:
            List of workflow results
        """
        results = []
        for doc in documents:
            result = await self.process(doc)
            results.append(result)
        return results
