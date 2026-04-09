"""
Shared ticket schema contract between Kafka producer, orchestrator, and agents.
All systems must adhere to this schema for compatibility.
"""

from pydantic import BaseModel
from typing import Optional, List


class TicketSchema(BaseModel):
    """
    Shared ticket contract.
    This is the single source of truth for ticket structure across all services.
    """
    
    # Core identification
    event_id: str
    issue_id: int
    project: str
    
    # Ticket content
    title: str
    intent: str
    scope: Optional[str] = None
    summary: str
    description: str
    
    # Structured sections
    context: Optional[str] = None
    acceptance_criteria: Optional[List[str]] = None
    constraints: Optional[str] = None
    non_goals: Optional[str] = None
    
    # Priority and scoping
    priority: str
    hinted_scope: Optional[List[str]] = None
    depends_on: Optional[List[int]] = None
    
    # Git and routing
    branch: Optional[str] = None
    routing_key: str
    action: str
    
    # Metadata
    labels: Optional[List[str]] = None
    author: str
    url: str
    created_at: str
    received_at: str
    updated_at: Optional[str] = None
    
    # Workspace (pre-cloned by external system)
    workspace_path: str