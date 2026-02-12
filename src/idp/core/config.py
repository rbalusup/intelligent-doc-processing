"""Configuration management using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="IDP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # AWS Configuration
    aws_region: str = Field(default="us-east-1", description="AWS region for Bedrock")
    aws_profile: str | None = Field(default=None, description="AWS profile name")
    aws_endpoint_url: str | None = Field(
        default=None, description="Custom AWS endpoint URL (for local testing)"
    )

    # Bedrock Configuration
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Default Bedrock model ID",
    )
    bedrock_max_tokens: int = Field(default=4096, description="Max tokens for LLM responses")
    bedrock_temperature: float = Field(default=0.0, description="Temperature for LLM responses")

    # Storage Configuration
    storage_backend: Literal["local", "s3", "memory"] = "local"
    storage_local_path: str = Field(default="./data", description="Local storage path")
    storage_s3_bucket: str | None = Field(default=None, description="S3 bucket name")
    storage_s3_prefix: str = Field(default="documents/", description="S3 key prefix")

    # Retry Configuration
    retry_max_attempts: int = Field(default=3, description="Max retry attempts")
    retry_base_delay: float = Field(default=1.0, description="Base delay between retries (seconds)")
    retry_max_delay: float = Field(default=30.0, description="Max delay between retries (seconds)")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "console"

    # Evaluation
    evaluation_dataset_path: str = Field(
        default="./datasets", description="Path to evaluation datasets"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
