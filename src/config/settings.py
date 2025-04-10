"""Application settings and configuration.

This module contains all the configuration settings for the application
using pydantic-settings.
It reads configuration from environment variables and .env files.
"""

from pydantic import PostgresDsn, HttpUrl, SecretStr, BaseModel, Field
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


class Settings(BaseModel):
    """Application settings."""

    core: CoreSettings = CoreSettings()
    database: DataBaseSettings = DataBaseSettings()
    scraper: ScraperSettings = ScraperSettings()


settings = Settings()
