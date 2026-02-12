"""LangGraph workflow definition for document processing."""

from typing import Any, Annotated, TypedDict
import operator

from langgraph.graph import StateGraph, END

from idp.core.config import get_settings
from idp.core.logging import get_logger
from idp.models.document import Document, DocumentType
from idp.services.bedrock import BedrockService

logger = get_logger(__name__)


class GraphState(TypedDict):
    """State for the document processing graph."""
    
    document: Document
    document_type: str | None
    classification_confidence: float | None
    extracted_data: dict[str, Any] | None
    validation_issues: list[dict[str, Any]] | None
    is_valid: bool
    retrieved_context: list[dict[str, Any]] | None
    error: str | None


class DocumentProcessingGraph:
    """Defines the LangGraph workflow."""

    def __init__(self):
        """Initialize the graph."""
        self.settings = get_settings()
        self.bedrock_service = BedrockService()
        self.workflow = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the state graph."""
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("classification", self._classification_node)
        workflow.add_node("retrieval", self._retrieval_node)
        workflow.add_node("extraction", self._extraction_node)
        workflow.add_node("validation", self._validation_node)

        # Define edges
        workflow.set_entry_point("classification")

        # Conditional edge after classification
        workflow.add_conditional_edges(
            "classification",
            self._check_classification,
            {
                "continue": "retrieval",
                "unknown": END,
                "error": END
            }
        )

        workflow.add_edge("retrieval", "extraction")
        workflow.add_edge("extraction", "validation")
        workflow.add_edge("validation", END)

        return workflow.compile()

    async def _classification_node(self, state: GraphState) -> dict:
        """Classification node."""
        logger.info("Running classification node")
        try:
            # TODO: Integrate with actual ClassificationAgent or Bedrock Agent
            # For now, simplistic logic or mock
            doc = state["document"]
            # Placeholder: Use Bedrock to classify if Agent is configured
            if self.settings.bedrock_agent_id:
                 # Call agent...
                 pass
            
            # Fallback to current logic or just pass through for now to structure the graph
            # In a real migration, we'd call the existing ClassificationAgent here
            
            return {
                "document_type": "invoice", # Placeholder
                "classification_confidence": 0.95
            }
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {"error": str(e)}

    def _check_classification(self, state: GraphState) -> str:
        """Determine next step based on classification."""
        if state.get("error"):
            return "error"
        
        doc_type = state.get("document_type")
        if not doc_type or doc_type == "unknown":
             return "unknown"
        
        return "continue"

    async def _retrieval_node(self, state: GraphState) -> dict:
        """Retrieval node using Bedrock Knowledge Base."""
        logger.info("Running retrieval node")
        try:
            doc_type = state.get("document_type")
            query = f"guidelines for {doc_type}"
            
            results = await self.bedrock_service.retrieve(query)
            return {"retrieved_context": results}
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            # Don't fail the whole workflow for retrieval failure
            return {"retrieved_context": []}

    async def _extraction_node(self, state: GraphState) -> dict:
        """Extraction node."""
        logger.info("Running extraction node")
        try:
            # TODO: Integrate with ExtractionAgent
            return {"extracted_data": {"invoice_number": "123"}} # Placeholder
        except Exception as e:
             logger.error(f"Extraction failed: {e}")
             return {"error": str(e)}

    async def _validation_node(self, state: GraphState) -> dict:
        """Validation node."""
        logger.info("Running validation node")
        return {"is_valid": True, "validation_issues": []}

