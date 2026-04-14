from typing import TypedDict, List, Dict, Any, Optional

class AgentReport(TypedDict):
    agent: str
    status: str
    summary: str
    artifacts: List[str]
    issues: List[str]
    suggestions: List[str]
    tokens: int
    metadata: Optional[Dict[str, Any]]

class GraphState(TypedDict):
    # Core state
    spec: str
    repo_url: str
    workspace_path: str
    model_profile: Dict[str, Any]
    
    # Execution tracking
    iteration_count: int
    total_tokens: int
    step_id: str
    
    # Results
    test_output: Optional[str]
    tests_passed: Optional[bool]
    agent_outcome: Optional[str]
    
    # Communication
    orchestrator_inbox: Optional[AgentReport]
    agent_reports: List[AgentReport]
    
    # Context
    mcp_servers: List[str]
    detected_language: Optional[str]
    detected_framework: Optional[str]
    
    # Logging
    log_file_path: Optional[str]
    chat_log_file_path: Optional[str]
