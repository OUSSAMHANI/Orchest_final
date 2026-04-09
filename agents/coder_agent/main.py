"""
Coder Agent - Generates code based on specifications.
"""

from fastapi import FastAPI
from shared.schemas.agent_io import AgentInput, AgentOutput

app = FastAPI(title="Coder Agent", version="1.0.0")

@app.post("/execute")
async def execute(request: AgentInput) -> AgentOutput:
    """
    Generate code based on specification.
    
    Expected output:
    {
        "files": ["modified/file1.py", "created/file2.py"],
        "changes": "Description of changes",
        "branch": "feature/branch-name",
        "commit_hash": "abc123...",
        "diff": "git diff output"
    }
    """
    # TODO: Implement by coworker
    return AgentOutput(
        status="success",
        output={
            "files": [],
            "changes": "",
            "branch": None,
            "commit_hash": None,
            "diff": None
        },
        confidence=0.0,
        metadata={"agent": "coder", "step_id": request.step_id}
    )

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "coder"}

@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    return {"status": "ready", "agent": "coder"}