"""Tests for backend configuration settings."""

from spindle.config import Settings, get_settings


def test_default_settings():
    settings = Settings()
    assert settings.PROJECT_NAME == "Spindle"
    assert settings.API_V1_STR == "/api/v1"
    assert "postgresql+asyncpg://" in settings.DATABASE_URL
    assert not settings.DEBUG


def test_testing_environment_override(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///test.db")
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.is_testing is True
    assert settings.get_database_url() == "sqlite+aiosqlite:///test.db"
    get_settings.cache_clear()


def test_cors_origins():
    settings = Settings()
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "app://obsidian.md" in settings.CORS_ORIGINS
