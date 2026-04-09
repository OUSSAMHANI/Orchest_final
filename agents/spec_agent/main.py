"""
Spec Agent - Generates technical specifications from tickets.
"""

from fastapi import FastAPI, HTTPException
from shared.schemas.agent_io import AgentInput, AgentOutput

app = FastAPI(title="Spec Agent", version="1.0.0")

@app.post("/execute")
async def execute(request: AgentInput) -> AgentOutput:
    """
    Generate technical specification from ticket.
    
    Expected output:
    {
        "spec_file": "path/to/spec.md",
        "requirements": ["req1", "req2"],
        "acceptance_criteria": ["ac1", "ac2"],
        "constraints": ["constraint1"],
        "suggested_files": ["file1.py", "file2.py"]
    }
    """
    # TODO: Implement by coworker
    return AgentOutput(
        status="success",
        output={
            "spec_file": "",
            "requirements": [],
            "acceptance_criteria": [],
            "constraints": [],
            "suggested_files": []
        },
        confidence=0.0,
        metadata={"agent": "spec", "step_id": request.step_id}
    )

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "spec"}

@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    return {"status": "ready", "agent": "spec"}