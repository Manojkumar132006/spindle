"""Integration test verifying model insertion and querying on live PostgreSQL."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from spindle.config import get_settings
from spindle.models import (
    ApprovalStatus,
    CanonStatus,
    Character,
    Constraint,
    ConstraintSeverity,
    ConstraintType,
    DocumentExcerpt,
    DocumentType,
    Event,
    Project,
    SourceDocument,
    Suggestion,
    SuggestionType,
    WorldRule,
)


@pytest.mark.asyncio
async def test_live_postgres_model_operations():
    """Verify that all models can be inserted and queried against live PostgreSQL."""
    settings = get_settings()
    # Connect directly to Postgres using configured DATABASE_URL
    postgres_url = settings.DATABASE_URL
    engine = create_async_engine(postgres_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        # Create Project
        project = Project(
            name="Postgres Integration World",
            description="Testing live PostgreSQL models and pgvector.",
            configuration={"engine": "postgres"},
        )
        session.add(project)
        await session.flush()

        # Create SourceDocument and DocumentExcerpt with Vector
        doc = SourceDocument(
            project_id=project.id,
            file_path="Manuscript/Chapter 1.md",
            content_hash="postgres_hash_12345",
            document_type=DocumentType.SCENE,
            raw_content="The regent looked out upon the silent valley.",
        )
        session.add(doc)
        await session.flush()

        excerpt = DocumentExcerpt(
            document_id=doc.id,
            excerpt_text="The regent looked out upon the silent valley.",
            embedding=[0.05] * 1536,
        )
        session.add(excerpt)

        # Create Character
        character = Character(
            project_id=project.id,
            name="Archon Valerius",
            aliases=["Valerius"],
            current_state="alive",
            canon_status=CanonStatus.CONFIRMED,
        )
        session.add(character)

        # Create Event
        event = Event(
            project_id=project.id,
            title="The Council Convening",
            narrative_position=1.0,
            chronological_timestamp="412 AC",
            chronological_order=412.0,
            participants=["Archon Valerius"],
            confidence=1.0,
        )
        session.add(event)

        # Create WorldRule
        rule = WorldRule(
            project_id=project.id,
            name="Iron Magic Binding",
            description="Iron nullifies oath magic.",
        )
        session.add(rule)

        # Create Constraint
        constraint = Constraint(
            project_id=project.id,
            name="Valerius Mortality Rule",
            description="Valerius cannot act after death.",
            constraint_type=ConstraintType.CANON,
            severity=ConstraintSeverity.HARD,
        )
        session.add(constraint)

        # Create Suggestion
        suggestion = Suggestion(
            project_id=project.id,
            suggestion_type=SuggestionType.PLOT_POINT,
            title="Valerius Inspects the Vault",
            premise="Valerius uncovers unauthorized ledger copies.",
            approval_status=ApprovalStatus.PENDING_AUTHOR_APPROVAL,
        )
        session.add(suggestion)

        await session.commit()

        # Query back and verify
        res = await session.execute(select(Project).where(Project.id == project.id))
        retrieved_project = res.scalar_one()
        assert retrieved_project.name == "Postgres Integration World"

        # Verify Vector excerpt in PostgreSQL
        excerpt_res = await session.execute(
            select(DocumentExcerpt).where(DocumentExcerpt.document_id == doc.id)
        )
        retrieved_excerpt = excerpt_res.scalar_one()
        assert len(retrieved_excerpt.embedding) == 1536

        # Clean up test project
        await session.delete(project)
        await session.commit()

    await engine.dispose()
