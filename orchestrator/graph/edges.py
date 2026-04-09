"""
Graph Edges
Conditional edge logic for LangGraph routing.
"""

import logging
from typing import Literal

from ..state.schema import OrchestratorState
from ..routing.conditional import route_after_execution
from ..planning.plan_validator import has_circular_dependencies


logger = logging.getLogger(__name__)


# =========================
# CONDITIONAL EDGE LOGIC
# =========================

def route_decision(
    state: OrchestratorState
) -> Literal["continue", "retry", "skip", "regenerate", "complete"]:
    """
    Central routing decision after each execution.
    
    Returns:
        Next action: continue, retry, skip, regenerate, or complete
    """
    # Check if no plan exists
    if not state.get("plan"):
        logger.info("No plan, completing")
        return "complete"
    
    # Check for circular dependencies in plan
    plan = state.get("plan", {})
    if has_circular_dependencies(plan):
        logger.warning("Plan has circular dependencies, completing")
        return "complete"
    
    # Check if execution is blocked
    if _is_execution_blocked(state):
        logger.info("Execution blocked, completing")
        return "complete"
    
    # Max regenerations check
    MAX_REGENERATIONS = 3
    if state.get("regeneration_count", 0) >= MAX_REGENERATIONS:
        logger.warning(f"Max regenerations ({MAX_REGENERATIONS}) reached, stopping")
        return "complete"
    
    # Get routing decision from conditional module
    decision = route_after_execution(state)
    
    # Safety check
    if decision not in ["continue", "retry", "skip", "regenerate", "complete"]:
        logger.warning(f"Invalid decision: {decision}, terminating")
        return "complete"
    
    logger.debug(f"Routing decision: {decision}")
    return decision


# =========================
# HELPER FUNCTIONS
# =========================

def _is_execution_blocked(state: OrchestratorState) -> bool:
    """
    Check if execution is blocked (deadlock detection).
    """
    plan = state.get("plan")
    if not plan or "steps" not in plan:
        return False
    
    results = state.get("results", {})
    steps = plan["steps"]
    
    has_pending = False
    all_blocked = True
    
    for step in steps:
        step_id = step.get("id")
        result = results.get(step_id)
        
        # Skip already successful steps
        if result and result.get("status") == "success":
            continue
        
        has_pending = True
        
        # Check if dependencies are met
        depends_on = step.get("depends_on", [])
        deps_met = True
        
        for dep_id in depends_on:
            dep_result = results.get(dep_id)
            if not dep_result or dep_result.get("status") != "success":
                deps_met = False
                break
        
        if deps_met:
            all_blocked = False
    
    return has_pending and all_blocked


def should_continue_execution(state: OrchestratorState) -> bool:
    """
    Check if orchestrator should keep running.
    """
    if state.get("status") != "executing":
        return False
    
    plan = state.get("plan")
    if not plan or not plan.get("steps"):
        return False
    
    current_index = state.get("current_step_index", 0)
    total_steps = len(plan["steps"])
    
    return current_index < total_steps