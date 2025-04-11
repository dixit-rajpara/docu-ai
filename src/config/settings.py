"""Application settings and configuration.

This module contains all the configuration settings for the application
using pydantic-settings.
It reads configuration from environment variables and .env files.
"""

from typing import Optional

from pydantic import PostgresDsn, HttpUrl, SecretStr, BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Application settings."""

    log_level: str = Field(default="INFO")
    embedding_dimension: int = Field(default=1536)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ScraperSettings(BaseSettings):
    """Scraper API configuration."""

    provider: str = Field(default="crawl4ai")
    api_host: HttpUrl = Field(default="http://localhost:11235")
    api_key: SecretStr = Field(default=None)
    polling_interval: float = Field(default=2.0)
    request_timeout: float = Field(default=60.0)
    default_job_timeout: float = Field(default=300.0)
    max_concurrent_jobs_override: int = Field(default=10)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="scraper_",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DataBaseSettings(BaseSettings):
    """Main application settings."""

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="postgres")
    password: SecretStr = Field(default="postgres")
    db: str = Field(default="docu_ai")
    pool_size: int = Field(default=5)
    max_overflow: int = Field(default=10)
    echo: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="postgres_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> PostgresDsn:
        """Constructs the database URL from config parameters."""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            path=self.db,
        )

    @property
    def database_url_str(self) -> str:
        """Returns the database URL as a string for SQLAlchemy."""
        return str(self.database_url)


class EmbeddingSettings(BaseSettings):
    """Settings for embedding generation."""

    provider: str = Field(
        default="openai",
        description="Embedding provider ('openai', 'huggingface', etc.)",
    )
    # --- OpenAI Specific ---
    openai_api_key: SecretStr = Field(default=None, description="API key for OpenAI")
    openai_model: str = Field(
        default="text-embedding-3-small", description="OpenAI model for embeddings"
    )

    # --- HuggingFace Specific ---
    huggingface_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace model identifier (local path or HF Hub name)",
    )
    # Device can be 'cpu', 'cuda', 'cuda:0', 'mps' (for Apple Silicon), etc.
    # 'auto' will let sentence-transformers try to pick the best available device.
    huggingface_device: str = Field(
        default="auto",
        description="Device for HuggingFace model ('cpu', 'cuda', 'mps', 'auto')",
    )

    # --- Ollama Specific ---
    ollama_host: str = Field(
        default="http://localhost:11434", description="Host URL for the Ollama server"
    )
    ollama_model: str = Field(
        default="nomic-embed-text",
        description="Ollama model name for embeddings (must be pulled in Ollama)",
    )

    # --- General ---
    # Dimension is critical for DB schema setup, determined by the chosen model.
    # Keep it explicitly configurable for clarity, but it *must* match the actual
    # model output.
    # Defaults common for OpenAI models. Adjust if using different models/providers.
    dimension: int = Field(
        default=1536, description="Output dimension of the embedding model"
    )
    batch_size: int = Field(
        default=32, description="Batch size for generating embeddings"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="embedding_",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CompletionSettings(BaseSettings):
    """Settings for LLM text completion/generation."""

    # Default model to use if not specified in the call.
    # LiteLLM format: "provider/model_name" e.g., "openai/gpt-3.5-turbo", "anthropic/claude-2", "ollama/llama2"
    # Or just model name if provider can be inferred from env vars (e.g., "gpt-4")
    model: str = Field(
        default="ollama/llama3.1", description="Default model for LLM completion"
    )
    api_base: Optional[HttpUrl] = Field(
        default=None,
        description="Optional LiteLLM API base URL",
    )
    temperature: float = Field(
        default=0.1, description="Default creativity/randomness (0.0-2.0)"
    )
    max_tokens: Optional[int] = Field(
        default=256, description="Default maximum tokens to generate"
    )
    timeout: Optional[float] = Field(
        default=600.0, description="Default request timeout in seconds"
    )  # LiteLLM default is 600

    # If set, enables LiteLLM proxy features (e.g., http://localhost:4000)
    # Useful for logging, fallback, caching etc. Set if you run `litellm --proxy`
    proxy_base_url: Optional[HttpUrl] = Field(
        default=None, description="Optional LiteLLM proxy base URL"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="llm_completion_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("api_base", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        # If input from env/dotenv is '', convert it to None before further validation
        if v == "":
            return None
        # If it's already None or a valid string, pass it through
        return v


class Settings(BaseModel):
    """Application settings."""

    core: CoreSettings = CoreSettings()
    database: DataBaseSettings = DataBaseSettings()
    scraper: ScraperSettings = ScraperSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    completion: CompletionSettings = CompletionSettings()


settings = Settings()
