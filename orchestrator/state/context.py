"""
Runtime State Manager for Orchestrator
Handles state lifecycle with thread safety and optional persistence.
"""

import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from copy import deepcopy

from .schema import OrchestratorState, create_initial_state


class StateContext:
    """
    Runtime state manager for a single ticket execution.
    Thread-safe with optional persistence and history.
    """
    
    def __init__(
        self,
        ticket: Dict[str, Any],
        state_id: Optional[str] = None,
        persistence_client: Optional[Any] = None,
        enable_history: bool = False,
    ):
        self._state: OrchestratorState = create_initial_state(ticket)
        self._state_id = state_id or self._generate_id()
        self._lock = threading.RLock()
        self._persistence = persistence_client
        self._history: List[Dict[str, Any]] = [] if enable_history else None
        
        if self._persistence:
            self._load()
    
    # =========================
    # PUBLIC METHODS
    # =========================
    
    def get(self, key: Optional[str] = None) -> Any:
        """Get full state or specific key."""
        with self._lock:
            if key is None:
                return deepcopy(self._state)
            return self._state.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Set a state value."""
        with self._lock:
            old_value = self._state.get(key)
            self._state[key] = value
            self._after_change(key, old_value, value)
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Batch update multiple keys."""
        with self._lock:
            for key, value in updates.items():
                old_value = self._state.get(key)
                self._state[key] = value
                self._after_change(key, old_value, value)
    
    def get_state_id(self) -> str:
        """Return unique state identifier."""
        return self._state_id
    
    def get_current_step(self) -> Optional[str]:
        """Convenience method."""
        return self._state.get("current_step")
    
    def set_current_step(self, step_id: str) -> None:
        """Convenience method."""
        self.set("current_step", step_id)
        self.set("current_step_index", self._state.get("current_step_index", 0) + 1)
    
    def add_result(self, step_id: str, result: Dict[str, Any]) -> None:
        """Add result for a completed step."""
        with self._lock:
            if "results" not in self._state:
                self._state["results"] = {}
            self._state["results"][step_id] = {
                **result,
                "completed_at": datetime.utcnow().isoformat(),
            }
    
    def add_error(self, step_id: str, error: Dict[str, Any]) -> None:
        """Add error for a failed step."""
        with self._lock:
            if "errors" not in self._state:
                self._state["errors"] = []
            self._state["errors"].append({
                "step_id": step_id,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            })
    
    def increment_retry(self, step_id: str) -> int:
        """Increment retry count for a step."""
        with self._lock:
            if "retry_count" not in self._state:
                self._state["retry_count"] = {}
            current = self._state["retry_count"].get(step_id, 0)
            self._state["retry_count"][step_id] = current + 1
            return current + 1
    
    def persist(self) -> None:
        """Save state to external store."""
        if self._persistence:
            import json
            self._persistence.set(
                f"state:{self._state_id}",
                json.dumps(self._state, default=str),
            )
    
    def get_history(self) -> Optional[List[Dict[str, Any]]]:
        """Return state change history if enabled."""
        return self._history
    
    def snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of current state."""
        with self._lock:
            return {
                "state_id": self._state_id,
                "state": deepcopy(self._state),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    # =========================
    # PRIVATE METHODS
    # =========================
    
    def _generate_id(self) -> str:
        return f"state_{uuid.uuid4().hex[:16]}"
    
    def _after_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Handle post-change operations."""
        if self._history is not None:
            self._history.append({
                "key": key,
                "old_value": old_value,
                "new_value": new_value,
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        if self._persistence:
            self.persist()
    
    def _load(self) -> None:
        """Load state from persistence."""
        if self._persistence:
            import json
            data = self._persistence.get(f"state:{self._state_id}")
            if data:
                self._state = json.loads(data)


# =========================
# CONTEXT MANAGER (Optional)
# =========================

class StateContextManager:
    """Manages multiple state contexts for concurrent tickets."""
    
    def __init__(self, persistence_client: Optional[Any] = None):
        self._contexts: Dict[str, StateContext] = {}
        self._lock = threading.RLock()
        self._persistence = persistence_client
    
    def create(self, ticket: Dict[str, Any], state_id: Optional[str] = None) -> StateContext:
        with self._lock:
            context = StateContext(
                ticket=ticket,
                state_id=state_id,
                persistence_client=self._persistence,
            )
            self._contexts[context.get_state_id()] = context
            return context
    
    def get(self, state_id: str) -> Optional[StateContext]:
        with self._lock:
            return self._contexts.get(state_id)
    
    def delete(self, state_id: str) -> None:
        with self._lock:
            if state_id in self._contexts:
                del self._contexts[state_id]
    
    def list_active(self) -> List[str]:
        with self._lock:
            return list(self._contexts.keys())