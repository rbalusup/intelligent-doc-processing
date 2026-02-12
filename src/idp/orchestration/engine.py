"""Workflow engine for orchestrating document processing."""

import uuid
from datetime import datetime
from typing import Any

from idp.core.config import Settings, get_settings
from idp.core.logging import get_logger
from idp.llm.client import BaseLLMClient
from idp.models.document import Document
from idp.models.workflow import StepStatus, WorkflowResult, WorkflowState, WorkflowStep
from idp.orchestration.graph import DocumentProcessingGraph
from idp.orchestration.workflows import WorkflowDefinition

logger = get_logger(__name__)


class WorkflowEngine:
    """Engine for executing document processing workflows using LangGraph."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        settings: Settings | None = None,
        workflow: WorkflowDefinition | None = None,
    ) -> None:
        """Initialize the workflow engine.

        Args:
            llm_client: LLM client for agents (kept for interface compatibility)
            settings: Application settings
            workflow: Workflow definition to use (ignored in LangGraph version for now)
        """
        self._settings = settings or get_settings()
        self._graph = DocumentProcessingGraph()
        
        logger.info("Initialized LangGraph workflow engine")

    async def process(self, document: Document) -> WorkflowResult:
        """Process a document through the workflow.

        Args:
            document: Document to process

        Returns:
            Workflow result with state and any errors
        """
        workflow_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(
            "Starting workflow",
            workflow_id=workflow_id,
            document_id=document.id,
        )

        # Initial state for LangGraph
        initial_state = {
            "document": document,
            "document_type": None,
            "classification_confidence": None,
            "extracted_data": None,
            "validation_issues": None,
            "is_valid": False,
            "retrieved_context": None,
            "error": None,
        }

        error_message = None
        final_status = StepStatus.PENDING

        try:
            # Invoke LangGraph
            final_state = await self._graph.workflow.ainvoke(initial_state)
            
            if final_state.get("error"):
                raise Exception(final_state["error"])

            final_status = StepStatus.COMPLETED

        except Exception as e:
            logger.error(
                "Workflow failed",
                workflow_id=workflow_id,
                error=str(e),
            )
            error_message = str(e)
            final_status = StepStatus.FAILED
            # In case of exception, final_state might not be available or partial
            final_state = initial_state 

        # Map back to WorkflowState for compatibility
        # Note: We are approximating step execution details as LangGraph invoke 
        # doesn't give granular step timings by default without streaming/tracing.
        
        workflow_state = WorkflowState(
            workflow_id=workflow_id,
            document_id=document.id,
            status=final_status,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            context={
                "document_type": final_state.get("document_type"),
                "classification_confidence": final_state.get("classification_confidence"),
                "extraction": final_state.get("extracted_data"),
                "validation_issues": final_state.get("validation_issues"),
                "retrieved_context": final_state.get("retrieved_context"),
            }
        )
        
        # Add performed steps to state (inferred)
        if final_state.get("document_type"):
            step = workflow_state.add_step("classification")
            step.status = StepStatus.COMPLETED
            step.output_data = {"document_type": final_state["document_type"]}

        if final_state.get("retrieved_context"):
            step = workflow_state.add_step("retrieval")
            step.status = StepStatus.COMPLETED
            step.output_data = {"count": len(final_state["retrieved_context"])}
            
        if final_state.get("extracted_data"):
            step = workflow_state.add_step("extraction")
            step.status = StepStatus.COMPLETED
            step.output_data = final_state["extracted_data"]

        if final_state.get("is_valid") is not None:
             step = workflow_state.add_step("validation")
             step.status = StepStatus.COMPLETED
             step.output_data = {
                 "valid": final_state["is_valid"], 
                 "issues": final_state.get("validation_issues")
             }

        return WorkflowResult.from_state(workflow_state, error_message)

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
