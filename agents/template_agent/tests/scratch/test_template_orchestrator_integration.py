import sys
import os
import asyncio

# Ensure project root is in sys.path
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, patch
from shared.schemas.agent_io import AgentInput, AgentType, AgentStatus

async def test_template_main_endpoint():
    print("Testing template_agent/main.py entry point logic...")
    
    # Mock request data
    mock_input = {
        "step_id": "test_template_step_1",
        "agent_type": "tester",  # Template uses a valid enum for validation
        "workspace_path": "/workspaces/template_test_path",
        "ticket": {
            "repo_url": "https://github.com/user/template-repo"
        },
        "ticket_summary": {
            "title": "Template Title",
            "intent": "test",
            "summary": "template summary",
            "description": "template description",
            "workspace_path": "/workspaces/template_test_path"
        },
        "step_description": "General task for the template agent",
        "previous_outputs": {
            "spec": {
                "spec_text": "Placeholder Specification."
            }
        },
        "metadata": {
            "model_profile": {"name": "standard"},
            "retry_count": 0
        }
    }
    
    # Create AgentInput object
    request = AgentInput(**mock_input)
    
    # Mock the template_agent_node function call
    from agents.template_agent import main as template_main
    with patch.object(template_main, "template_agent_node") as mock_node, \
         patch.object(template_main, "log_request_start") as mock_log_start:
        
        mock_log_start.return_value = ("mock_template_log.log", "mock_template_chat.log")
        mock_node.return_value = {
            "agent_outcome": "success",
            "orchestrator_inbox": {
                "summary": "Template logic executed",
                "artifacts": []
            },
            "total_tokens": 100
        }
        
        # Manually invoke the execute logic
        from agents.template_agent.main import execute
        
        response = await execute(request)
        
        print(f"Response Status: {response.status}")
        print(f"Response Output: {response.output}")
        
        # Verify that the workspace_path was correctly passed
        args, kwargs = mock_node.call_args
        state_passed = args[0]
        
        if state_passed.get("workspace_path") == "/workspaces/template_test_path":
            print("SUCCESS: correctly passed workspace_path to template node.")
        else:
            print(f"FAILURE: incorrect workspace_path in state: {state_passed.get('workspace_path')}")

        if state_passed.get("spec") == "Placeholder Specification.":
            print("SUCCESS: correctly extracted spec_text from previous_outputs.")
        else:
            print(f"FAILURE: incorrect spec in state: {state_passed.get('spec')}")

if __name__ == "__main__":
    asyncio.run(test_template_main_endpoint())
