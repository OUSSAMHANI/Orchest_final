"""
Reviewer Agent - Reviews code and creates merge requests.
"""

from fastapi import FastAPI
from shared.schemas.agent_io import AgentInput, AgentOutput

app = FastAPI(title="Reviewer Agent", version="1.0.0")

@app.post("/execute")
async def execute(request: AgentInput) -> AgentOutput:
    """
    Review code and create merge request.
    
    Expected output:
    {
        "overall_score": 8.5,
        "issues": [{"severity": "high", "message": "..."}],
        "suggestions": ["suggestion1", "suggestion2"],
        "approved": true,
        "mr_url": "https://gitlab.com/.../merge_requests/1",
        "mr_iid": 123,
        "summary": "Review summary..."
    }
    """
    # TODO: Implement by coworker
    return AgentOutput(
        status="success",
        output={
            "overall_score": 0.0,
            "issues": [],
            "suggestions": [],
            "approved": False,
            "mr_url": None,
            "mr_iid": None,
            "summary": ""
        },
        confidence=0.0,
        metadata={"agent": "reviewer", "step_id": request.step_id}
    )

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "reviewer"}

@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    return {"status": "ready", "agent": "reviewer"}