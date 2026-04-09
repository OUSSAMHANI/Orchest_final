"""
Conditional Routing Module
Handles routing decisions and state mutations for LangGraph orchestration.
Pure decision-making with minimal state updates.
"""

import logging
from typing import Literal, Dict, Any, Optional, cast
from datetime import datetime

from ..state.schema import OrchestratorState
from ..planning.planner import regenerate_plan


# =========================
# LOGGING SETUP
# =========================

logger = logging.getLogger(__name__)


# =========================
# CONFIG HELPERS
# =========================

def _get_config_value(state: OrchestratorState, key: str, default: Any) -> Any:
    """Get configuration value from state metadata."""
    return state.get("metadata", {}).get("config", {}).get("orchestrator", {}).get(key, default)


def _get_step_by_id(state: OrchestratorState, step_id: str) -> Optional[Dict[str, Any]]:
    """Get step by ID from plan."""
    plan = state.get("plan")
    if not plan or "steps" not in plan:
        return None
    
    for step in plan["steps"]:
        if step.get("id") == step_id:
            return step
    return None


def _is_critical_step(step: Dict[str, Any]) -> bool:
    """Check if step is critical."""
    return step.get("critical", True)


def _get_step_retry_count(state: OrchestratorState, step_id: str) -> int:
    """Get retry count for a step."""
    return state.get("retry_count", {}).get(step_id, 0)


def _is_last_step(state: OrchestratorState, current_step_id: str) -> bool:
    """Check if current step is the last step in the plan."""
    plan = state.get("plan")
    if not plan or "steps" not in plan:
        return False
    
    steps = plan["steps"]
    if not steps:
        return False
    
    return steps[-1].get("id") == current_step_id


# =========================
# ROUTING DECISION
# =========================

def route_after_execution(
    state: OrchestratorState
) -> Literal["continue", "retry", "skip", "regenerate", "complete"]:
    """
    Decide next action after a step execution.
    PURE FUNCTION → no state mutation allowed.
    """
    current_step_id = state.get("current_step")
    if not current_step_id:
        logger.debug("No current step, continuing")
        return "continue"
    
    result = state.get("results", {}).get(current_step_id)
    if not result:
        logger.debug(f"No result for step {current_step_id}, continuing")
        return "continue"
    
    step = _get_step_by_id(state, current_step_id)
    if not step:
        logger.warning(f"Step {current_step_id} not found in plan, continuing")
        return "continue"
    
    status = result.get("status")
    confidence = result.get("confidence", 0.0)
    
    retry_count = _get_step_retry_count(state, current_step_id)
    regeneration_count = state.get("regeneration_count", 0)
    
    is_critical = _is_critical_step(step)
    
    # Get config values
    confidence_threshold = _get_config_value(state, "confidence_threshold", 0.7)
    max_retries = _get_config_value(state, "max_retries", 2)
    max_regenerations = _get_config_value(state, "max_regenerations", 2)
    
    # Check if this is the last step
    is_last = _is_last_step(state, current_step_id)
    
    logger.debug(f"Step {current_step_id}: status={status}, confidence={confidence}, "
                 f"retry={retry_count}/{max_retries}, critical={is_critical}")
    
    # -----------------------------
    # SUCCESS CASES
    # -----------------------------
    if status == "success":
        if confidence >= confidence_threshold:
            logger.info(f"Step {current_step_id} succeeded with high confidence")
            if is_last:
                logger.info("Last step completed successfully, finishing")
                return "complete"
            return "continue"
        
        # Low confidence success
        if retry_count < max_retries:
            logger.info(f"Step {current_step_id} has low confidence, retrying ({retry_count + 1}/{max_retries})")
            return "retry"
        
        # Retries exhausted
        if is_critical:
            if regeneration_count < max_regenerations:
                logger.info(f"Critical step {current_step_id} low confidence, regenerating plan")
                return "regenerate"
            logger.warning(f"Critical step {current_step_id} low confidence, stopping")
            return "complete"
        else:
            logger.info(f"Non-critical step {current_step_id} low confidence, skipping")
            if is_last:
                return "complete"
            return "skip"
    
    # -----------------------------
    # FAILURE CASES
    # -----------------------------
    if status == "failed":
        if retry_count < max_retries:
            logger.info(f"Step {current_step_id} failed, retrying ({retry_count + 1}/{max_retries})")
            return "retry"
        
        if is_critical:
            if regeneration_count < max_regenerations:
                logger.info(f"Critical step {current_step_id} failed, regenerating plan")
                return "regenerate"
            logger.warning(f"Critical step {current_step_id} failed, stopping")
            return "complete"
        
        logger.info(f"Non-critical step {current_step_id} failed, skipping")
        if is_last:
            return "complete"
        return "skip"
    
    # -----------------------------
    # SKIPPED / UNKNOWN
    # -----------------------------
    if status == "skipped":
        logger.debug(f"Step {current_step_id} was skipped, continuing")
        if is_last:
            return "complete"
        return "continue"
    
    logger.warning(f"Unknown status {status} for step {current_step_id}, continuing")
    return "continue"


# =========================
# STATE MUTATION HANDLERS
# =========================

def handle_retry(state: OrchestratorState) -> OrchestratorState:
    """Prepare state for retrying current step."""
    step_id = state.get("current_step")
    if not step_id:
        return state
    
    # Increment retry count
    new_retry_count = dict(state.get("retry_count", {}))
    new_retry_count[step_id] = new_retry_count.get(step_id, 0) + 1
    
    # Find step index for current step
    plan = state.get("plan") or {}
    steps = plan.get("steps", [])
    current_step_index = 0
    for i, step in enumerate(steps):
        if step.get("id") == step_id:
            current_step_index = i
            break
    
    return cast(OrchestratorState, {
        **state,
        "retry_count": new_retry_count,
        "adaptation_reason": f"Retrying step {step_id}",
        "current_step_index": current_step_index,
    })


def handle_skip(state: OrchestratorState) -> OrchestratorState:
    """Mark step as skipped and move forward."""
    step_id = state.get("current_step")
    if not step_id:
        return state
    
    # Create new results with skipped step
    new_results = dict(state.get("results", {}))
    new_results[step_id] = {
        "status": "skipped",
        "output": None,
        "error": "Skipped due to repeated failure or low confidence",
        "confidence": 0.0,
        "completed_at": datetime.utcnow().isoformat(),
    }
    
    # Calculate next index
    next_index = state.get("current_step_index", 0) + 1
    
    return cast(OrchestratorState, {
        **state,
        "results": new_results,
        "adaptation_reason": f"Skipped step {step_id}",
        "current_step_index": next_index,
    })


def handle_regenerate(state: OrchestratorState) -> OrchestratorState:
    """Regenerate plan and reset execution."""
    step_id = state.get("current_step")
    
    # Get error context
    error_context = None
    if step_id:
        result = state.get("results", {}).get(step_id, {})
        error_context = result.get("error", "unknown error")
    
    # Ensure state has required fields
    if "errors" not in state:
        state = {**state, "errors": []}  # type: ignore
    
    # Increment regeneration count
    new_regeneration_count = state.get("regeneration_count", 0) + 1
    
    # Create state with updated regeneration count
    state_with_count = {
        **state,
        "regeneration_count": new_regeneration_count,
        "adaptation_reason": f"Regenerating plan due to: {error_context}",
    }
    
    try:
        # Call regenerate_plan (returns new state)
        new_state = regenerate_plan(cast(OrchestratorState, state_with_count), error_context)
        
        # Ensure new_state has required fields
        if "errors" not in new_state:
            new_state = {**new_state, "errors": []}
        
        # Reset execution pointer in the new state
        return cast(OrchestratorState, {
            **new_state,
            "current_step_index": 0,
            "current_step": None,
            "status": "executing",
        })
    except Exception as e:
        # If regeneration fails, return original state with error
        logger.error(f"Regeneration failed: {e}")
        errors = state.get("errors", [])
        errors.append({
            "step": "plan_regeneration",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        return cast(OrchestratorState, {
            **state,
            "errors": errors,
            "status": "failed",
            "adaptation_reason": f"Regeneration failed: {str(e)}"
        })


# =========================
# EXECUTION CONTROL
# =========================

def should_continue_execution(state: OrchestratorState) -> bool:
    """Check if orchestrator should keep running."""
    if state.get("status") != "executing":
        return False
    
    plan = state.get("plan")
    if not plan or not plan.get("steps"):
        return False
    
    return state.get("current_step_index", 0) < len(plan["steps"])


# =========================
# ANALYTICS
# =========================

def get_adaptation_summary(state: OrchestratorState) -> Dict[str, Any]:
    """Lightweight adaptation tracking."""
    results = state.get("results", {})
    history = state.get("metadata", {}).get("history", [])
    
    retries = sum(1 for r in results.values() if r.get("status") == "failed")
    skips = sum(1 for r in results.values() if r.get("status") == "skipped")
    regenerations = state.get("regeneration_count", 0)
    
    ticket = state.get("ticket", {})
    
    return {
        "issue_id": ticket.get("issue_id"),
        "intent": ticket.get("intent"),
        "scope": ticket.get("scope"),
        "workspace_path": state.get("workspace_path"),
        "retries": retries,
        "skips": skips,
        "regenerations": regenerations,
        "total_adaptations": retries + skips + regenerations,
        "history_size": len(history),
    }