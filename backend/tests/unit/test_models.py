"""Unit tests verifying all Spindle narrative data models can be inserted and queried."""

import uuid

import pytest
from sqlalchemy import select

from spindle.models import (
    ApprovalStatus,
    BranchStatus,
    BranchType,
    CanonStatus,
    Character,
    CharacterKnowledge,
    Constraint,
    ConstraintSeverity,
    ConstraintType,
    DocumentExcerpt,
    DocumentType,
    EnforcementLevel,
    EnforcementMethod,
    Event,
    KnowledgeStatus,
    Location,
    NarrativeBranch,
    NarrativeThread,
    Project,
    Relationship,
    RuleType,
    SourceDocument,
    Suggestion,
    SuggestionRevision,
    SuggestionType,
    ThreadStatus,
    WorldRule,
)


@pytest.mark.asyncio
async def test_create_and_query_project(test_session):
    """Test creating and retrieving a Project model."""
    project = Project(
        name="The Varenhold Chronicles",
        description="A fantasy universe governed by the Binding Oath.",
        configuration={"genre": "low-fantasy", "theme": "epistemic control"},
    )
    test_session.add(project)
    await test_session.commit()

    result = await test_session.execute(
        select(Project).where(Project.name == "The Varenhold Chronicles")
    )
    saved_project = result.scalar_one_or_none()

    assert saved_project is not None
    assert isinstance(saved_project.id, uuid.UUID)
    assert saved_project.description == "A fantasy universe governed by the Binding Oath."
    assert saved_project.configuration["genre"] == "low-fantasy"
    assert saved_project.created_at is not None
    assert saved_project.updated_at is not None


@pytest.mark.asyncio
async def test_create_source_document_and_excerpts(test_session):
    """Test creating SourceDocument and linked DocumentExcerpt records."""
    project = Project(name="Project Source Docs")
    test_session.add(project)
    await test_session.commit()

    doc = SourceDocument(
        project_id=project.id,
        file_path="Manuscript/Chapter 1.md",
        content_hash="abc123sha256hash",
        document_type=DocumentType.SCENE,
        raw_content="# Chapter 1\nElena copied the oath one page at a time.",
        parsed_metadata={"pov": "Elena Vareth", "chapter": 1},
    )
    test_session.add(doc)
    await test_session.commit()

    dummy_embedding = [0.01 * i for i in range(1536)]
    excerpt = DocumentExcerpt(
        document_id=doc.id,
        excerpt_text="Elena copied the oath one page at a time.",
        start_line=1,
        end_line=2,
        heading="Opening Scene",
        embedding=dummy_embedding,
        metadata_json={"significance": "key discovery"},
    )
    test_session.add(excerpt)
    await test_session.commit()

    result = await test_session.execute(select(SourceDocument).where(SourceDocument.id == doc.id))
    fetched_doc = result.scalar_one()

    assert fetched_doc.file_path == "Manuscript/Chapter 1.md"
    assert fetched_doc.document_type == DocumentType.SCENE

    excerpt_result = await test_session.execute(
        select(DocumentExcerpt).where(DocumentExcerpt.document_id == doc.id)
    )
    fetched_excerpt = excerpt_result.scalar_one()
    assert fetched_excerpt.heading == "Opening Scene"
    assert len(fetched_excerpt.embedding) == 1536


@pytest.mark.asyncio
async def test_create_entities_and_relationships(test_session):
    """Test creating Character, Location, WorldRule, and Character relationships."""
    project = Project(name="Entity Testing Universe")
    test_session.add(project)
    await test_session.commit()

    # Characters
    elena = Character(
        project_id=project.id,
        name="Elena Vareth",
        aliases=["Elena", "the scribe"],
        role="protagonist",
        description="A court scribe who copies the chancellor's laws.",
        personality="Careful, observational, fiercely protective of family.",
        motivations="Free her brother from the binding oath.",
        secrets="Keeps a private ledger of laws the chancellor breaks.",
        current_state="alive",
        canon_status=CanonStatus.CONFIRMED,
    )
    aldric = Character(
        project_id=project.id,
        name="Aldric Voss",
        aliases=["the chancellor"],
        role="antagonist",
        description="The Regent's chancellor who authored the Binding Oath.",
        current_state="alive",
        canon_status=CanonStatus.CONFIRMED,
    )
    test_session.add_all([elena, aldric])
    await test_session.commit()

    # Location
    varenhold = Location(
        project_id=project.id,
        name="Varenhold",
        kind="city",
        region="The Vey Valley",
        description="A walled city where toll gates display the chancellor's seal.",
        attributes={"bridges": 4, "ruling_authority": "The Council and Chancellor"},
    )
    test_session.add(varenhold)

    # World Rule
    oath_rule = WorldRule(
        project_id=project.id,
        name="The Binding Oath Law",
        description=(
            "An oath sworn for food passes unconditionally to descendants until the Regency falls."
        ),
        rule_type=RuleType.MAGIC,
        enforcement_level=EnforcementLevel.HARD,
    )
    test_session.add(oath_rule)

    # Relationship
    rel = Relationship(
        project_id=project.id,
        source_character_id=elena.id,
        target_character_id=aldric.id,
        relationship_type="employer_employee",
        current_state="Distrusted compliance",
        history=[{"event": "Hired to archive laws", "status": "cautious"}],
    )
    test_session.add(rel)
    await test_session.commit()

    # Verify Character
    char_query = await test_session.execute(
        select(Character).where(Character.name == "Elena Vareth")
    )
    fetched_char = char_query.scalar_one()
    assert "the scribe" in fetched_char.aliases
    assert fetched_char.canon_status == CanonStatus.CONFIRMED

    # Verify Relationship
    rel_query = await test_session.execute(
        select(Relationship).where(Relationship.source_character_id == elena.id)
    )
    fetched_rel = rel_query.scalar_one()
    assert fetched_rel.relationship_type == "employer_employee"
    assert fetched_rel.target_character_id == aldric.id


@pytest.mark.asyncio
async def test_create_events_and_threads(test_session):
    """Test Event causality, chronological ordering, and NarrativeThread linkages."""
    project = Project(name="Event Testing Universe")
    test_session.add(project)
    await test_session.commit()

    event1 = Event(
        project_id=project.id,
        title="Signing of the Binding Oath",
        description="Citizens swear loyalty in exchange for winter grain.",
        narrative_position=0.0,
        chronological_timestamp="Year 412 of the Regency",
        chronological_order=412.0,
        participants=["Aldric Voss"],
        causal_dependencies=[],
        confidence=1.0,
        canon_status=CanonStatus.CONFIRMED,
    )
    test_session.add(event1)
    await test_session.commit()

    event2 = Event(
        project_id=project.id,
        title="Discovery of the Loophole",
        description="Elena notices the clause stating the oath binds only while Regency stands.",
        narrative_position=7.2,
        chronological_timestamp="Year 424 of the Regency",
        chronological_order=424.0,
        participants=["Elena Vareth"],
        causal_dependencies=[str(event1.id)],
        confidence=1.0,
        canon_status=CanonStatus.CONFIRMED,
    )
    test_session.add(event2)
    await test_session.commit()

    thread = NarrativeThread(
        project_id=project.id,
        title="Breaking the Binding Oath",
        description=(
            "Elena's quest to exploit the legal loophole without triggering civil collapse."
        ),
        involved_entities=["Elena Vareth", "Aldric Voss"],
        introduction_event_id=event2.id,
        status=ThreadStatus.OPEN,
    )
    test_session.add(thread)
    await test_session.commit()

    thread_query = await test_session.execute(
        select(NarrativeThread).where(NarrativeThread.title == "Breaking the Binding Oath")
    )
    saved_thread = thread_query.scalar_one()
    assert saved_thread.status == ThreadStatus.OPEN
    assert saved_thread.introduction_event_id == event2.id


@pytest.mark.asyncio
async def test_character_knowledge_ledger(test_session):
    """Test recording and querying CharacterKnowledge epistemic state."""
    project = Project(name="Epistemic Universe")
    test_session.add(project)
    await test_session.commit()

    char = Character(
        project_id=project.id,
        name="Elena Vareth",
        current_state="alive",
    )
    test_session.add(char)
    await test_session.commit()

    knowledge = CharacterKnowledge(
        character_id=char.id,
        fact_or_event_id="fact_regency_loophole_page_3",
        knowledge_status=KnowledgeStatus.CONFIRMED,
        acquired_at=7.2,
        acquired_chronological=424.0,
        details="Elena read the 3rd page of the archivist's ledger personally.",
    )
    test_session.add(knowledge)
    await test_session.commit()

    res = await test_session.execute(
        select(CharacterKnowledge).where(CharacterKnowledge.character_id == char.id)
    )
    fetched_knowledge = res.scalar_one()
    assert fetched_knowledge.knowledge_status == KnowledgeStatus.CONFIRMED
    assert fetched_knowledge.fact_or_event_id == "fact_regency_loophole_page_3"
    assert fetched_knowledge.acquired_at == 7.2


@pytest.mark.asyncio
async def test_constraint_model(test_session):
    """Test creating and querying author Constraints."""
    project = Project(name="Constraint Universe")
    test_session.add(project)
    await test_session.commit()

    constraint = Constraint(
        project_id=project.id,
        name="No Anachronistic Loophole Knowledge",
        description=(
            "No character other than Elena may know of the Regency loophole before Chapter 12."
        ),
        constraint_type=ConstraintType.CHARACTER_KNOWLEDGE,
        severity=ConstraintSeverity.HARD,
        enforcement_method=EnforcementMethod.DETERMINISTIC,
        scope={"fact_id": "fact_regency_loophole_page_3", "max_narrative_position": 12.0},
        parameters={"allowed_characters": ["Elena Vareth"]},
        active=True,
    )
    test_session.add(constraint)
    await test_session.commit()

    res = await test_session.execute(
        select(Constraint).where(Constraint.name == "No Anachronistic Loophole Knowledge")
    )
    fetched_constraint = res.scalar_one()
    assert fetched_constraint.severity == ConstraintSeverity.HARD
    assert fetched_constraint.enforcement_method == EnforcementMethod.DETERMINISTIC
    assert fetched_constraint.active is True


@pytest.mark.asyncio
async def test_suggestions_branches_and_revisions(test_session):
    """Test NarrativeBranch, creative Suggestion, and SuggestionRevision lifecycle."""
    project = Project(name="Creative Suggestion Universe")
    test_session.add(project)
    await test_session.commit()

    branch = NarrativeBranch(
        project_id=project.id,
        name="What-If: Council Discovers Loophole Early",
        branch_type=BranchType.WHAT_IF,
        status=BranchStatus.ACTIVE,
    )
    test_session.add(branch)
    await test_session.commit()

    suggestion = Suggestion(
        project_id=project.id,
        branch_id=branch.id,
        suggestion_type=SuggestionType.PLOT_POINT,
        title="Elena Confides in the Council Scribe",
        premise=(
            "Elena shares the discovered loophole with an older colleague before "
            "the archivist locks the vault."
        ),
        detailed_content={"scene_outline": "Elena meets Kaelan in the scriptorium...", "act": 2},
        supporting_evidence=["Examples/The Loophole.md", "Examples/Elena Vareth.md"],
        assumptions=["Kaelan's family is also bound by the oath."],
        validation_results={"canon_pass": True, "temporal_pass": True, "epistemic_warnings": []},
        approval_status=ApprovalStatus.PENDING_AUTHOR_APPROVAL,
    )
    test_session.add(suggestion)
    await test_session.commit()

    revision = SuggestionRevision(
        suggestion_id=suggestion.id,
        revision_number=1,
        content=suggestion.detailed_content,
        validation_results=suggestion.validation_results,
        revision_reason="Initial LangGraph PlotArchitect generation",
    )
    test_session.add(revision)
    await test_session.commit()

    res = await test_session.execute(select(Suggestion).where(Suggestion.id == suggestion.id))
    fetched_sug = res.scalar_one()
    assert fetched_sug.approval_status == ApprovalStatus.PENDING_AUTHOR_APPROVAL
    assert fetched_sug.branch_id == branch.id
    assert len(fetched_sug.supporting_evidence) == 2

    rev_res = await test_session.execute(
        select(SuggestionRevision).where(SuggestionRevision.suggestion_id == suggestion.id)
    )
    fetched_rev = rev_res.scalar_one()
    assert fetched_rev.revision_number == 1
