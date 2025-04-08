"""Application settings and configuration.

This module contains all the configuration settings for the application using pydantic-settings.
It reads configuration from environment variables and .env files.
"""

from pydantic import PostgresDsn, HttpUrl, SecretStr, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Application settings."""

    log_level: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CrawlerSettings(BaseSettings):
    """Crawler API configuration."""

    provider: str
    api_host: HttpUrl
    api_key: SecretStr

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="crawler_",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DataBaseSettings(BaseSettings):
    """Main application settings."""

    host: str
    port: int
    user: str
    password: SecretStr
    db: str

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
            scheme="postgresql",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            path=self.db,
        )


class Settings(BaseModel):
    """Application settings."""

    core: CoreSettings = CoreSettings()
    database: DataBaseSettings = DataBaseSettings()
    crawler: CrawlerSettings = CrawlerSettings()


settings = Settings()
