"""
Step Executor
Executes a single plan step by calling the appropriate agent.
Handles retries, error management, and state updates.
"""

import logging
from typing import Dict, Any, Optional, cast
from datetime import datetime

from ..state.schema import OrchestratorState
from .agent_client import get_agent_client
from .retry_handler import get_retry_handler


# =========================
# LOGGING SETUP
# =========================

logger = logging.getLogger(__name__)


# =========================
# STEP EXECUTOR
# =========================

class StepExecutor:
    """
    Executes a single step from the plan.
    Responsible for calling the agent, handling retries, and updating state.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize step executor with configuration.
        
        Args:
            config: Configuration dictionary with agent and retry settings
        """
        self.config = config or {}
        self.agent_client = get_agent_client(self.config.get("agents"))
        self.retry_handler = get_retry_handler(self.config.get("retry", {}))
    
    def execute_step(self, state: OrchestratorState) -> OrchestratorState:
        """
        Execute the current step from the plan.
        
        Args:
            state: Current orchestrator state
        
        Returns:
            Updated state with step result or error
        """
        # Get next step to execute
        step = self._get_next_step(state)
        
        if step is None:
            logger.info("No step to execute")
            return state
        
        step_id = step.get("id")
        agent_name = step.get("agent")
        is_critical = step.get("critical", True)
        
        logger.info(f"Executing step: {step_id} -> agent: {agent_name}")
        
        # Check dependencies
        if not self._are_dependencies_met(state, step):
            error_msg = f"Dependencies not met: {step.get('depends_on', [])}"
            logger.warning(f"Step {step_id}: {error_msg}")
            return self._handle_error(state, step_id, agent_name, error_msg, is_critical)
        
        # Prepare context for agent
        context = self._prepare_context(state, step)
        
        # Get current retry count
        current_retry = state.get("retry_count", {}).get(step_id, 0)
        
        try:
            # Execute with retry logic
            result, attempts = self.retry_handler.execute_with_retry(
                step_id=step_id,
                func=lambda: self._call_agent(step_id, agent_name, context),
                get_current_retry_count=lambda _: current_retry,
                increment_retry=lambda step_id: self._increment_retry_count(state, step_id),
                on_retry=lambda step_id, attempt, delay: logger.info(
                    f"Step {step_id} retry {attempt} in {delay:.2f}s"
                ),
            )
            
            # Step succeeded
            logger.info(f"Step {step_id} completed successfully after {attempts} attempt(s)")
            return self._handle_success(state, step_id, result)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Step {step_id} failed permanently: {error_msg}")
            
            # Check if this failure should stop the workflow
            if self.retry_handler.is_critical_failure(step_id, error_msg, current_retry, is_critical):
                return self._handle_fatal_error(state, step_id, agent_name, error_msg)
            else:
                return self._handle_error(state, step_id, agent_name, error_msg, is_critical)
    
    def _get_next_step(self, state: OrchestratorState) -> Optional[Dict[str, Any]]:
        """
        Get the next executable step from the plan.
        Respects dependencies and already completed steps.
        """
        plan = state.get("plan")
        if not plan or "steps" not in plan:
            return None
        
        results = state.get("results", {})
        
        for step in plan["steps"]:
            step_id = step.get("id")
            
            # Skip already successful steps
            if results.get(step_id, {}).get("status") == "success":
                continue
            
            # Check dependencies
            if self._are_dependencies_met(state, step):
                return step
        
        return None
    
    def _are_dependencies_met(self, state: OrchestratorState, step: Dict[str, Any]) -> bool:
        """
        Check if all dependencies for a step are met.
        """
        depends_on = step.get("depends_on", [])
        if not depends_on:
            return True
        
        results = state.get("results", {})
        
        for dep_id in depends_on:
            dep_result = results.get(dep_id)
            if not dep_result or dep_result.get("status") != "success":
                logger.debug(f"Dependency not met: {dep_id} for step {step.get('id')}")
                return False
        
        return True
    
    def _call_agent(self, step_id: str, agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the agent via HTTP client.
        """
        return self.agent_client.call_agent(agent_name, step_id, context)
    
    def _prepare_context(self, state: OrchestratorState, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare context for agent execution.
        Includes ticket, workspace, previous outputs, and step details.
        """
        ticket = state.get("ticket", {})
        results = state.get("results", {})
        
        # Collect outputs from previous successful steps
        previous_outputs = {}
        for step_id, result in results.items():
            if result.get("status") == "success" and "output" in result:
                previous_outputs[step_id] = result["output"]
        
        # Build ticket summary
        ticket_summary = {
            "title": ticket.get("title", ""),
            "intent": ticket.get("intent", ""),
            "scope": ticket.get("scope", ""),
            "summary": ticket.get("summary", ""),
            "description": ticket.get("description", ""),
            "acceptance_criteria": ticket.get("acceptance_criteria", []),
            "constraints": ticket.get("constraints"),
            "non_goals": ticket.get("non_goals"),
            "priority": ticket.get("priority", "normal"),
            "issue_id": ticket.get("issue_id"),
            "gitlab_url": ticket.get("url"),
            "author": ticket.get("author"),
            "branch": ticket.get("branch"),
            "labels": ticket.get("labels", []),
            "workspace_path": state.get("workspace_path"),
        }
        
        return {
            # Workspace
            "workspace_path": state.get("workspace_path"),
            "agent_type": step.get("agent"),
            
            # Ticket data
            "ticket": ticket,
            "ticket_summary": ticket_summary,
            
            # Convenience fields
            "intent": ticket.get("intent"),
            "scope": ticket.get("scope"),
            "description": ticket.get("description"),
            "acceptance_criteria": ticket.get("acceptance_criteria", []),
            
            # Execution context
            "previous_outputs": previous_outputs,
            "step_id": step.get("id"),
            "step_description": step.get("description", ""),
            "plan": state.get("plan"),
            "metadata": state.get("metadata", {}),
        }
    
    def _handle_success(
        self, 
        state: OrchestratorState, 
        step_id: str, 
        result: Dict[str, Any]
    ) -> OrchestratorState:
        """
        Handle successful step execution.
        """
        new_results = dict(state.get("results", {}))
        new_results[step_id] = {
            **result,
            "status": "success",
            "completed_at": datetime.utcnow().isoformat(),
        }
        
        new_state = {
            **state,
            "results": new_results,
            "current_step": step_id,
            "current_step_index": state.get("current_step_index", 0) + 1,
        }
        
        return cast(OrchestratorState, new_state)
    
    def _handle_error(
        self,
        state: OrchestratorState,
        step_id: str,
        agent_name: str,
        error: str,
        is_critical: bool = True,
    ) -> OrchestratorState:
        """
        Handle non-fatal step error.
        Marks step as failed but workflow may continue.
        """
        new_results = dict(state.get("results", {}))
        new_results[step_id] = {
            "status": "failed",
            "error": error,
            "agent": agent_name,
            "completed_at": datetime.utcnow().isoformat(),
        }
        
        new_errors = list(state.get("errors", []))
        new_errors.append({
            "step": step_id,
            "agent": agent_name,
            "error": error,
            "is_critical": is_critical,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        new_state = {
            **state,
            "results": new_results,
            "errors": new_errors,
            "current_step": step_id,
        }
        
        # If not critical, increment step index to move on
        if not is_critical:
            new_state["current_step_index"] = state.get("current_step_index", 0) + 1
        
        return cast(OrchestratorState, new_state)
    
    def _handle_fatal_error(
        self,
        state: OrchestratorState,
        step_id: str,
        agent_name: str,
        error: str,
    ) -> OrchestratorState:
        """
        Handle fatal error that should stop the workflow.
        """
        new_state = self._handle_error(state, step_id, agent_name, error, is_critical=True)
        new_state["status"] = "failed"
        new_state["adaptation_reason"] = f"Critical step '{step_id}' failed permanently"
        
        return cast(OrchestratorState, new_state)
    
    def _increment_retry_count(self, state: OrchestratorState, step_id: str) -> int:
        """
        Increment retry count for a step.
        """
        retry_count = dict(state.get("retry_count", {}))
        new_count = retry_count.get(step_id, 0) + 1
        retry_count[step_id] = new_count
        
        # This is called during retry, but we can't modify state directly here
        # The actual increment will happen in the main execute_step flow
        return new_count


# =========================
# SINGLETON INSTANCE
# =========================

_default_executor: Optional[StepExecutor] = None


def get_step_executor(config: Optional[Dict[str, Any]] = None) -> StepExecutor:
    """
    Get singleton step executor instance.
    """
    global _default_executor
    if _default_executor is None or config is not None:
        _default_executor = StepExecutor(config)
    return _default_executor


# =========================
# CONVENIENCE FUNCTION
# =========================

def execute_step(state: OrchestratorState) -> OrchestratorState:
    """
    Convenience function to execute a step.
    Compatible with LangGraph node signature.
    """
    executor = get_step_executor()
    return executor.execute_step(state)