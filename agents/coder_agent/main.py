"""
Coder Agent - Generates code based on specifications.
"""
import os
import sys

# Ensure project root is in PYTHONPATH
# This allows 'shared', 'config', 'llm', etc. to be imported correctly
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJ_ROOT not in sys.path:
    sys.path.append(PROJ_ROOT)

# Also ensure the agent's Own directory is in sys.path so 'from state import ...' works
# if it's meant to be local to the agent.
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if AGENT_DIR not in sys.path:
    sys.path.append(AGENT_DIR)


from fastapi import FastAPI
from shared.schemas.agent_io import AgentInput, AgentOutput, AgentStatus
from agents.coder_agent.agents.coding_agent import coding_agent_node
from agents.coder_agent.llm.base_config import MODEL_PROFILE_STANDARD

app = FastAPI(title="Coder Agent", version="1.0.0")

@app.post("/execute")
async def execute(request: AgentInput) -> AgentOutput:
    """
    Generate code based on specification.
    """
    # Build the initial GraphState for the agent node
    # The agent expects 'spec', 'workspace_dir', and 'model_profile' etc.
    state = {
        "spec": request.previous_outputs.get("spec", {}).get("spec_text", "") or request.step_description,
        "repo_url": request.ticket.get("repo_url", ""),
        "workspace_path": request.workspace_path,
        "model_profile": request.metadata.get("model_profile", MODEL_PROFILE_STANDARD),
        "iteration_count": request.metadata.get("retry_count", 0),
        "total_tokens": 0,
        "step_id": request.step_id,
        "agent_reports": [],
        "mcp_servers": request.metadata.get("mcp_servers", []),
        "detected_language": request.metadata.get("detected_language"),
        "detected_framework": request.metadata.get("detected_framework"),
    }

    try:
        # Run the agent node
        result_state = await coding_agent_node(state)
        
        # Extract report
        report = result_state.get("orchestrator_inbox", {})
        
        return AgentOutput(
            status=result_state.get("agent_outcome", "success"),
            output={
                "files": report.get("artifacts", []),
                "changes": report.get("summary", ""),
                "branch": result_state.get("branch"),
                "commit_hash": result_state.get("commit_hash"),
                "diff": result_state.get("diff")
            },
            confidence=0.9 if result_state.get("agent_outcome") == "success" else 0.5,
            metadata={
                "agent": "coder",
                "step_id": request.step_id,
                "tokens": result_state.get("total_tokens", 0),
                "iterations": result_state.get("iteration_count", 0),
                "issues": report.get("issues", [])
            }
        )
    except Exception as e:
        return AgentOutput(
            status=AgentStatus.FAILED,
            output={},
            confidence=0.0,
            error=str(e),
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