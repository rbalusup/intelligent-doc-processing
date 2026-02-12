"""Verification script for LangGraph implementation."""

import asyncio
import os
from unittest.mock import MagicMock, patch

# Mock boto3 before importing idp services
with patch("boto3.Session") as mock_session_cls:
    mock_session = MagicMock()
    mock_client = MagicMock()
    
    mock_session.client.return_value = mock_client
    mock_session_cls.return_value = mock_session
    
    # Mock specific Bedrock responses
    mock_client.retrieve.return_value = {
        "retrievalResults": [{"content": {"text": "Guideline 1"}}]
    }
    
    # Mock agent invocation
    mock_client.invoke_agent.return_value = {
        "completion": [
            {"chunk": {"bytes": b'{"document_type": "invoice", "confidence": 0.99}'}}
        ]
    }

    # Now import the engine
    from idp.models.document import Document
    from idp.orchestration.engine import WorkflowEngine
    from idp.llm.client import BaseLLMClient

    class MockLLMClient(BaseLLMClient):
        async def generate(self, *args, **kwargs):
            return MagicMock()
        async def generate_json(self, *args, **kwargs):
            return MagicMock()
        @property
        def model_id(self): return "mock"

    async def verify():
        print("Starting verification...")
        
        # Create engine
        engine = WorkflowEngine(llm_client=MockLLMClient())
        
        # Create dummy document
        doc = Document(
            id="test-doc-1",
            content=b"Invoice #123",
            mime_type="application/pdf",
            filename="invoice.pdf"
        )
        
        # Process
        print("Processing document...")
        result = await engine.process(doc)
        
        print(f"Workflow ID: {result.workflow_id}")
        print(f"Success: {result.success}")
        print(f"Status: {result.state.status}")
        print(f"Document Type: {result.state.context.get('document_type')}")
        print(f"Steps: {[s.name for s in result.state.steps]}")
        
        if result.success and result.state.context.get('document_type') == 'invoice':
            print("VERIFICATION PASSED")
        else:
            print("VERIFICATION FAILED")

if __name__ == "__main__":
    asyncio.run(verify())
