"""API dependency injections for database sessions and project context."""

import uuid
from typing import Annotated

from fastapi import Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.database import get_db_session
from spindle.models.project import Project


async def get_current_project(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_project_id: Annotated[str | None, Header(alias="X-Project-ID")] = None,
    project_id: Annotated[str | None, Query(description="Project UUID")] = None,
) -> Project:
    """Resolve the active narrative Project context.

    Checks X-Project-ID header or project_id query parameter. If neither is provided
    or found, resolves or creates a default project workspace.
    """
    raw_id = x_project_id or project_id

    if raw_id:
        try:
            target_uuid = uuid.UUID(raw_id)
            stmt = select(Project).where(Project.id == target_uuid)
            res = await session.execute(stmt)
            project = res.scalar_one_or_none()
            if project is not None:
                return project
        except (ValueError, TypeError):
            pass

    # Fallback to or create default project
    stmt = select(Project).order_by(Project.created_at.asc()).limit(1)
    res = await session.execute(stmt)
    project = res.scalar_one_or_none()

    if project is None:
        project = Project(
            name="Default Project",
            description="Default narrative universe workspace.",
            configuration={"theme": "default"},
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

    return project
