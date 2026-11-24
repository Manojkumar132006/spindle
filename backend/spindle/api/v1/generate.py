"""Narrative generation endpoints driving the LangGraph multi-agent workflow."""

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from spindle.agents.graph import build_narrative_graph
from spindle.agents.state import GraphState
from spindle.api.deps import get_current_project
from spindle.core.constraints.engine import ConstraintEngine
from spindle.core.state_service import NarrativeStateService
from spindle.database import get_db_session
from spindle.llm.providers import get_llm_client
from spindle.models.base import ApprovalStatus, SuggestionType
from spindle.models.project import Project
from spindle.models.suggestion import Suggestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["Generation"])


class GeneratePlotPointRequest(BaseModel):
    """Payload for generating a canon-grounded plot point."""

    request: str = Field(description="Author prompt or goal for the plot development")
    narrative_position: float = Field(default=0.0, description="Target scene or chapter position")
    branch_id: uuid.UUID | None = Field(default=None, description="Optional narrative branch ID")


class GenerateSideStoryRequest(BaseModel):
    """Payload for generating a canon-consistent side story."""

    request: str = Field(description="Author prompt or concept for the side story")
    narrative_position: float = Field(default=0.0, description="Target story placement")
    branch_id: uuid.UUID | None = Field(default=None, description="Optional narrative branch ID")
    characters: list[str] = Field(default_factory=list, description="Target characters to feature")


class GenerateContinuityRequest(BaseModel):
    """Payload for requesting continuity analysis."""

    request: str = Field(description="Continuity query or proposed scene development")
    narrative_position: float = Field(default=0.0, description="Target story placement")
    branch_id: uuid.UUID | None = Field(default=None, description="Optional narrative branch ID")


class SuggestionResponse(BaseModel):
    """Detailed response containing a generated suggestion and its validation report."""

    id: uuid.UUID
    project_id: uuid.UUID
    suggestion_type: str
    title: str
    premise: str
    detailed_content: dict[str, Any]
    supporting_evidence: list[str]
    assumptions: list[str]
    validation_results: dict[str, Any]
    approval_status: str
    branch_id: uuid.UUID | None = None


async def _execute_generation(
    project: Project,
    session: AsyncSession,
    user_request: str,
    narrative_position: float,
    mode: str,
    branch_id: uuid.UUID | None = None,
) -> SuggestionResponse:
    """Core helper orchestrating narrative state retrieval, LangGraph execution, and persistence."""
    # 1. Fetch point-in-time story state snapshot
    state_service = NarrativeStateService(session)
    story_state = await state_service.get_story_state(
        project_id=project.id,
        narrative_position=narrative_position,
        branch_id=branch_id,
    )

    # 2. Build and execute LangGraph workflow
    llm_client = get_llm_client()
    constraint_engine = ConstraintEngine()
    graph = build_narrative_graph(llm_client=llm_client, constraint_engine=constraint_engine)

    initial_state: GraphState = {
        "project_id": str(project.id),
        "narrative_position": narrative_position,
        "branch_id": str(branch_id) if branch_id else None,
        "user_request": user_request,
        "generation_mode": mode,
        "story_state": story_state,
        "revision_count": 0,
        "revision_notes": [],
    }

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("Narrative generation graph execution failed: %s", e, exc_info=True)
        err_detail = f"{type(e).__name__}: {str(e)}" if str(e) else type(e).__name__
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Narrative generation engine error: {err_detail}",
        ) from e

    suggestion_data = final_state.get("final_suggestion", {})

    # 3. Persist the generated Suggestion into database
    suggestion = Suggestion(
        project_id=project.id,
        branch_id=branch_id,
        suggestion_type=suggestion_data.get("suggestion_type", mode),
        title=suggestion_data.get("title", "Untitled Suggestion"),
        premise=suggestion_data.get("premise", ""),
        detailed_content=suggestion_data.get("detailed_content", {}),
        supporting_evidence=suggestion_data.get("supporting_evidence", []),
        assumptions=suggestion_data.get("assumptions", []),
        validation_results=suggestion_data.get("validation_results", {}),
        approval_status=ApprovalStatus.PENDING_AUTHOR_APPROVAL.value,
    )
    session.add(suggestion)
    await session.commit()
    await session.refresh(suggestion)

    return SuggestionResponse(
        id=suggestion.id,
        project_id=suggestion.project_id,
        suggestion_type=suggestion.suggestion_type,
        title=suggestion.title,
        premise=suggestion.premise,
        detailed_content=suggestion.detailed_content,
        supporting_evidence=suggestion.supporting_evidence,
        assumptions=suggestion.assumptions,
        validation_results=suggestion.validation_results,
        approval_status=suggestion.approval_status,
        branch_id=suggestion.branch_id,
    )


@router.post(
    "/plot-point",
    response_model=SuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a canon-grounded plot point",
)
async def generate_plot_point(
    payload: GeneratePlotPointRequest,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SuggestionResponse:
    """Execute LangGraph multi-agent workflow to generate a validated plot point."""
    return await _execute_generation(
        project=project,
        session=session,
        user_request=payload.request,
        narrative_position=payload.narrative_position,
        mode=SuggestionType.PLOT_POINT.value,
        branch_id=payload.branch_id,
    )


@router.post(
    "/side-story",
    response_model=SuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a canon-consistent side story",
)
async def generate_side_story(
    payload: GenerateSideStoryRequest,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SuggestionResponse:
    """Execute LangGraph multi-agent workflow to generate a validated side story."""
    prompt = payload.request
    if payload.characters:
        prompt += f" Featuring characters: {', '.join(payload.characters)}."

    return await _execute_generation(
        project=project,
        session=session,
        user_request=prompt,
        narrative_position=payload.narrative_position,
        mode=SuggestionType.SIDE_STORY.value,
        branch_id=payload.branch_id,
    )


@router.post(
    "/continuity-analysis",
    response_model=SuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze story context for potential continuity contradictions",
)
async def generate_continuity_analysis(
    payload: GenerateContinuityRequest,
    project: Annotated[Project, Depends(get_current_project)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SuggestionResponse:
    """Evaluate proposed scenes or premises against established story continuity."""
    return await _execute_generation(
        project=project,
        session=session,
        user_request=payload.request,
        narrative_position=payload.narrative_position,
        mode=SuggestionType.CONTINUITY_ANALYSIS.value,
        branch_id=payload.branch_id,
    )
