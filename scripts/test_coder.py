import asyncio
import os
import sys
import argparse
from unittest.mock import MagicMock, patch

# Ensure project root is in PYTHONPATH
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_ROOT not in sys.path:
    sys.path.append(PROJ_ROOT)

# Also ensure the agent's Own directory is in sys.path
AGENT_DIR = os.path.join(PROJ_ROOT, "agents", "coder_agent")
if AGENT_DIR not in sys.path:
    sys.path.append(AGENT_DIR)


from agents.coder_agent.agents.coding_agent import CodingAgent
from agents.coder_agent.llm.base_config import MODEL_PROFILE_STANDARD

async def main():
    parser = argparse.ArgumentParser(description="Manual Test for Coder Agent")
    parser.add_argument("--spec", type=str, default="Create a simple hello_world.py file that prints 'Hello World'", 
                        help="Specification for the agent")
    parser.add_argument("--workspace", type=str, default="workspace/test_coder", 
                        help="Workspace directory relative to project root")
    parser.add_argument("--dry-run", action="store_true", 
                        help="If set, file writes will be mocked")
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
    
    print(f"--- Coder Agent Manual Test ---")
    print(f"Spec: {args.spec}")
    print(f"Workspace: {workspace_path}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Model: {args.model}")
    print("-" * 30)

    state = {
        "spec": args.spec,
        "repo_url": "",
        "workspace_path": workspace_path,
        "model_profile": MODEL_PROFILE_STANDARD,
        "iteration_count": 0,
        "total_tokens": 0,
        "step_id": "manual_test_1",
        "agent_reports": [],
        "mcp_servers": [],
    }

    agent = CodingAgent()

    # If dry run, patch write_file tool
    if args.dry_run:
        print("[INFO] Mocking file system for dry run...")
        with patch("agents.coder_agent.tools.files.write_file.invoke") as mock_write:
            mock_write.side_effect = lambda args: f"Mocked write to {args.get('file_path')}"
            result = await agent.run(state)
    else:
        print("[INFO] Running with real file system writes...")
        result = await agent.run(state)

    print("-" * 30)
    print(f"Outcome: {result.get('agent_outcome')}")
    print(f"Summary: {result.get('orchestrator_inbox', {}).get('summary')}")
    print(f"Artifacts: {result.get('orchestrator_inbox', {}).get('artifacts')}")
    print(f"Total Tokens: {result.get('total_tokens')}")

if __name__ == "__main__":
    asyncio.run(main())
