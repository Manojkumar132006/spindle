"""Unit tests for LangGraph multi-agent orchestration, state flow, and bounded revisions."""

import uuid
from typing import Any

import pytest

from spindle.agents.graph import build_narrative_graph
from spindle.agents.state import GraphState
from spindle.core.constraints.base import BaseConstraintValidator
from spindle.core.constraints.engine import ConstraintEngine
from spindle.core.constraints.report import (
    ValidationDiagnostic,
    ValidationOutcome,
)
from spindle.core.state_service import StoryState
from spindle.llm.client import BaseLLMClient
from spindle.models.base import ConstraintSeverity
from spindle.models.entity import Character
from spindle.models.event import Event


class FakeTestLLMClient(BaseLLMClient):
    """Test-local stub for unit testing LangGraph workflow state transitions without network."""

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        return "Test LLM completion."

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[Any],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> Any:
        name = response_model.__name__.lower()
        if "director" in name:
            mode = "plot_point"
            if "side_story" in prompt:
                mode = "side_story"
            elif "continuity_analysis" in prompt:
                mode = "continuity_analysis"
            data = {
                "generation_mode": mode,
                "scope_summary": "Test scope",
                "required_analyses": ["Analysis A"],
                "target_characters": ["Elena Vareth"],
                "target_events": ["Discovery of the Loophole"],
            }
        elif "canon" in name:
            data = {
                "established_precedents": ["Precedent A"],
                "unresolved_threads": ["Thread 1"],
                "active_canon_facts": ["Fact 1"],
                "contradiction_risks": [],
            }
        elif "character" in name:
            data = {
                "motivation_alignment": "High",
                "behavioral_plausibility_score": 8.5,
                "relationship_dynamics": [],
                "knowledge_boundaries": [],
                "potential_character_growth": "Positive",
            }
        elif "timeline" in name:
            data = {
                "chronological_placement": "Chapter 1",
                "temporal_ordering_valid": True,
                "character_presence_confirmed": True,
                "dependencies_satisfied": True,
                "timeline_notes": "None",
            }
        elif "causal" in name:
            data = {
                "prerequisites": ["Discovery of the Loophole"],
                "immediate_consequences": ["Outcome A"],
                "downstream_implications": ["Impact B"],
                "causal_plausibility_score": 9.0,
            }
        elif "plot" in name or "proposal" in name:
            data = {
                "title": "A Test Plot Proposal",
                "premise": "Elena acts on the discovery.",
                "narrative_purpose": "Advance the test plot.",
                "involved_characters": ["Elena Vareth"],
                "preconditions": [],
                "causal_dependencies": ["Discovery of the Loophole"],
                "expected_consequences": [],
                "supporting_evidence": ["Examples/The Loophole.md"],
                "assumptions": [],
                "detailed_content": {
                    "act": 1,
                    "scene_beats": ["Elena enters", "Elena discovers", "Elena exits"],
                },
            }
        elif "critic" in name:
            data = {
                "originality_score": 8.0,
                "narrative_plausibility_score": 8.5,
                "thematic_relevance_score": 9.0,
                "identified_weaknesses": [],
                "overall_verdict": "Solid test execution.",
            }
        elif "branch" in name:
            data = {
                "branches": [
                    {
                        "branch_name": "Direct Confrontation at the Toll",
                        "dramatic_angle": "High Stakes Confrontation",
                        "premise": "Elena confronts the archivist directly.",
                        "scene_beats": ["Elena demands the ledger", "The archivist threatens alarm", "A standoff ensues"],
                        "involved_characters": ["Elena Vareth"],
                        "causal_dependencies": ["Discovery of the Loophole"],
                        "causal_consequences": ["Archivist sounds alarm"],
                        "constraint_risks": [],
                        "supporting_evidence": ["Examples/The Loophole.md"],
                    },
                    {
                        "branch_name": "Covert Night Infiltration",
                        "dramatic_angle": "Stealth and Deception",
                        "premise": "Elena sneaks into the archive after curfew.",
                        "scene_beats": ["Elena bypasses the gate", "She copies the pages", "She escapes unseen"],
                        "involved_characters": ["Elena Vareth"],
                        "causal_dependencies": ["Discovery of the Loophole"],
                        "causal_consequences": ["Parchment reported missing"],
                        "constraint_risks": [],
                        "supporting_evidence": ["Examples/The Loophole.md"],
                    },
                ]
            }
        else:
            data = {}
        return response_model.model_validate(data)


@pytest.mark.asyncio
async def test_langgraph_full_workflow_execution():
    """Test full 8-agent LangGraph execution from request to result synthesis."""
    project_id = uuid.uuid4()
    test_llm = FakeTestLLMClient()

    # Create dummy story state
    char = Character(
        id=uuid.uuid4(),
        project_id=project_id,
        name="Elena Vareth",
        current_state="alive",
    )
    discovery_event = Event(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Discovery of the Loophole",
        narrative_position=5.0,
    )
    story_state = StoryState(
        project_id=project_id,
        narrative_position=7.2,
        characters=[char],
        established_events=[discovery_event],
    )

    engine = ConstraintEngine()
    graph = build_narrative_graph(llm_client=test_llm, constraint_engine=engine)

    initial_state: GraphState = {
        "project_id": str(project_id),
        "narrative_position": 7.2,
        "branch_id": None,
        "user_request": "Elena searches the archive for evidence about the Binding Oath.",
        "generation_mode": "plot_point",
        "story_state": story_state,
        "revision_count": 0,
        "revision_notes": [],
    }

    final_state = await graph.ainvoke(initial_state)

    # Verify all agent outputs are populated in GraphState
    assert "director_output" in final_state
    assert final_state["director_output"]["generation_mode"] == "plot_point"

    assert "canon_analysis" in final_state
    assert len(final_state["canon_analysis"]["established_precedents"]) > 0

    assert "character_analysis" in final_state
    assert final_state["character_analysis"]["behavioral_plausibility_score"] > 0

    assert "timeline_analysis" in final_state
    assert final_state["timeline_analysis"]["temporal_ordering_valid"] is True

    assert "causal_analysis" in final_state
    assert len(final_state["causal_analysis"]["prerequisites"]) > 0

    assert "draft_proposal" in final_state
    assert "title" in final_state["draft_proposal"]
    assert "premise" in final_state["draft_proposal"]

    assert "validation_report" in final_state
    assert final_state["validation_report"]["is_valid"] is True

    assert "critic_evaluation" in final_state
    assert final_state["critic_evaluation"]["originality_score"] > 0

    assert "final_suggestion" in final_state
    suggestion = final_state["final_suggestion"]
    assert suggestion["title"] == final_state["draft_proposal"]["title"]
    assert suggestion["approval_status"] == "pending_author_approval"


class AlwaysFailValidator(BaseConstraintValidator):
    """Validator designed to simulate hard constraint failure for testing bounded revision."""

    def __init__(self, fail_count: int = 1):
        self.call_count = 0
        self.fail_count = fail_count

    async def validate(
        self,
        proposal: dict[str, Any],
        story_state: StoryState,
    ) -> list[ValidationDiagnostic]:
        self.call_count += 1
        if self.call_count <= self.fail_count:
            return [
                ValidationDiagnostic(
                    rule_id="TEST_HARD_FAIL",
                    rule_name="Simulated Failure",
                    outcome=ValidationOutcome.FAIL,
                    severity=ConstraintSeverity.HARD,
                    message="Proposal attempts prohibited action.",
                    remediation_hint="Remove the prohibited action.",
                )
            ]
        return [
            ValidationDiagnostic(
                rule_id="TEST_HARD_FAIL",
                rule_name="Simulated Failure",
                outcome=ValidationOutcome.PASS,
                severity=ConstraintSeverity.HARD,
                message="Proposal adheres to rule.",
            )
        ]


@pytest.mark.asyncio
async def test_langgraph_bounded_revision_loop():
    """Test conditional routing: hard failure triggers revision back to Plot Architect and terminates."""
    project_id = uuid.uuid4()
    test_llm = FakeTestLLMClient()

    # Constraint engine with persistent failure to test bound (max 2 revisions)
    failing_validator = AlwaysFailValidator(fail_count=10)
    engine = ConstraintEngine(validators=[failing_validator])

    graph = build_narrative_graph(llm_client=test_llm, constraint_engine=engine)

    story_state = StoryState(project_id=project_id, narrative_position=5.0)

    initial_state: GraphState = {
        "project_id": str(project_id),
        "narrative_position": 5.0,
        "branch_id": None,
        "user_request": "Elena performs an action violating constraints.",
        "generation_mode": "plot_point",
        "story_state": story_state,
        "revision_count": 0,
        "revision_notes": [],
    }

    final_state = await graph.ainvoke(initial_state)

    # Must have looped through plot_architect up to bounded limit (revision_count == 2)
    assert final_state["revision_count"] == 2
    assert len(final_state["revision_notes"]) >= 2
    assert "Simulated Failure" in final_state["revision_notes"][0]
    # And finished at ResultSynthesizer despite failure
    assert "final_suggestion" in final_state
    assert final_state["final_suggestion"]["validation_results"]["has_hard_failures"] is True
