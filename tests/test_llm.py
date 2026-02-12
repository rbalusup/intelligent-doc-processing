"""Tests for LLM clients."""

import json
import pytest

from idp.llm.client import LLMMessage, LLMResponse, MessageRole
from idp.llm.mock.client import MockLLMClient, MockResponse, create_classification_mock


class TestLLMMessage:
    """Tests for LLMMessage."""

    def test_message_creation(self) -> None:
        """Test creating a message."""
        msg = LLMMessage(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"

    def test_message_to_dict(self) -> None:
        """Test converting message to dict."""
        msg = LLMMessage(role=MessageRole.ASSISTANT, content="Hi there")
        d = msg.to_dict()
        assert d["role"] == "assistant"
        assert d["content"] == "Hi there"


class TestLLMResponse:
    """Tests for LLMResponse."""

    def test_response_creation(self) -> None:
        """Test creating a response."""
        resp = LLMResponse(
            content="Response text",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            latency_ms=150.5,
        )
        assert resp.content == "Response text"
        assert resp.total_tokens == 150
        assert resp.latency_ms == 150.5

    def test_response_to_dict(self) -> None:
        """Test converting response to dict."""
        resp = LLMResponse(
            content="Test",
            model="model-1",
            input_tokens=10,
            output_tokens=5,
        )
        d = resp.to_dict()
        assert d["content"] == "Test"
        assert d["total_tokens"] == 15


class TestMockLLMClient:
    """Tests for MockLLMClient."""

    @pytest.mark.asyncio
    async def test_default_response(self) -> None:
        """Test default mock response."""
        client = MockLLMClient(default_response="Default answer")
        messages = [LLMMessage(role=MessageRole.USER, content="Hello")]

        response = await client.generate(messages)

        assert response.content == "Default answer"
        assert response.model == "mock-model"
        assert len(client.call_history) == 1

    @pytest.mark.asyncio
    async def test_pattern_matching(self) -> None:
        """Test pattern-based responses."""
        client = MockLLMClient(
            responses={
                r"invoice": MockResponse(content="This is an invoice"),
                r"receipt": MockResponse(content="This is a receipt"),
            },
            default_response="Unknown document",
        )

        # Test invoice pattern
        response = await client.generate([
            LLMMessage(role=MessageRole.USER, content="Classify this invoice")
        ])
        assert response.content == "This is an invoice"

        # Test receipt pattern
        response = await client.generate([
            LLMMessage(role=MessageRole.USER, content="What is this receipt?")
        ])
        assert response.content == "This is a receipt"

        # Test default
        response = await client.generate([
            LLMMessage(role=MessageRole.USER, content="Something else")
        ])
        assert response.content == "Unknown document"

    @pytest.mark.asyncio
    async def test_json_response(self) -> None:
        """Test JSON response generation."""
        client = MockLLMClient(
            default_response=MockResponse(
                content={"type": "invoice", "confidence": 0.95}
            )
        )

        response = await client.generate_json(
            messages=[LLMMessage(role=MessageRole.USER, content="Classify")],
            schema={"type": "object"},
        )

        data = json.loads(response.content)
        assert data["type"] == "invoice"
        assert data["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_call_history(self) -> None:
        """Test call history tracking."""
        client = MockLLMClient()

        await client.generate([
            LLMMessage(role=MessageRole.USER, content="First")
        ])
        await client.generate([
            LLMMessage(role=MessageRole.USER, content="Second")
        ])

        assert len(client.call_history) == 2
        assert client.call_history[0]["messages"][0]["content"] == "First"
        assert client.call_history[1]["messages"][0]["content"] == "Second"

        client.clear_history()
        assert len(client.call_history) == 0

    @pytest.mark.asyncio
    async def test_response_generator(self) -> None:
        """Test dynamic response generator."""
        def generator(messages: list[LLMMessage]) -> MockResponse:
            word_count = len(messages[-1].content.split())
            return MockResponse(content=f"Word count: {word_count}")

        client = MockLLMClient(response_generator=generator)

        response = await client.generate([
            LLMMessage(role=MessageRole.USER, content="one two three")
        ])
        assert response.content == "Word count: 3"

    @pytest.mark.asyncio
    async def test_classification_mock(self) -> None:
        """Test pre-configured classification mock."""
        client = create_classification_mock()

        # Test invoice classification
        response = await client.generate([
            LLMMessage(role=MessageRole.USER, content="Invoice #123")
        ])
        data = json.loads(response.content)
        assert data["document_type"] == "invoice"

        # Test receipt classification
        response = await client.generate([
            LLMMessage(role=MessageRole.USER, content="Receipt from merchant")
        ])
        data = json.loads(response.content)
        assert data["document_type"] == "receipt"

        # Test contract classification
        response = await client.generate([
            LLMMessage(role=MessageRole.USER, content="This Agreement between parties")
        ])
        data = json.loads(response.content)
        assert data["document_type"] == "contract"

        # Test form classification
        response = await client.generate([
            LLMMessage(role=MessageRole.USER, content="Application form with checkbox")
        ])
        data = json.loads(response.content)
        assert data["document_type"] == "form"

    @pytest.mark.asyncio
    async def test_token_tracking(self) -> None:
        """Test token counting in responses."""
        client = MockLLMClient(
            default_response=MockResponse(
                content="Test",
                input_tokens=100,
                output_tokens=25,
                latency_ms=50.0,
            )
        )

        response = await client.generate([
            LLMMessage(role=MessageRole.USER, content="Test")
        ])

        assert response.input_tokens == 100
        assert response.output_tokens == 25
        assert response.total_tokens == 125
        assert response.latency_ms == 50.0
