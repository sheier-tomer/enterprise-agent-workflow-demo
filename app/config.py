"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables with validation.
"""

from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://workflow_user:workflow_pass@localhost:5432/workflow_db",
        description="Async PostgreSQL connection string",
    )
    database_echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy query logging",
    )

    # LLM Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (leave empty for mock mode)",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use",
    )
    use_mock_llm: bool = Field(
        default=True,
        description="Use mock LLM responses (deterministic, no API calls)",
    )

    # Embedding Configuration
    embedding_provider: Literal["openai", "sentence-transformers", "mock"] = Field(
        default="sentence-transformers",
        description="Embedding provider: openai, sentence-transformers, or mock",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Embedding model name",
    )
    embedding_dimension: int = Field(
        default=384,
        description="Embedding vector dimension",
    )

    # Application Configuration
    app_name: str = Field(
        default="Enterprise Agentic Workflow Engine",
        description="Application name",
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # Guardrails Configuration
    max_tool_calls_per_workflow: int = Field(
        default=20,
        description="Maximum tool calls allowed per workflow execution",
    )
    confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence score to skip escalation",
    )

    # Data Seeding
    seed_on_startup: bool = Field(
        default=True,
        description="Seed database with synthetic data on startup",
    )
    seed_customers_count: int = Field(
        default=50,
        description="Number of synthetic customers to generate",
    )
    seed_transactions_count: int = Field(
        default=500,
        description="Number of synthetic transactions to generate",
    )
    seed_policies_count: int = Field(
        default=10,
        description="Number of synthetic policy documents to generate",
    )

    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="Server host",
    )
    port: int = Field(
        default=8000,
        description="Server port",
    )
    workers: int = Field(
        default=1,
        description="Number of worker processes",
    )

    @field_validator("confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        """Ensure confidence threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("confidence_threshold must be between 0 and 1")
        return v

    @field_validator("use_mock_llm", mode="before")
    @classmethod
    def auto_enable_mock_if_no_api_key(cls, v: bool, info) -> bool:
        """Automatically enable mock mode if no API key is provided."""
        data = info.data
        if "openai_api_key" in data and not data["openai_api_key"]:
            return True
        return v


# Global settings instance
settings = Settings()
