"""
Agent Input/Output Contracts
Shared between orchestrator and all agents (spec, coder, tester, reviewer).
Single source of truth for agent communication.
ALL COMMUNICATIONS ARE JSON.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


# =========================
# ENUMS
# =========================

class AgentStatus(str, Enum):
    """Agent execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class AgentType(str, Enum):
    """Available agent types."""
    SPEC = "spec"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"


class IntentType(str, Enum):
    """Ticket intent type."""
    FIX = "fix"
    FEATURE = "feature"
    DOCS = "docs"
    REFACTOR = "refactor"
    TEST = "test"
    REVIEW = "review"


class PriorityType(str, Enum):
    """Ticket priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# =========================
# TICKET SUMMARY SCHEMA
# =========================

class TicketSummary(BaseModel):
    """
    Extracted and structured ticket information for agents.
    This is what agents actually use to understand the task.
    """
    
    # Core identification
    issue_id: Optional[int] = Field(None, description="GitLab issue/work item ID")
    event_id: Optional[str] = Field(None, description="Unique event UUID")
    project: Optional[str] = Field(None, description="Project name")
    
    # Ticket content (structured)
    title: str = Field(..., description="Issue title, may contain [AGENT:type] prefix")
    intent: IntentType = Field(..., description="Intent: fix, feature, docs, refactor, test, review")
    scope: Optional[str] = Field(None, description="Affected component/module (e.g., kafka-producer, auth-service)")
    summary: str = Field(..., description="Short summary of what needs to be done")
    description: str = Field(..., description="Full description with all details")
    
    # Structured sections (parsed from description)
    context: Optional[str] = Field(None, description="Additional context, background information")
    acceptance_criteria: List[str] = Field(default_factory=list, description="List of acceptance criteria that must be met")
    constraints: Optional[str] = Field(None, description="Technical constraints, limitations, restrictions")
    non_goals: Optional[str] = Field(None, description="What is explicitly NOT to be done")
    
    # Priority and metadata
    priority: PriorityType = Field(PriorityType.NORMAL, description="Priority level")
    author: Optional[str] = Field(None, description="User who created the ticket")
    labels: List[str] = Field(default_factory=list, description="GitLab labels")
    
    # Git information
    branch: Optional[str] = Field(None, description="Branch to work on (will be created if not exists)")
    workspace_path: str = Field(..., description="Absolute path to pre-cloned repository")
    
    # URLs
    gitlab_url: Optional[str] = Field(None, description="GitLab work item URL")
    
    # Hints
    hinted_scope: List[str] = Field(default_factory=list, description="Hinted files/directories to focus on")
    
    class Config:
        json_schema_extra = {
            "example": {
                "issue_id": 187940541,
                "event_id": "df94d58e-0960-407d-9e0b-28b7ae077338",
                "project": "WebHookTest",
                "title": "[AGENT:fix] kafka-producer :: prevent connection leak",
                "intent": "fix",
                "scope": "kafka-producer",
                "summary": "prevent connection leak",
                "description": "Intent\nFix connection leak in Kafka producer lifecycle\n\nContext\nProducer connections are not closed after request completion, causing file descriptor growth.\nExpected: connections are always released after use.",
                "context": "Producer connections are not closed after request completion, causing file descriptor growth.",
                "acceptance_criteria": [
                    "No increase in open file descriptors after 1000 requests",
                    "All existing tests pass",
                    "New tests cover lifecycle behavior"
                ],
                "constraints": "Do not change public API",
                "non_goals": "Do not refactor entire Kafka module",
                "priority": "normal",
                "author": "justinianmarcusemperi",
                "labels": ["backend", "performance"],
                "branch": "feature/fix-kafka-leak",
                "workspace_path": "/workspaces/ticket-187940541",
                "gitlab_url": "https://gitlab.com/justinianmarcusemperi/webhooktest/-/work_items/36",
                "hinted_scope": ["services/kafka/producer.py"]
            }
        }


# =========================
# INPUT SCHEMA (Orchestrator → Agent)
# =========================

class AgentInput(BaseModel):
    """
    Standard input all agents receive from orchestrator.
    This is the COMPLETE contract — agents have everything they need.
    """
    
    # ===== Core Identification =====
    step_id: str = Field(
        ..., 
        description="Unique step ID from the execution plan. Used for tracking and logging."
    )
    agent_type: AgentType = Field(
        ..., 
        description="Which agent is being called. Determines how to process the input."
    )
    
    # ===== Workspace Access =====
    workspace_path: str = Field(
        ..., 
        description="Absolute path to pre-cloned repository. Agent MUST read/write files ONLY within this directory."
    )
    
    # ===== Complete Ticket Context =====
    ticket: Dict[str, Any] = Field(
        ..., 
        description="FULL original ticket as received from Kafka. Contains all raw data including description, metadata, etc."
    )
    
    # ===== Structured Ticket Summary =====
    ticket_summary: TicketSummary = Field(
        ..., 
        description="Structured and parsed ticket information. Use this for most operations. Contains intent, scope, acceptance_criteria, constraints, etc."
    )
    
    # ===== Step-Specific Instructions =====
    step_description: str = Field(
        ..., 
        description="What this specific step should accomplish. Example: 'Generate technical specification for fixing connection leak' or 'Fix the connection leak in producer.py'"
    )
    
    # ===== Previous Agent Outputs =====
    previous_outputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="""Outputs from previously executed steps. Structure depends on which steps ran before:
        
        - If SPEC ran before: previous_outputs['spec'] contains spec_file, requirements, acceptance_criteria
        - If CODER ran before: previous_outputs['coder'] contains files, changes, branch
        - If TESTER ran before: previous_outputs['tester'] contains test results, coverage
        - If REVIEWER ran before: previous_outputs['reviewer'] contains review score, issues
        
        Use these to build upon previous work. Example: Coder uses Spec output to implement.
        """
    )
    
    # ===== Execution Configuration =====
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="""Execution metadata and configuration:
        
        Common fields:
        - timeout: Maximum execution time in seconds (default: 120)
        - retry_count: Current retry attempt number
        - max_retries: Maximum retries allowed
        - debug: Enable debug logging (true/false)
        - dry_run: Simulate execution without changes (true/false)
        - llm_model: Specific LLM model to use (if applicable)
        - llm_temperature: LLM temperature setting (0.0 to 1.0)
        """
    )
    mr_diff: str = Field(
        default="",
        description="Git diff of the merge request that introduced/exposed the bug. Used by spec agent for bug localization."
    )
    
    # ===== Validation =====
    @validator("workspace_path")
    def workspace_path_must_exist(cls, v):
        if not v or not v.strip():
            raise ValueError("workspace_path is required and cannot be empty")
        return v.strip()
    
    @validator("step_id")
    def step_id_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError("step_id is required and cannot be empty")
        return v.strip()
    
    @validator("step_description")
    def step_description_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError("step_description is required and cannot be empty")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "step_id": "coder_1",
                "agent_type": "coder",
                "workspace_path": "/workspaces/ticket-187940541",
                "ticket": {
                    "event_id": "df94d58e-0960-407d-9e0b-28b7ae077338",
                    "issue_id": 187940541,
                    "title": "[AGENT:fix] kafka-producer :: prevent connection leak",
                    "intent": "fix",
                    "description": "Fix connection leak..."
                },
                "ticket_summary": {
                    "issue_id": 187940541,
                    "title": "[AGENT:fix] kafka-producer :: prevent connection leak",
                    "intent": "fix",
                    "scope": "kafka-producer",
                    "summary": "prevent connection leak",
                    "description": "Fix connection leak in Kafka producer lifecycle...",
                    "acceptance_criteria": [
                        "No increase in open file descriptors after 1000 requests",
                        "All existing tests pass"
                    ],
                    "constraints": "Do not change public API",
                    "workspace_path": "/workspaces/ticket-187940541"
                },
                "step_description": "Fix the connection leak in services/kafka/producer.py by ensuring connections are always closed after use",
                "previous_outputs": {},
                "metadata": {
                    "timeout": 120,
                    "retry_count": 0,
                    "debug": False
                }
            }
        }


# =========================
# OUTPUT SCHEMA (Agent → Orchestrator)
# =========================

class AgentOutput(BaseModel):
    """
    Standard output all agents return to orchestrator.
    """
    
    # ===== Status =====
    status: AgentStatus = Field(
        ..., 
        description="Execution status: 'success' (completed successfully), 'failed' (error occurred), 'partial' (partial completion)"
    )
    
    # ===== Core Output =====
    output: Dict[str, Any] = Field(
        ...,
        description="""Agent-specific output structure. Content depends on agent type:
        
        SPEC AGENT output:
        {
            "spec_file": "path/to/spec.md",
            "requirements": ["req1", "req2"],
            "acceptance_criteria": ["ac1", "ac2"],
            "constraints": ["constraint1"],
            "dependencies": ["dep1", "dep2"]
        }
        
        CODER AGENT output:
        {
            "files": ["modified/file1.py", "created/file2.py"],
            "changes": "Description of changes made",
            "branch": "feature/branch-name",
            "commit_hash": "abc123...",
            "diff": "git diff output"
        }
        
        TESTER AGENT output:
        {
            "tests_passed": 42,
            "tests_failed": 0,
            "tests_skipped": 3,
            "coverage": 87.5,
            "report_file": "path/to/report.json",
            "failures": []
        }
        
        REVIEWER AGENT output:
        {
            "overall_score": 8.5,
            "issues": [{"severity": "high", "message": "..."}],
            "suggestions": ["suggestion1", "suggestion2"],
            "approved": true,
            "mr_url": "https://gitlab.com/.../merge_requests/1"
        }
        """
    )
    
    # ===== Confidence =====
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0). 1.0 = completely confident, 0.0 = no confidence. Use lower confidence when uncertain."
    )
    
    # ===== Error Information =====
    error: Optional[str] = Field(
        default=None,
        description="Error message if status is 'failed'. Should be human-readable and actionable."
    )
    
    # ===== Execution Metadata =====
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="""Execution metadata:
        
        Common fields:
        - execution_time_ms: Time taken in milliseconds
        - tokens_used: Number of LLM tokens used (if applicable)
        - llm_model: Which LLM model was used
        - llm_temperature: Temperature setting used
        - retry_attempt: Which retry attempt this was
        - warnings: List of warnings during execution
        - debug_info: Additional debug information (if debug mode)
        """
    )
    
    # ===== Validation =====
    @validator("output")
    def output_must_be_valid(cls, v, values):
        if values.get("status") == AgentStatus.SUCCESS and not v:
            raise ValueError("Output cannot be empty when status is success")
        return v
    
    @validator("error")
    def error_required_on_failure(cls, v, values):
        if values.get("status") == AgentStatus.FAILED and not v:
            raise ValueError("Error message required when status is failed")
        return v
    
    class Config:
        json_schema_extra = {
            "example_success": {
                "status": "success",
                "output": {
                    "files": ["services/kafka/producer.py", "tests/test_producer.py"],
                    "changes": "Added connection.close() in finally block and added unit tests",
                    "branch": "feature/fix-kafka-leak",
                    "commit_hash": "a1b2c3d4e5f6"
                },
                "confidence": 0.95,
                "error": None,
                "metadata": {
                    "execution_time_ms": 1234,
                    "tokens_used": 1500,
                    "llm_model": "gpt-4"
                }
            },
            "example_failure": {
                "status": "failed",
                "output": {},
                "confidence": 0.0,
                "error": "Workspace path does not exist: /workspaces/ticket-187940541",
                "metadata": {
                    "execution_time_ms": 234,
                    "retry_attempt": 2
                }
            }
        }


# =========================
# AGENT-SPECIFIC OUTPUT SCHEMAS (Detailed)
# =========================

class SpecAgentOutput(BaseModel):
    """
    Expected output structure from SPEC AGENT.
    This agent analyzes the ticket and creates a technical specification.
    """
    
    spec_file: str = Field(
        ..., 
        description="Path to generated specification file (relative to workspace_path). Example: 'specs/ticket-187940541.md'"
    )
    requirements: List[str] = Field(
        ..., 
        description="List of functional requirements extracted from ticket. Each requirement should be clear and testable."
    )
    acceptance_criteria: List[str] = Field(
        ..., 
        description="List of acceptance criteria that must be met for success. Should match or extend ticket's acceptance_criteria."
    )
    constraints: Optional[List[str]] = Field(
        None, 
        description="Technical constraints to respect. Examples: 'Do not change public API', 'Maintain backward compatibility'"
    )
    dependencies: Optional[List[str]] = Field(
        None, 
        description="Detected internal/external dependencies. Example: ['kafka-python==2.0.0', 'internal/auth-service']"
    )
    suggested_files: Optional[List[str]] = Field(
        None, 
        description="Hinted files that likely need changes. Helps coder agent focus."
    )
    implementation_notes: Optional[str] = Field(
        None, 
        description="Additional notes for implementation. Special considerations, edge cases, etc."
    )


class CoderAgentOutput(BaseModel):
    """
    Expected output structure from CODER AGENT.
    This agent writes/updates code based on specification.
    """
    
    files: List[str] = Field(
        ..., 
        description="List of modified or created files (relative to workspace_path). Example: ['services/kafka/producer.py', 'tests/test_producer.py']"
    )
    changes: str = Field(
        ..., 
        description="Human-readable description of changes made. Should be detailed enough for reviewer."
    )
    branch: Optional[str] = Field(
        None, 
        description="Git branch name created/used for changes. Example: 'feature/fix-kafka-leak-187940541'"
    )
    commit_hash: Optional[str] = Field(
        None, 
        description="Git commit hash if changes were committed. Example: 'a1b2c3d4e5f67890'"
    )
    diff: Optional[str] = Field(
        None, 
        description="Git diff output showing exact changes. Useful for reviewer."
    )
    compile_success: bool = Field(
        True, 
        description="Whether the code compiles/validates successfully (if applicable)"
    )
    warnings: Optional[List[str]] = Field(
        None, 
        description="Warnings during code generation (deprecations, style issues, etc.)"
    )


class TesterAgentOutput(BaseModel):
    """
    Expected output structure from TESTER AGENT.
    This agent runs tests and validates changes.
    """
    
    tests_passed: int = Field(
        ..., 
        description="Number of tests that passed"
    )
    tests_failed: int = Field(
        ..., 
        description="Number of tests that failed"
    )
    tests_skipped: int = Field(
        0, 
        description="Number of tests that were skipped"
    )
    tests_total: int = Field(
        ..., 
        description="Total number of tests run (passed + failed + skipped)"
    )
    coverage: Optional[float] = Field(
        None, 
        description="Test coverage percentage (0.0 to 100.0). Example: 87.5"
    )
    report_file: Optional[str] = Field(
        None, 
        description="Path to detailed test report (relative to workspace_path)"
    )
    failures: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Detailed information about failed tests. Each failure should include test name, error message, and stack trace."
    )
    regression_detected: bool = Field(
        False, 
        description="Whether changes introduced regressions (previously passing tests now failing)"
    )
    performance_impact: Optional[Dict[str, Any]] = Field(
        None, 
        description="Performance impact metrics if measured. Example: {'response_time_ms': {'before': 150, 'after': 145}}"
    )


class ReviewerAgentOutput(BaseModel):
    """
    Expected output structure from REVIEWER AGENT.
    This agent reviews code and creates merge request.
    """
    
    overall_score: float = Field(
        ..., 
        ge=0.0, 
        le=10.0, 
        description="Overall quality score (0-10). 10 = perfect, 0 = completely unacceptable."
    )
    issues: List[Dict[str, Any]] = Field(
        ..., 
        description="Issues found during review. Each issue should have: severity (critical/major/minor), message, file (optional), line (optional)"
    )
    suggestions: List[str] = Field(
        ..., 
        description="Improvement suggestions (non-blocking). These are recommendations, not requirements."
    )
    approved: bool = Field(
        False, 
        description="Whether changes are approved for merge. Set to True if overall_score >= 7.0 typically."
    )
    mr_url: Optional[str] = Field(
        None, 
        description="Merge request URL if created. Example: 'https://gitlab.com/project/-/merge_requests/123'"
    )
    mr_iid: Optional[int] = Field(
        None, 
        description="Merge request internal ID"
    )
    summary: str = Field(
        ..., 
        description="One-paragraph summary of review findings"
    )
    security_concerns: Optional[List[str]] = Field(
        None, 
        description="Security-related issues found (if any)"
    )
    performance_concerns: Optional[List[str]] = Field(
        None, 
        description="Performance-related issues found (if any)"
    )


# =========================
# HEALTH CHECK SCHEMA
# =========================

class AgentHealthResponse(BaseModel):
    """
    Agent health check response.
    Used by orchestrator to verify agent availability.
    """
    
    status: str = Field(
        ..., 
        description="Health status: 'healthy' (ready), 'unhealthy' (not ready), 'degraded' (partial)"
    )
    agent_type: AgentType = Field(
        ..., 
        description="Agent type (spec, coder, tester, reviewer)"
    )
    version: str = Field(
        ..., 
        description="Agent version (semantic versioning). Example: '1.2.0'"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="UTC timestamp of health check"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional health details. Examples: {'llm_available': True, 'dependencies_ok': True}"
    )


# =========================
# ERROR RESPONSE SCHEMA
# =========================

class AgentErrorResponse(BaseModel):
    """
    Standard error response from agent.
    Used when agent cannot process request (validation errors, internal errors).
    """
    
    error: str = Field(
        ..., 
        description="Human-readable error message"
    )
    error_type: str = Field(
        ..., 
        description="Error type: 'timeout', 'validation_error', 'workspace_error', 'llm_error', 'internal_error'"
    )
    step_id: Optional[str] = Field(
        None, 
        description="Step ID that caused the error"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="UTC timestamp of error"
    )
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional error details for debugging"
    )
    recoverable: bool = Field(
        True, 
        description="Whether the error is recoverable (orchestrator can retry)"
    )