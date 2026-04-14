import asyncio
import os
import sys
import argparse
from dotenv import load_dotenv
from unittest.mock import MagicMock, patch

# Ensure project root is in PYTHONPATH
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

# Also ensure the agent's Own directory is in sys.path
AGENT_DIR = os.path.join(PROJ_ROOT, "agents", "tester_agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)


from agents.tester_agent.agents.testing_agent import TestingAgent
from agents.tester_agent.llm.base_config import MODEL_PROFILE_STANDARD

async def main():
    # Load environment variables from the agent's .env file
    load_dotenv(os.path.join(AGENT_DIR, ".env"))
    
    parser = argparse.ArgumentParser(description="Manual Test for Tester Agent")
    parser.add_argument("--spec", type=str, default="Create integration tests in 'tests/integration/' to verify the API endpoints using pytest and requests. Ensure the test suite is modular and includes a 'script.sh' for automated execution and teardown.", 
                        help="Specification for the agent")
    parser.add_argument("--workspace", type=str, default="workspace/test_tester", 
                        help="Workspace directory relative to project root")
    parser.add_argument("--model", type=str, default="google_genai/gemma-4-31b-it", 
                        help="LLM model string")
    
    args = parser.parse_args()

    # Set environment variables for the agent
    os.environ["LLM_MODEL"] = args.model
    # Make sure we have a dummy API key if not set, or warn
    if "GOOGLE_API_KEY" not in os.environ:
        print("WARNING: GOOGLE_API_KEY not set. LLM calls may fail.")

    workspace_path = os.path.join(PROJ_ROOT, args.workspace)
    if not os.path.exists(workspace_path):
        os.makedirs(workspace_path)
    
    print(f"--- Tester Agent Manual Test ---")
    print(f"Spec: {args.spec}")
    print(f"Workspace: {workspace_path}")
    print(f"Model: {args.model}")
    print("-" * 30)

    state = {
        "spec": args.spec,
        "repo_url": "",
        "workspace_path": workspace_path,
        "model_profile": MODEL_PROFILE_STANDARD,
        "iteration_count": 0,
        "total_tokens": 0,
        "step_id": "manual_test_tester_1",
        "agent_reports": [],
        "mcp_servers": [],
    }

    agent = TestingAgent()

    print("[INFO] Running with real file system writes...")
    result = await agent.run(state)

    print("-" * 30)
    print(f"Outcome: {result.get('agent_outcome')}")
    print(f"Summary: {result.get('orchestrator_inbox', {}).get('summary')}")
    print(f"Tests Generated: {result.get('tests_generated', [])}")
    print(f"Total Tokens: {result.get('total_tokens')}")

if __name__ == "__main__":
    asyncio.run(main())
