import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import os
import sys

# Add project root to sys.path
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJ_ROOT not in sys.path:
    sys.path.append(PROJ_ROOT)

# Add agent dir to sys.path
AGENT_DIR = os.path.join(PROJ_ROOT, "agents", "coder_agent")
if AGENT_DIR not in sys.path:
    sys.path.append(AGENT_DIR)


from agents.coder_agent.agents.coding_agent import CodingAgent
from agents.coder_agent.state import GraphState

@pytest.fixture
def mock_state():
    return {
        "spec": "Fix a bug in the code",
        "repo_url": "https://github.com/test/repo",
        "workspace_path": "/tmp/test_workspace",
        "model_profile": {},
        "iteration_count": 0,
        "total_tokens": 0,
    }

@pytest.mark.asyncio
async def test_build_context_basic(mock_state):
    agent = CodingAgent()
    
    # Mock extract_language and other dependencies
    with patch("agents.coder_agent.agents.coding_agent.detect_language") as mock_detect:
        mock_detect.return_value = {"language": "python", "framework": "fastapi"}
        
        with patch("agents.coder_agent.agents.coding_agent.get_hints") as mock_hints:
            mock_hints.return_value = {
                "framework": "pytest",
                "file_pattern": "*.py",
                "script_hint": "pytest",
                "convention": "standard"
            }
            
            # We also need to mock os.walk and os.path.exists in _file_list
            with patch("os.path.exists", return_value=True):
                with patch("os.walk", return_value=[("/tmp/test_workspace", [], ["main.py"])]):
                    context = await agent.build_context(mock_state)
                    
                    assert context["detected_language"] == "python"
                    assert context["detected_framework"] == "fastapi"
                    assert "spec_text" in context
                    assert "main.py" in context["file_list_str"]

@pytest.mark.asyncio
async def test_get_tools(mock_state):
    agent = CodingAgent()
    agent._cached_workspace = "/tmp/test_workspace"
    agent._cached_lang = "python"
    
    with patch("agents.coder_agent.agents.coding_agent.get_file_tools") as mock_file_tools:
        mock_file_tools.return_value = [MagicMock(name="write_file")]
        with patch("agents.coder_agent.agents.coding_agent.get_search_tools") as mock_search_tools:
            mock_search_tools.return_value = [MagicMock(name="search")]
            
            tools = await agent.get_tools(mock_state)
            
            # Should have file tools + search tools + run_tests tool
            assert len(tools) >= 3
            tool_names = [t.name for t in tools]
            assert "run_tests" in tool_names

@pytest.mark.asyncio
async def test_build_report(mock_state):
    agent = CodingAgent()
    agent._cached_lang = "python"
    agent._cached_fw = "fastapi"
    agent._cached_workspace = "/tmp/test_workspace"
    agent._artifacts = ["file1.py"]
    
    report = await agent.build_report(
        status="success",
        summary="Fixed everything",
        state=mock_state,
        tokens=100
    )
    
    assert report["agent"] == "coding_agent"
    assert report["status"] == "success"
    assert report["summary"] == "Fixed everything"
    assert "file1.py" in report["artifacts"]
    assert report["metadata"]["language"] == "python"

