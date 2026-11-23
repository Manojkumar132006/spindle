"""Individual agent node functions for the LangGraph narrative intelligence workflow."""

import json
from typing import Any

from spindle.agents.state import (
    CanonAnalystOutput,
    CausalReasonerOutput,
    CharacterAnalystOutput,
    DirectorOutput,
    GraphState,
    NarrativeCriticOutput,
    PlotProposalOutput,
    TimelineAnalystOutput,
)
from spindle.core.constraints.engine import ConstraintEngine
from spindle.core.state_service import StoryState
from spindle.llm.client import BaseLLMClient
from spindle.llm.prompts import (
    CANON_ANALYST_SYSTEM_PROMPT,
    CAUSAL_REASONER_SYSTEM_PROMPT,
    CHARACTER_ANALYST_SYSTEM_PROMPT,
    DIRECTOR_SYSTEM_PROMPT,
    NARRATIVE_CRITIC_SYSTEM_PROMPT,
    PLOT_ARCHITECT_SYSTEM_PROMPT,
    TIMELINE_ANALYST_SYSTEM_PROMPT,
)


def create_director_node(llm_client: BaseLLMClient):
    """Factory for Agent 1: Narrative Director node."""

    async def director_node(state: GraphState) -> dict[str, Any]:
        user_req = state.get("user_request", "")
        pos = state.get("narrative_position", 0.0)
        mode = state.get("generation_mode", "plot_point")

        prompt = (
            f"User Request: {user_req}\n"
            f"Target Narrative Position: {pos}\n"
            f"Requested Mode: {mode}\n\n"
            "Classify the request, set the analytical scope, and determine the involved entities."
        )

        output = await llm_client.generate_structured(
            prompt=prompt,
            response_model=DirectorOutput,
            system_prompt=DIRECTOR_SYSTEM_PROMPT,
        )
        return {
            "director_output": output.model_dump(),
            "generation_mode": output.generation_mode,
        }

    return director_node


def create_canon_analyst_node(llm_client: BaseLLMClient):
    """Factory for Agent 2: Canon Analyst node."""

    async def canon_analyst_node(state: GraphState) -> dict[str, Any]:
        story_state: StoryState | None = state.get("story_state")
        user_req = state.get("user_request", "")

        events_summary = []
        threads_summary = []
        rules_summary = []

        if story_state:
            events_summary = [
                f"- {e.title} (pos {e.narrative_position})"
                for e in story_state.established_events[:10]
            ]
            threads_summary = [f"- {t.title}: {t.status}" for t in story_state.open_threads[:5]]
            rules_summary = [
                f"- {r.name}: {r.description[:100]}" for r in story_state.active_world_rules[:5]
            ]

        prompt = (
            f"User Request: {user_req}\n"
            f"Established Events:\n" + "\n".join(events_summary or ["None"]) + "\n\n"
            "Open Narrative Threads:\n" + "\n".join(threads_summary or ["None"]) + "\n\n"
            "Active World Rules:\n" + "\n".join(rules_summary or ["None"]) + "\n\n"
            "Analyze active canon precedents, threads, and potential contradiction risks."
        )

        output = await llm_client.generate_structured(
            prompt=prompt,
            response_model=CanonAnalystOutput,
            system_prompt=CANON_ANALYST_SYSTEM_PROMPT,
        )
        return {"canon_analysis": output.model_dump()}

    return canon_analyst_node


def create_character_analyst_node(llm_client: BaseLLMClient):
    """Factory for Agent 3: Character Analyst node."""

    async def character_analyst_node(state: GraphState) -> dict[str, Any]:
        story_state: StoryState | None = state.get("story_state")
        user_req = state.get("user_request", "")
        director = state.get("director_output", {})

        char_profiles = []
        if story_state:
            for char in story_state.characters[:5]:
                char_profiles.append(
                    f"Name: {char.name}\nRole: {char.role}\nWound: {char.fears}\n"
                    f"Values: {char.motivations}\nState: {char.current_state}"
                )

        prompt = (
            f"User Request: {user_req}\n"
            f"Scope: {director.get('scope_summary', '')}\n"
            f"Characters in Universe:\n" + "\n---\n".join(char_profiles or ["None"]) + "\n\n"
            "Evaluate psychological coherence, motivation alignment, and epistemic boundaries."
        )

        output = await llm_client.generate_structured(
            prompt=prompt,
            response_model=CharacterAnalystOutput,
            system_prompt=CHARACTER_ANALYST_SYSTEM_PROMPT,
        )
        return {"character_analysis": output.model_dump()}

    return character_analyst_node


def create_timeline_analyst_node(llm_client: BaseLLMClient):
    """Factory for Agent 4: Timeline Analyst node."""

    async def timeline_analyst_node(state: GraphState) -> dict[str, Any]:
        story_state: StoryState | None = state.get("story_state")
        user_req = state.get("user_request", "")
        pos = state.get("narrative_position", 0.0)

        timeline_events = []
        if story_state:
            for ev in story_state.chronological_events[:10]:
                timeline_events.append(
                    f"- Order {ev.chronological_order or ev.narrative_position}: {ev.title} ({ev.chronological_timestamp or 'No date'})"
                )

        prompt = (
            f"User Request: {user_req}\n"
            f"Target Narrative Position: {pos}\n"
            f"Preceding Chronology:\n" + "\n".join(timeline_events or ["None"]) + "\n\n"
            "Analyze chronological sequence, character presence, and temporal consistency."
        )

        output = await llm_client.generate_structured(
            prompt=prompt,
            response_model=TimelineAnalystOutput,
            system_prompt=TIMELINE_ANALYST_SYSTEM_PROMPT,
        )
        return {"timeline_analysis": output.model_dump()}

    return timeline_analyst_node


def create_causal_reasoner_node(llm_client: BaseLLMClient):
    """Factory for Agent 5: Causal Reasoner node."""

    async def causal_reasoner_node(state: GraphState) -> dict[str, Any]:
        user_req = state.get("user_request", "")
        canon = state.get("canon_analysis", {})

        prompt = (
            f"User Request: {user_req}\n"
            f"Canon Facts:\n" + "\n".join(canon.get("active_canon_facts", [])) + "\n\n"
            "Identify causal prerequisites and project downstream implications."
        )

        output = await llm_client.generate_structured(
            prompt=prompt,
            response_model=CausalReasonerOutput,
            system_prompt=CAUSAL_REASONER_SYSTEM_PROMPT,
        )
        return {"causal_analysis": output.model_dump()}

    return causal_reasoner_node


def create_plot_architect_node(llm_client: BaseLLMClient):
    """Factory for Agent 6: Plot Architect node."""

    async def plot_architect_node(state: GraphState) -> dict[str, Any]:
        user_req = state.get("user_request", "")
        pos = state.get("narrative_position", 0.0)
        mode = state.get("generation_mode", "plot_point")
        canon = state.get("canon_analysis", {})
        character = state.get("character_analysis", {})
        timeline = state.get("timeline_analysis", {})
        causal = state.get("causal_analysis", {})
        revision_notes = state.get("revision_notes", [])

        revision_text = ""
        if revision_notes:
            revision_text = (
                "\nCRITICAL: A previous draft failed constraints. Fix the following violations:\n"
                + "\n".join(f"- {note}" for note in revision_notes)
                + "\n"
            )

        prompt = (
            f"User Request: {user_req}\n"
            f"Narrative Position: {pos}\n"
            f"Mode: {mode}\n"
            f"Canon Context: {json.dumps(canon)}\n"
            f"Character Context: {json.dumps(character)}\n"
            f"Timeline Context: {json.dumps(timeline)}\n"
            f"Causal Context: {json.dumps(causal)}\n"
            f"{revision_text}\n"
            "Synthesize a grounded narrative proposal adhering to all constraints."
        )

        output = await llm_client.generate_structured(
            prompt=prompt,
            response_model=PlotProposalOutput,
            system_prompt=PLOT_ARCHITECT_SYSTEM_PROMPT,
        )
        rev_count = state.get("revision_count", 0)
        return {
            "draft_proposal": output.model_dump(),
            "revision_count": rev_count + 1 if revision_notes else rev_count,
        }

    return plot_architect_node


def create_constraint_validator_node(engine: ConstraintEngine):
    """Factory for Agent 7: Constraint Validator node."""

    async def constraint_validator_node(state: GraphState) -> dict[str, Any]:
        story_state: StoryState | None = state.get("story_state")
        draft = state.get("draft_proposal", {})
        pos = state.get("narrative_position", 0.0)

        if not story_state:
            # If no story state present, treat as minimally passing
            return {
                "validation_report": {
                    "overall_outcome": "PASS",
                    "is_valid": True,
                    "has_hard_failures": False,
                    "summary": "No active story state to validate against.",
                    "diagnostics": [],
                }
            }

        # Build proposal dict for ConstraintEngine
        proposal_dict = {
            "title": draft.get("title", ""),
            "premise": draft.get("premise", ""),
            "narrative_position": pos,
            "involved_characters": draft.get("involved_characters", []),
            "preconditions": draft.get("preconditions", []),
            "causal_dependencies": draft.get("causal_dependencies", []),
            "supporting_evidence": draft.get("supporting_evidence", []),
            "assumptions": draft.get("assumptions", []),
            "detailed_content": draft.get("detailed_content", {}),
        }

        report = await engine.validate(proposal_dict, story_state)

        report_dict = {
            "overall_outcome": report.overall_outcome.value,
            "is_valid": report.is_valid,
            "has_hard_failures": report.has_hard_failures,
            "summary": report.summary,
            "passed_count": report.passed_count,
            "failed_count": report.failed_count,
            "warning_count": report.warning_count,
            "diagnostics": [
                {
                    "rule_id": d.rule_id,
                    "rule_name": d.rule_name,
                    "outcome": d.outcome.value,
                    "severity": d.severity.value,
                    "message": d.message,
                    "evidence": d.evidence,
                    "remediation_hint": d.remediation_hint,
                }
                for d in report.diagnostics
            ],
        }

        # If hard failure, formulate revision note
        new_revision_notes = list(state.get("revision_notes", []))
        if report.has_hard_failures:
            for diag in report.diagnostics:
                if diag.outcome.value == "FAIL":
                    hint = diag.remediation_hint or diag.message
                    new_revision_notes.append(f"[{diag.rule_name}] {hint}")

        return {
            "validation_report": report_dict,
            "revision_notes": new_revision_notes,
        }

    return constraint_validator_node


def create_narrative_critic_node(llm_client: BaseLLMClient):
    """Factory for Agent 8: Narrative Critic node."""

    async def narrative_critic_node(state: GraphState) -> dict[str, Any]:
        draft = state.get("draft_proposal", {})
        val_report = state.get("validation_report", {})

        prompt = (
            f"Draft Proposal:\n{json.dumps(draft, indent=2)}\n\n"
            f"Validation Summary: {val_report.get('summary', '')}\n\n"
            "Critique this suggestion for originality, plausibility, and narrative value."
        )

        output = await llm_client.generate_structured(
            prompt=prompt,
            response_model=NarrativeCriticOutput,
            system_prompt=NARRATIVE_CRITIC_SYSTEM_PROMPT,
        )
        return {"critic_evaluation": output.model_dump()}

    return narrative_critic_node


def create_result_synthesizer_node():
    """Factory for Result Synthesizer node compiling final suggestion payload."""

    async def result_synthesizer_node(state: GraphState) -> dict[str, Any]:
        draft = state.get("draft_proposal", {})
        val_report = state.get("validation_report", {})
        critic = state.get("critic_evaluation", {})
        mode = state.get("generation_mode", "plot_point")

        final_suggestion = {
            "suggestion_type": mode,
            "title": draft.get("title", "Untitled Narrative Suggestion"),
            "premise": draft.get("premise", ""),
            "detailed_content": {
                **draft.get("detailed_content", {}),
                "narrative_purpose": draft.get("narrative_purpose", ""),
                "involved_characters": draft.get("involved_characters", []),
                "preconditions": draft.get("preconditions", []),
                "causal_dependencies": draft.get("causal_dependencies", []),
                "expected_consequences": draft.get("expected_consequences", []),
                "critic_verdict": critic.get("overall_verdict", ""),
                "critic_scores": {
                    "originality": critic.get("originality_score", 8.0),
                    "plausibility": critic.get("narrative_plausibility_score", 8.0),
                    "thematic_relevance": critic.get("thematic_relevance_score", 8.0),
                },
            },
            "supporting_evidence": draft.get("supporting_evidence", []),
            "assumptions": draft.get("assumptions", []),
            "validation_results": val_report,
            "approval_status": "pending_author_approval",
        }

        return {"final_suggestion": final_suggestion}

    return result_synthesizer_node
