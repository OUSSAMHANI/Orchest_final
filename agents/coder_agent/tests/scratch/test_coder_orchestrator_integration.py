import sys
import os
import asyncio

# Ensure project root is in sys.path
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, patch
from shared.schemas.agent_io import AgentInput, AgentType, AgentStatus

async def test_coder_main_endpoint():
    print("Testing coder_agent/main.py entry point logic...")
    
    # Mock request data
    mock_input = {
        "step_id": "test_coder_step_1",
        "agent_type": "coder",
        "workspace_path": "/workspaces/coder_test_path",
        "ticket": {
            "repo_url": "https://github.com/user/coder-repo"
        },
        "ticket_summary": {
            "title": "Coder Title",
            "intent": "feature",
            "summary": "coder summary",
            "description": "coder description",
            "workspace_path": "/workspaces/coder_test_path"
        },
        "step_description": "Implement hello world",
        "previous_outputs": {
            "spec": {
                "spec_text": "Coder Specification logic."
            }
        },
        "metadata": {
            "model_profile": {"name": "standard"},
            "retry_count": 0
        }
    }
    
    # Create AgentInput object
    request = AgentInput(**mock_input)
    
    # Mock the coding_agent_node function call
    from agents.coder_agent import main as coder_main
    with patch.object(coder_main, "coding_agent_node") as mock_node, \
         patch.object(coder_main, "log_request_start") as mock_log_start:
        
        mock_log_start.return_value = ("mock_coder_log.log", "mock_coder_chat.log")
        mock_node.return_value = {
            "agent_outcome": "success",
            "orchestrator_inbox": {
                "summary": "Code generated",
                "artifacts": ["hello_world.py"]
            },
            "total_tokens": 500
        }
        
        # Manually invoke the execute logic
        from agents.coder_agent.main import execute
        
        response = await execute(request)
        
        print(f"Response Status: {response.status}")
        print(f"Response Output: {response.output}")
        
        # Verify that the workspace_path was correctly passed
        args, kwargs = mock_node.call_args
        state_passed = args[0]
        
        if state_passed.get("workspace_path") == "/workspaces/coder_test_path":
            print("SUCCESS: correctly passed workspace_path to coder node.")
        else:
            print(f"FAILURE: incorrect workspace_path in state: {state_passed.get('workspace_path')}")

        if state_passed.get("spec") == "Coder Specification logic.":
            print("SUCCESS: correctly extracted spec_text from previous_outputs.")
        else:
            print(f"FAILURE: incorrect spec in state: {state_passed.get('spec')}")

if __name__ == "__main__":
    asyncio.run(test_coder_main_endpoint())
