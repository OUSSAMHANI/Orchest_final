"""
Graph Builder
Constructs the LangGraph workflow for orchestration.
"""

import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

from ..state.schema import OrchestratorState, create_initial_state
from ..planning.planner import generate_plan
from ..execution.step_executor import execute_step
from ..routing.conditional import (
    route_after_execution,
    handle_retry,
    handle_skip,
    handle_regenerate,
    should_continue_execution,
)

from .nodes import plan_node, execute_node, retry_node, skip_node, regenerate_node, route_node
from .edges import route_decision


logger = logging.getLogger(__name__)


# =========================
# GRAPH CREATION
# =========================

def create_orchestrator_graph() -> StateGraph:
    """
    Create and compile the LangGraph workflow.
    
    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(OrchestratorState)
    
    # Add nodes
    workflow.add_node("planner", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("route", route_node)
    workflow.add_node("retry", retry_node)
    workflow.add_node("skip", skip_node)
    workflow.add_node("regenerate", regenerate_node)
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    # Add edges
    workflow.add_edge("planner", "execute")
    workflow.add_edge("execute", "route")
    
    # Add conditional edges from route
    workflow.add_conditional_edges(
        "route",
        route_decision,
        {
            "continue": "execute",
            "retry": "retry",
            "skip": "skip",
            "regenerate": "regenerate",
            "complete": END,
        },
    )
    
    # Add edges from handler nodes
    workflow.add_edge("retry", "execute")
    workflow.add_edge("skip", "execute")
    workflow.add_edge("regenerate", "planner")
    
    return workflow.compile()


# =========================
# RUN FUNCTIONS
# =========================

def run_orchestrator(ticket: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run orchestrator with Kafka ticket.
    
    Args:
        ticket: Full Kafka ticket dictionary
    
    Returns:
        Final state as dictionary
    """
    from ..state.context import StateContext
    
    context = StateContext(ticket)
    initial_state = context.get()
    graph = create_orchestrator_graph()
    
    try:
        final_state = graph.invoke(initial_state, {"recursion_limit": 100})
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        return {
            "ticket": ticket,
            "workspace_path": ticket.get("workspace_path"),
            "status": "failed",
            "final_output": {"error": str(e), "error_type": type(e).__name__},
            "results": {},
            "errors": [{"step": "graph_execution", "error": str(e)}],
            "plan": None,
            "current_step": None,
            "current_step_index": 0,
            "retry_count": {},
            "regeneration_count": 0,
            "adaptation_reason": f"Graph execution failed: {str(e)}"
        }
    
    return _finalize_state(final_state)


def run_orchestrator_with_config(
    ticket: Dict[str, Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run orchestrator with custom configuration.
    
    Args:
        ticket: Full Kafka ticket dictionary
        config: Configuration dictionary
    
    Returns:
        Final state as dictionary
    """
    from ..state.context import StateContext
    
    context = StateContext(ticket)
    initial_state = context.get_state()
    initial_state["metadata"] = {"config": config}
    
    graph = create_orchestrator_graph()
    
    try:
        final_state = graph.invoke(initial_state, {"recursion_limit": 100})
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        return {
            "ticket": ticket,
            "workspace_path": ticket.get("workspace_path"),
            "status": "failed",
            "final_output": {"error": str(e)},
            "results": {},
            "errors": [{"step": "graph_execution", "error": str(e)}],
            "plan": None,
            "current_step": None,
            "current_step_index": 0,
            "retry_count": {},
            "regeneration_count": 0,
            "adaptation_reason": f"Graph execution failed: {str(e)}"
        }
    
    return _finalize_state(final_state)


def _finalize_state(state: OrchestratorState) -> Dict[str, Any]:
    """Ensure final state is consistent."""
    final_state = dict(state)
    
    if not final_state.get("final_output"):
        final_state["final_output"] = {
            "results": final_state.get("results", {}),
            "status": final_state.get("status"),
            "workspace_path": final_state.get("workspace_path"),
        }
    
    if final_state.get("status") not in {"completed", "failed"}:
        final_state["status"] = "completed"
    
    return final_state