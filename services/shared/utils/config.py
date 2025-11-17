"""
Application configuration using pydantic-settings.
Loads from environment variables and .env files.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="claim-triage-system", description="Application name")
    environment: str = Field(default="development", description="Environment (dev, staging, prod)")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")

    # LLM Configuration
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.0, description="LLM temperature")
    openai_max_tokens: int = Field(default=2048, description="Max tokens per request")

    # LangSmith (optional observability)
    langsmith_api_key: Optional[str] = Field(None, description="LangSmith API key")
    langsmith_project: str = Field(
        default="claim-triage-system", description="LangSmith project name"
    )
    langsmith_tracing: bool = Field(default=False, description="Enable LangSmith tracing")

    # Embeddings
    embedding_model: str = Field(
        default="text-embedding-3-small", description="Embedding model name (OpenAI)"
    )
    embedding_device: str = Field(default="cpu", description="Device for embeddings (cpu/cuda)")
    embedding_batch_size: int = Field(default=32, description="Batch size for embeddings")

    # Vector Store (ChromaDB)
    chroma_host: str = Field(default="localhost", description="ChromaDB host")
    chroma_port: int = Field(default=8001, description="ChromaDB port")
    chroma_persist_directory: str = Field(
        default="./data/vector_store", description="ChromaDB persistence directory"
    )

    # PostgreSQL
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")
    postgres_db: str = Field(default="claim_triage", description="PostgreSQL database name")

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(None, description="Redis password")

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Security
    encryption_key: Optional[str] = Field(None, description="Encryption key for PHI")
    secret_key: str = Field(
        default="change-me-in-production", description="Secret key for sessions/tokens"
    )

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=60, description="Requests per minute per user")

    # Caching
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")

    # Processing
    max_batch_size: int = Field(default=10, description="Max claims to process in one batch")
    processing_timeout_seconds: int = Field(
        default=300, description="Timeout for claim processing"
    )

    # Monitoring
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Prometheus metrics port")

    # File paths
    policy_docs_path: str = Field(
        default="./data/policy_docs", description="Path to policy documents"
    )
    test_cases_path: str = Field(default="./data/test_cases", description="Path to test cases")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    Uses lru_cache to load settings only once.
    """
    return Settings()
