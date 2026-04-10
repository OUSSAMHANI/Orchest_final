"""
Spec Handler - Adapter between FastAPI and the agent_spec pipeline.
"""

import logging
from typing import Dict, Any
from shared.schemas.agent_io import AgentInput
from .agent_spec.graph import run_agent_spec

logger = logging.getLogger(__name__)


class SpecHandler:
    """Adapter that calls the agent_spec pipeline."""
    
    def process(self, request: AgentInput) -> Dict[str, Any]:
        """Process a spec generation request."""
        workspace_path = request.workspace_path
        ticket = request.ticket
        
        thread_id = str(ticket.get("issue_id") or ticket.get("event_id", "default"))
        
        logger.info(f"Processing spec for workspace: {workspace_path}")
        
        # Call the pipeline
        location = run_agent_spec(
            ticket=ticket,
            mr_diff=request.mr_diff,
            repo_path=workspace_path,
            thread_id=thread_id,
            llm_model=None
        )
        
        return self._format_output(location, workspace_path, ticket)
    
    def _format_output(
        self, 
        location: Dict[str, Any], 
        workspace_path: str,
        ticket: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform location dict to spec agent output format."""
        
        # Build requirements from location data
        requirements = []
        if location.get("root_cause"):
            requirements.append(f"Root cause: {location['root_cause']}")
        if location.get("expected_behavior"):
            requirements.append(f"Expected behavior: {location['expected_behavior']}")
        if ticket.get("acceptance_criteria"):
            requirements.extend(ticket["acceptance_criteria"])
        
        # Build implementation notes from location
        implementation_notes = []
        if location.get("problem_summary"):
            implementation_notes.append(location["problem_summary"])
        if location.get("function"):
            implementation_notes.append(f"Function: {location['function']}")
        if location.get("line"):
            implementation_notes.append(f"Line: {location['line']}")
        if location.get("callers"):
            implementation_notes.append(f"Callers: {', '.join(location['callers'][:3])}")
        if location.get("callees"):
            implementation_notes.append(f"Callees: {', '.join(location['callees'][:3])}")
        if location.get("code_context"):
            implementation_notes.append(f"\nCode context:\n{location['code_context']}")
        
        # Build suggested files
        suggested_files = []
        if location.get("file"):
            suggested_files.append(location["file"])
        
        return {
            "spec_file": f"{workspace_path}/spec.md",
            "requirements": requirements,
            "acceptance_criteria": ticket.get("acceptance_criteria", []),
            "constraints": location.get("patch_constraints", []),
            "suggested_files": suggested_files,
            "implementation_notes": "\n".join(implementation_notes),
            "confidence": location.get("confidence", 0.85),
            "language": location.get("language"),
            "fallback_locations": location.get("fallback_locations", [])
        }