"""SQLAlchemy 2.0 asynchronous database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from spindle.config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


def create_engine_and_session(
    database_url: str | None = None,
    echo: bool | None = None,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create and return an async engine and session factory."""
    settings = get_settings()
    url = database_url or settings.get_database_url()
    is_echo = settings.DB_ECHO if echo is None else echo

    engine_kwargs: dict = {"echo": is_echo}

    if "sqlite" in url:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

    engine = create_async_engine(url, **engine_kwargs)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return engine, session_factory


# Default application engine and sessionmaker
engine, async_session_factory = create_engine_and_session()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def verify_connection(test_engine: AsyncEngine | None = None) -> bool:
    """Verify database connectivity."""
    target_engine = test_engine or engine
    async with target_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        return result.scalar() == 1
