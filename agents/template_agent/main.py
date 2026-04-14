"""
Tester Agent - Generates tests based on specifications.
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
from agents.tester_agent.agents.testing_agent import testing_agent_node
from agents.tester_agent.llm.base_config import MODEL_PROFILE_STANDARD

app = FastAPI(title="Tester Agent", version="1.0.0")

@app.post("/execute")
async def execute(request: AgentInput) -> AgentOutput:
    """
    Generate tests based on specification.
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
        "test_output": "",
        "tests_passed": False,
    }

    try:
        # Run the agent node
        result_state = await testing_agent_node(state)
        
        # Extract report
        report = result_state.get("orchestrator_inbox", {})
        
        # Map results to TesterAgentOutput structure
        tests_passed_count = 1 if result_state.get("tests_passed") else 0
        tests_failed_count = 1 if not result_state.get("tests_passed") and result_state.get("agent_outcome") == "failed" else 0
        
        return AgentOutput(
            status=result_state.get("agent_outcome", "success"),
            output={
                "tests_passed": tests_passed_count,
                "tests_failed": tests_failed_count,
                "tests_skipped": 0,
                "tests_total": tests_passed_count + tests_failed_count,
                "coverage": 0.0,
                "report_file": None,
                "failures": [{"message": i} for i in report.get("issues", [])] if tests_failed_count > 0 else [],
                "tests_generated": result_state.get("tests_generated", 0)
            },
            confidence=0.9 if result_state.get("agent_outcome") == "success" else 0.5,
            metadata={
                "agent": "tester",
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
            metadata={"agent": "tester", "step_id": request.step_id}
        )

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "tester"}

@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    return {"status": "ready", "agent": "tester"}