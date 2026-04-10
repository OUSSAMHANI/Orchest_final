"""
State Model for LangGraph Orchestrator
Defines the state schema ONLY — no execution logic.
"""

from typing import TypedDict, Optional, Dict, Any, List, cast


# =========================
# STATE SCHEMA
# =========================

class OrchestratorState(TypedDict):
    """
    Blueprint of the state that flows through LangGraph.
    """
    
    # Input
    ticket: Dict[str, Any]              # Full Kafka ticket
    workspace_path: Optional[str]       # Pre-cloned workspace path
    
    # Execution plan
    plan: Optional[Dict[str, Any]]
    
    # Current execution state
    current_step: Optional[str]
    current_step_index: int
    
    # Results and history
    results: Dict[str, Any]
    errors: List[Dict[str, Any]]
    
    # Retry tracking
    retry_count: Dict[str, int]
    
    # Regeneration tracking
    regeneration_count: int
    
    # Final output
    final_output: Optional[Dict[str, Any]]
    
    # Status tracking
    status: str  # "planning", "executing", "completed", "failed"
    
    # Adaptation context
    adaptation_reason: Optional[str]
    
    # Metadata
    metadata: Dict[str, Any]


# =========================
# INITIAL STATE
# =========================

def create_initial_state(ticket: Dict[str, Any]) -> OrchestratorState:
    """
    Create initial state from Kafka ticket JSON.
    """
    if not isinstance(ticket, dict):
        raise TypeError(f"ticket must be dict, got {type(ticket)}")
    
    state: OrchestratorState = {
        # Input
        "ticket": ticket,
        "workspace_path": ticket.get("workspace_path"),
        
        # Plan
        "plan": None,
        
        # Execution
        "current_step": None,
        "current_step_index": 0,
        
        # Results
        "results": {},
        "errors": [],
        
        # Retry
        "retry_count": {},
        
        # Regeneration
        "regeneration_count": 0,
        
        # Output
        "final_output": None,
        
        # Status
        "status": "planning",
        
        # Adaptation
        "adaptation_reason": None,
        
        # Metadata
        "metadata": {},
    }
    return cast(OrchestratorState, state)


# =========================
# TICKET HELPERS (Data extraction only)
# =========================

def get_ticket_summary(state: OrchestratorState) -> Dict[str, Any]:
    """
    Extract key information from ticket for agents.
    Pure data extraction — no logic.
    """
    ticket = state["ticket"]
    
    return {
        "title": ticket.get("title", ""),
        "intent": ticket.get("intent", "fix"),
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
        "mr_diff": ticket.get("mr_diff", ""),  # ← Add mr_diff to summary
    }


def get_ticket_text(state: OrchestratorState) -> str:
    """
    Generate a text representation of the ticket for LLM prompts.
    Pure data formatting — no logic.
    """
    ticket = state["ticket"]
    summary = get_ticket_summary(state)
    
    parts = [
        f"Title: {summary['title']}",
        f"Intent: {summary['intent']}",
        f"Scope: {summary['scope']}",
        f"Summary: {summary['summary']}",
        "",
        "Description:",
        summary['description'],
    ]
    
    if summary['acceptance_criteria']:
        parts.append("\nAcceptance Criteria:")
        for ac in summary['acceptance_criteria']:
            parts.append(f"- {ac}")
    
    if summary['constraints']:
        parts.append(f"\nConstraints:\n{summary['constraints']}")
    
    return "\n".join(parts)