"""Deterministic MockLLM implementation for repeatable automated test execution."""

from collections import deque
from typing import Any, TypeVar

from pydantic import BaseModel

from spindle.llm.client import BaseLLMClient

T = TypeVar("T", bound=BaseModel)


class MockLLMClient(BaseLLMClient):
    """Deterministic Mock LLM returning rule-based structured completions."""

    def __init__(self, canned_responses: list[Any] | None = None) -> None:
        self.call_history: list[dict[str, Any]] = []
        self._canned_responses: deque[Any] = deque(canned_responses or [])

    def enqueue_response(self, response: Any) -> None:
        """Queue a specific response for upcoming completions."""
        self._canned_responses.append(response)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        self.call_history.append(
            {
                "type": "text",
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
            }
        )
        if self._canned_responses:
            res = self._canned_responses.popleft()
            if isinstance(res, str):
                return res
            return str(res)

        return "Mock LLM text completion based on story context."

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> T:
        self.call_history.append(
            {
                "type": "structured",
                "model": response_model.__name__,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
            }
        )

        if self._canned_responses:
            canned = self._canned_responses.popleft()
            if isinstance(canned, response_model):
                return canned
            if isinstance(canned, dict):
                return response_model.model_validate(canned)

        # Dynamic heuristic generation based on target Pydantic schema
        model_name = response_model.__name__.lower()

        # 1. Director output
        if "director" in model_name:
            data = {
                "generation_mode": (
                    "side_story"
                    if "side" in prompt.lower()
                    else "continuity_analysis"
                    if "continuity" in prompt.lower()
                    else "plot_point"
                ),
                "scope_summary": "Investigating character decisions and narrative arc progression.",
                "required_analyses": ["canon", "character", "timeline", "causal"],
                "target_characters": ["Elena Vareth"],
                "target_events": [],
            }
            return response_model.model_validate(data)

        # 2. Canon Analyst output
        if "canon" in model_name:
            data = {
                "established_precedents": [
                    "The Binding Oath took effect in Year 412.",
                    "The oath passes unconditionally to descendants until the Regency falls.",
                ],
                "unresolved_threads": ["Breaking the Binding Oath"],
                "active_canon_facts": ["Elena works as a scribe in the archive."],
                "contradiction_risks": ["Oath cannot be broken while the Regency stands."],
            }
            return response_model.model_validate(data)

        # 3. Character Analyst output
        if "character" in model_name:
            data = {
                "motivation_alignment": "Aligns with Elena's wound and desire to protect her brother.",
                "behavioral_plausibility_score": 9.0,
                "relationship_dynamics": [
                    "Tense distrust towards Chancellor Aldric Voss due to oath enforcement."
                ],
                "knowledge_boundaries": ["Elena knows the loophole exists; other scribes do not."],
                "potential_character_growth": (
                    "Moving from quiet compliance to active subversion."
                ),
            }
            return response_model.model_validate(data)

        # 4. Timeline Analyst output
        if "timeline" in model_name:
            data = {
                "chronological_placement": "Year 424 of the Regency",
                "temporal_ordering_valid": True,
                "character_presence_confirmed": True,
                "dependencies_satisfied": True,
                "timeline_notes": "Occurs after Chapter 7 archival discovery.",
            }
            return response_model.model_validate(data)

        # 5. Causal Reasoner output
        if "causal" in model_name:
            data = {
                "prerequisites": ["Access to the council archive", "Discovery of the loophole"],
                "immediate_consequences": ["Creates suspicion from the archivist"],
                "downstream_implications": ["Could trigger premature confrontation if leaked"],
                "causal_plausibility_score": 8.8,
            }
            return response_model.model_validate(data)

        # 6. Plot Architect output
        if "plot" in model_name or "proposal" in model_name or "architect" in model_name:
            data = {
                "title": "A Ledger Across the River",
                "premise": (
                    "Elena discreetly copies the loophole clause onto parchment scraps "
                    "to smuggle to the outer quarter."
                ),
                "narrative_purpose": "Advance the conspiracy while introducing tangible risk.",
                "involved_characters": ["Elena Vareth"],
                "preconditions": ["Elena has access to ink and paper during evening duty."],
                "causal_dependencies": ["Discovery of the Loophole"],
                "expected_consequences": ["Archivist notices missing parchment sheets."],
                "supporting_evidence": [
                    "Examples/The Loophole.md",
                    "Characters/Elena Vareth.md",
                ],
                "assumptions": ["The toll guards do not inspect scribe satchels closely."],
                "detailed_content": {
                    "act": 2,
                    "scene_beats": [
                        "Elena prepares the transcription while archive guards change shifts.",
                        "She conceals the leaf beneath ordinary commercial tax records.",
                        "She exits through the south toll gate under Aldric's banner.",
                    ],
                },
            }
            return response_model.model_validate(data)

        # 7. Narrative Critic output
        if "critic" in model_name:
            data = {
                "originality_score": 8.5,
                "narrative_plausibility_score": 9.2,
                "thematic_relevance_score": 9.0,
                "identified_weaknesses": [
                    "Risk of being caught by toll guards could be emphasized."
                ],
                "overall_verdict": (
                    "Strong contextual alignment with canon; meaningfully builds narrative tension."
                ),
            }
            return response_model.model_validate(data)

        # Fallback empty construction
        return response_model.model_construct()
