"""Typed GraphState and intermediate agent schemas for LangGraph multi-agent execution."""

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class DirectorOutput(BaseModel):
    """Output produced by Agent 1: Narrative Director."""

    generation_mode: str = Field(description="plot_point, side_story, or continuity_analysis")
    scope_summary: str = Field(description="High-level narrative focus and objectives")
    required_analyses: list[str] = Field(default_factory=list)
    target_characters: list[str] = Field(default_factory=list)
    target_events: list[str] = Field(default_factory=list)


class CanonAnalystOutput(BaseModel):
    """Output produced by Agent 2: Canon Analyst."""

    established_precedents: list[str] = Field(default_factory=list)
    unresolved_threads: list[str] = Field(default_factory=list)
    active_canon_facts: list[str] = Field(default_factory=list)
    contradiction_risks: list[str] = Field(default_factory=list)


class CharacterAnalystOutput(BaseModel):
    """Output produced by Agent 3: Character Analyst."""

    motivation_alignment: str = Field(default="")
    behavioral_plausibility_score: float = Field(default=8.0)
    relationship_dynamics: list[str] = Field(default_factory=list)
    knowledge_boundaries: list[str] = Field(default_factory=list)
    potential_character_growth: str = Field(default="")


class TimelineAnalystOutput(BaseModel):
    """Output produced by Agent 4: Timeline Analyst."""

    chronological_placement: str = Field(default="")
    temporal_ordering_valid: bool = Field(default=True)
    character_presence_confirmed: bool = Field(default=True)
    dependencies_satisfied: bool = Field(default=True)
    timeline_notes: str = Field(default="")


class CausalReasonerOutput(BaseModel):
    """Output produced by Agent 5: Causal Reasoner."""

    prerequisites: list[str] = Field(default_factory=list)
    immediate_consequences: list[str] = Field(default_factory=list)
    downstream_implications: list[str] = Field(default_factory=list)
    causal_plausibility_score: float = Field(default=8.0)


class PlotProposalOutput(BaseModel):
    """Output produced by Agent 6: Plot Architect."""

    title: str = Field(description="Concise title for the proposed development")
    premise: str = Field(description="Clear, 1-3 sentence core premise")
    narrative_purpose: str = Field(description="Dramatic or thematic purpose")
    involved_characters: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    causal_dependencies: list[str] = Field(default_factory=list)
    expected_consequences: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    detailed_content: dict[str, Any] = Field(default_factory=dict)


class NarrativeCriticOutput(BaseModel):
    """Output produced by Agent 8: Narrative Critic."""

    originality_score: float = Field(default=8.0)
    narrative_plausibility_score: float = Field(default=8.0)
    thematic_relevance_score: float = Field(default=8.0)
    identified_weaknesses: list[str] = Field(default_factory=list)
    overall_verdict: str = Field(default="")


class GraphState(TypedDict, total=False):
    """Typed shared state container flowing through the LangGraph workflow."""

    project_id: str
    narrative_position: float
    branch_id: str | None
    user_request: str
    generation_mode: str

    # Narrative State Snapshot
    story_state: Any

    # Agent Analyses
    director_output: dict[str, Any]
    canon_analysis: dict[str, Any]
    character_analysis: dict[str, Any]
    timeline_analysis: dict[str, Any]
    causal_analysis: dict[str, Any]

    # Creative Proposal & Constraint Validation
    draft_proposal: dict[str, Any]
    validation_report: dict[str, Any]
    critic_evaluation: dict[str, Any]

    # Revision Loop Bounds
    revision_count: int
    revision_notes: list[str]

    # Final Synthesized Result & Error Tracking
    final_suggestion: dict[str, Any]
    errors: list[str]
