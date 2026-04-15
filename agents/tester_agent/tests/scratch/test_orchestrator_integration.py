import sys
import os
import asyncio

# Ensure project root is in sys.path
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, patch
from shared.schemas.agent_io import AgentInput, AgentType, AgentStatus

async def test_main_endpoint():
    print("Testing tester_agent/main.py entry point logic...")
    
    # Mock request data
    mock_input = {
        "step_id": "test_step_1",
        "agent_type": "tester",
        "workspace_path": "/workspaces/custom_test_path",
        "ticket": {
            "repo_url": "https://github.com/user/test-repo"
        },
        "ticket_summary": {
            "title": "Test Title",
            "intent": "test",
            "summary": "test summary",
            "description": "test description",
            "workspace_path": "/workspaces/custom_test_path"
        },
        "step_description": "Create tests for the API",
        "previous_outputs": {
            "spec": {
                "spec_text": "This is the specification text."
            }
        },
        "metadata": {
            "model_profile": {"name": "standard"},
            "retry_count": 0
        }
    }
    
    # Create AgentInput object
    request = AgentInput(**mock_input)
    
    # We need to mock the testing_agent_node function call to avoid real LLM calls
    with patch("agents.tester_agent.main.testing_agent_node") as mock_node, \
         patch("agents.tester_agent.main.log_request_start") as mock_log_start:
        
        mock_log_start.return_value = ("mock_log.log", "mock_chat.log")
        mock_node.return_value = {
            "agent_outcome": "success",
            "orchestrator_inbox": {"summary": "Completed successfully", "issues": []},
            "tests_passed": True,
            "tests_generated": 5,
            "total_tokens": 100
        }
        
        # Manually invoke the execute logic (to avoid running the whole FastAPI app)
        from agents.tester_agent.main import execute
        
        response = await execute(request)
        
        print(f"Response Status: {response.status}")
        print(f"Response Output: {response.output}")
        
        # Verify that the workspace_path was correctly passed in the state to the node
        args, kwargs = mock_node.call_args
        state_passed = args[0]
        
        if state_passed.get("workspace_path") == "/workspaces/custom_test_path":
            print("SUCCESS: correctly passed workspace_path to agent node.")
        else:
            print(f"FAILURE: incorrect workspace_path in state: {state_passed.get('workspace_path')}")

        if state_passed.get("spec") == "This is the specification text.":
            print("SUCCESS: correctly extracted spec_text from previous_outputs.")
        else:
            print(f"FAILURE: incorrect spec in state: {state_passed.get('spec')}")

if __name__ == "__main__":
    # Ensure sys.path includes the project root
    import sys
    import os
    sys.path.append(os.getcwd())
    
    asyncio.run(test_main_endpoint())
