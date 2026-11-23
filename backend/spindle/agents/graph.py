"""LangGraph multi-agent workflow compilation, conditional routing, and bounded revisions."""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from spindle.agents.nodes import (
    create_canon_analyst_node,
    create_causal_reasoner_node,
    create_character_analyst_node,
    create_constraint_validator_node,
    create_director_node,
    create_narrative_critic_node,
    create_plot_architect_node,
    create_result_synthesizer_node,
    create_timeline_analyst_node,
)
from spindle.agents.state import GraphState
from spindle.core.constraints.engine import ConstraintEngine
from spindle.llm.client import BaseLLMClient
from spindle.llm.providers import get_llm_client


def should_revise_proposal(state: GraphState) -> str:
    """Conditional router: route to revision loop if hard constraints fail and bound not exceeded."""
    report = state.get("validation_report", {})
    revision_count = state.get("revision_count", 0)
    has_hard_failures = report.get("has_hard_failures", False)

    # Allow up to 2 revision iterations
    if has_hard_failures and revision_count < 2:
        return "plot_architect"
    return "narrative_critic"


def build_narrative_graph(
    llm_client: BaseLLMClient | None = None,
    constraint_engine: ConstraintEngine | None = None,
) -> CompiledStateGraph:
    """Construct and compile the 8-agent LangGraph narrative intelligence workflow."""
    client = llm_client or get_llm_client()
    engine = constraint_engine or ConstraintEngine()

    workflow = StateGraph(GraphState)

    # 1. Register Nodes
    workflow.add_node("director", create_director_node(client))
    workflow.add_node("canon_analyst", create_canon_analyst_node(client))
    workflow.add_node("character_analyst", create_character_analyst_node(client))
    workflow.add_node("timeline_analyst", create_timeline_analyst_node(client))
    workflow.add_node("causal_reasoner", create_causal_reasoner_node(client))
    workflow.add_node("plot_architect", create_plot_architect_node(client))
    workflow.add_node("constraint_validator", create_constraint_validator_node(engine))
    workflow.add_node("narrative_critic", create_narrative_critic_node(client))
    workflow.add_node("result_synthesizer", create_result_synthesizer_node())

    # 2. Sequential & Parallel Edges
    workflow.add_edge(START, "director")
    workflow.add_edge("director", "canon_analyst")

    # Parallel fan-out
    workflow.add_edge("canon_analyst", "character_analyst")
    workflow.add_edge("canon_analyst", "timeline_analyst")
    workflow.add_edge("canon_analyst", "causal_reasoner")

    # Fan-in to Plot Architect
    workflow.add_edge("character_analyst", "plot_architect")
    workflow.add_edge("timeline_analyst", "plot_architect")
    workflow.add_edge("causal_reasoner", "plot_architect")

    # Validation
    workflow.add_edge("plot_architect", "constraint_validator")

    # Conditional Routing (Bounded Revision Loop)
    workflow.add_conditional_edges(
        "constraint_validator",
        should_revise_proposal,
        {
            "plot_architect": "plot_architect",
            "narrative_critic": "narrative_critic",
        },
    )

    workflow.add_edge("narrative_critic", "result_synthesizer")
    workflow.add_edge("result_synthesizer", END)

    return workflow.compile()
