"""
Ticket model for incoming Kafka messages.
Represents a work item from GitLab to be processed by the orchestrator.
"""

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class Ticket(BaseModel):
    """
    Ticket received from Kafka (originating from GitLab).
    The workspace must be pre-cloned before the orchestrator receives this.
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
    
    # === Added field (required for orchestrator) ===
    workspace_path: str  # Pre-cloned repo location