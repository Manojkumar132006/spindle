"""Tests for database engine, session, and connectivity."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.database import (
    Base,
    create_engine_and_session,
    verify_connection,
)


@pytest.mark.asyncio
async def test_create_engine_and_session():
    test_url = "sqlite+aiosqlite:///:memory:"
    engine, session_factory = create_engine_and_session(database_url=test_url, echo=False)

    assert engine is not None
    assert session_factory is not None

    async with session_factory() as session:
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_verify_connection(test_engine):
    is_connected = await verify_connection(test_engine)
    assert is_connected is True


def test_declarative_base():
    assert Base is not None
    assert hasattr(Base, "metadata")


def test_pgvector_type_support():
    from pgvector.sqlalchemy import Vector

    vector_col = Vector(1536)
    assert vector_col.dim == 1536
