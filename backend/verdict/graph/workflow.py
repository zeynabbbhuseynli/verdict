from langgraph.graph import StateGraph, END
from verdict.graph.state import VerdictState
from verdict.graph.nodes import (
    run_investigator,
    run_challenger,
    run_judge,
    run_self_correction,
    run_finalize
)


def should_self_correct(state: VerdictState) -> str:
    rulings = state.get("judge_rulings", [])
    has_deferred = any(
        r.get("status") in ("DEFERRED", "REJECTED") and r.get("correction_required")
        for r in rulings
    )
    under_cap = state.get("current_iteration", 0) < state.get("max_iterations", 3)
    rate = state.get("admission_rate", 0.0)
    # Early exit if admission rate is already great
    if rate >= 0.90:
        return "finalize"
    return "correct" if (has_deferred and under_cap) else "finalize"


def check_iteration_cap(state: VerdictState) -> str:
    at_cap = state.get("current_iteration", 0) >= state.get("max_iterations", 3)
    return "finalize" if at_cap else "continue"


def build_graph() -> StateGraph:
    graph = StateGraph(VerdictState)

    graph.add_node("investigate", run_investigator)
    graph.add_node("challenge", run_challenger)
    graph.add_node("judge", run_judge)
    graph.add_node("self_correct", run_self_correction)
    graph.add_node("finalize", run_finalize)

    graph.set_entry_point("investigate")
    graph.add_edge("investigate", "challenge")
    graph.add_edge("challenge", "judge")

    graph.add_conditional_edges(
        "judge",
        should_self_correct,
        {"correct": "self_correct", "finalize": "finalize"}
    )

    graph.add_conditional_edges(
        "self_correct",
        check_iteration_cap,
        {"continue": "challenge", "finalize": "finalize"}
    )

    graph.add_edge("finalize", END)
    return graph.compile()


verdict_graph = build_graph()
