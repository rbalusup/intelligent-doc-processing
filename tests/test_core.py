"""Tests for core utilities."""

import pytest

from idp.core.config import Settings, get_settings
from idp.core.exceptions import IDPError, LLMError, AgentError
from idp.core.logging import configure_logging, get_logger
from idp.core.retry import RetryConfig


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = Settings()
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.aws_region == "us-east-1"
        assert settings.storage_backend == "local"

    def test_settings_override(self) -> None:
        """Test settings can be overridden."""
        settings = Settings(
            environment="production",
            debug=True,
            aws_region="us-west-2",
        )
        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.aws_region == "us-west-2"

    def test_get_settings_cached(self) -> None:
        """Test settings are cached."""
        # Clear cache first
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2


class TestExceptions:
    """Tests for custom exceptions."""

    def test_idp_error_basic(self) -> None:
        """Test basic IDPError."""
        error = IDPError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}

    def test_idp_error_with_details(self) -> None:
        """Test IDPError with details."""
        error = IDPError("Failed", details={"code": 500, "reason": "timeout"})
        assert "Failed" in str(error)
        assert "code" in str(error)
        assert error.details["code"] == 500

    def test_llm_error_retryable(self) -> None:
        """Test LLMError retryable flag."""
        error = LLMError("Rate limited", retryable=True)
        assert error.retryable is True

        error2 = LLMError("Invalid input", retryable=False)
        assert error2.retryable is False

    def test_agent_error(self) -> None:
        """Test AgentError with agent name."""
        error = AgentError(
            "Agent failed",
            agent_name="ClassificationAgent",
            details={"input_size": 1000},
        )
        assert error.agent_name == "ClassificationAgent"
        assert error.details["input_size"] == 1000


class TestRetryConfig:
    """Tests for retry configuration."""

    def test_default_config(self) -> None:
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0

    def test_should_retry_generic_exception(self) -> None:
        """Test should_retry with generic exception."""
        config = RetryConfig()
        assert config.should_retry(Exception("test")) is True

    def test_should_retry_specific_exceptions(self) -> None:
        """Test should_retry with specific exception types."""
        config = RetryConfig(retryable_exceptions=(ValueError,))
        assert config.should_retry(ValueError("test")) is True
        assert config.should_retry(TypeError("test")) is False

    def test_should_retry_with_retryable_attribute(self) -> None:
        """Test should_retry respects retryable attribute."""
        config = RetryConfig()

        retryable_error = LLMError("Rate limited", retryable=True)
        assert config.should_retry(retryable_error) is True

        non_retryable_error = LLMError("Invalid", retryable=False)
        assert config.should_retry(non_retryable_error) is False


class TestLogging:
    """Tests for logging utilities."""

    def test_configure_logging(self, settings: Settings) -> None:
        """Test logging configuration."""
        configure_logging(settings)
        # Should not raise

    def test_get_logger(self) -> None:
        """Test getting a logger."""
        logger = get_logger("test")
        assert logger is not None

    def test_get_logger_with_context(self) -> None:
        """Test logger with initial context."""
        logger = get_logger("test", request_id="123", user="test")
        assert logger is not None
