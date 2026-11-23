"""Configuration settings for Spindle."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Spindle application settings loaded from environment variables."""

    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False
    PROJECT_NAME: str = "Spindle"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://spindle:spindle_password@localhost:5432/spindle"
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "app://obsidian.md"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_testing(self) -> bool:
        """Check if environment is set to testing."""
        return self.ENVIRONMENT == "testing"

    def get_database_url(self) -> str:
        """Return the active database connection string."""
        if self.is_testing:
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
