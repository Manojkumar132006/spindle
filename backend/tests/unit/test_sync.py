"""Unit tests for entity resolution and incremental vault synchronization."""

import uuid

import pytest
from sqlalchemy import select

from spindle.ingestion import (
    EntityResolver,
    VaultSyncEngine,
)
from spindle.models import (
    Character,
    Project,
    SourceDocument,
)


def test_entity_resolver_aliases_and_wikilinks():
    """Test resolving entities across exact names, case variants, aliases, and wikilinks."""
    project_id = uuid.uuid4()
    resolver = EntityResolver(project_id)

    char_id = uuid.uuid4()
    resolver.register(
        entity_id=char_id,
        name="Elena Vareth",
        entity_type="character",
        aliases=["Elena", "the scribe"],
    )

    # Resolution by exact name
    r1 = resolver.resolve("Elena Vareth")
    assert r1 is not None
    assert r1.id == char_id

    # Resolution by lowercase
    r2 = resolver.resolve("elena vareth")
    assert r2 is not None
    assert r2.id == char_id

    # Resolution by alias
    r3 = resolver.resolve("the scribe")
    assert r3 is not None
    assert r3.id == char_id

    # Resolution from wikilink syntax
    r4 = resolver.resolve("[[Elena Vareth|Elena]]")
    assert r4 is not None
    assert r4.id == char_id

    # Resolution from path stem
    r5 = resolver.resolve("Characters/Elena Vareth.md")
    assert r5 is not None
    assert r5.id == char_id

    # Get or create existing entity returns existing ID and False
    resolved_id, is_new = resolver.get_or_create_id("Elena", "character")
    assert resolved_id == char_id
    assert is_new is False

    # Get or create new entity
    new_id, is_new2 = resolver.get_or_create_id("Kaelan", "character")
    assert new_id != char_id
    assert is_new2 is True


@pytest.mark.asyncio
async def test_vault_sync_engine_lifecycle(test_session):
    """Test full incremental sync lifecycle: new, unmodified, modified, and deleted files."""
    project = Project(name="Sync Test Vault")
    test_session.add(project)
    await test_session.commit()

    sync_engine = VaultSyncEngine(test_session, project.id)

    # Batch 1: Initial Ingestion of 3 files
    files_batch_1 = {
        "Characters/Elena Vareth.md": (
            "---\ntype: character\nrole: protagonist\naliases: [the scribe]\n---\n"
            "## Concept\nA court scribe who discovers a loophole.\n"
            "## Psychology\n### Values\nHer brother's safety.\n"
        ),
        "Worldbuilding/Locations/Varenhold.md": (
            "---\ntype: location\nkind: city\nregion: The Vey Valley\n---\n"
            "## What a visitor notices first\nEvery bridge has a toll gate.\n"
        ),
        "Worldbuilding/History/The Binding Oath.md": (
            "---\ntype: event\nwhen: Year 412\norder: 412\npeople: ['[[Elena Vareth]]']\n---\n"
            "## What changed because of it\nCitizens bound to obey the chancellor.\n"
        ),
    }

    res1 = await sync_engine.sync_vault(files_batch_1)
    assert res1.total_files == 3
    assert res1.indexed_files == 3
    assert res1.updated_files == 0
    assert res1.skipped_files == 0
    assert res1.extracted_characters == 1
    assert res1.extracted_locations == 1
    assert res1.extracted_events == 1
    assert res1.extracted_excerpts >= 3

    # Verify database state
    char_q = await test_session.execute(select(Character).where(Character.project_id == project.id))
    chars = char_q.scalars().all()
    assert len(chars) == 1
    assert chars[0].name == "Elena Vareth"
    assert "the scribe" in chars[0].aliases

    # Batch 2: Exact same files -> all skipped
    res2 = await sync_engine.sync_vault(files_batch_1)
    assert res2.total_files == 3
    assert res2.skipped_files == 3
    assert res2.indexed_files == 0
    assert res2.updated_files == 0

    # Batch 3: Modify one file and add one new file
    files_batch_3 = dict(files_batch_1)
    files_batch_3["Characters/Elena Vareth.md"] = (
        "---\ntype: character\nrole: protagonist\nage: 25\naliases: [the scribe]\n---\n"
        "## Concept\nA master archivist seeking freedom.\n"
    )
    files_batch_3["Characters/Aldric Voss.md"] = (
        "---\ntype: character\nrole: antagonist\n---\n## Concept\nThe chancellor.\n"
    )

    res3 = await sync_engine.sync_vault(files_batch_3)
    assert res3.total_files == 4
    assert res3.updated_files == 1  # Elena modified
    assert res3.indexed_files == 1  # Aldric new
    assert res3.skipped_files == 2  # Varenhold and Oath unmodified

    # Batch 4: Remove a file (Oath deleted)
    files_batch_4 = dict(files_batch_3)
    del files_batch_4["Worldbuilding/History/The Binding Oath.md"]

    res4 = await sync_engine.sync_vault(files_batch_4)
    assert res4.deleted_files == 1

    # Verify deleted document is gone from database
    doc_q = await test_session.execute(
        select(SourceDocument).where(
            SourceDocument.project_id == project.id,
            SourceDocument.file_path == "Worldbuilding/History/The Binding Oath.md",
        )
    )
    assert doc_q.scalar_one_or_none() is None
