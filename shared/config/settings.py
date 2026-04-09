"""
Central Configuration Management for Orchestrator System
Loads from environment variables and .env file with validation.
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field, validator
from pydantic_settings import BaseSettings


# Load .env file from project root
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings have defaults or are required.
    """
    
    # =========================
    # KAFKA CONFIGURATION
    # =========================
    KAFKA_BROKERS: List[str] = Field(
        default=["localhost:9092"],
        description="Kafka broker addresses"
    )
    KAFKA_TOPIC_TICKETS: str = Field(
        default="gitlab-tickets",
        description="Topic for incoming tickets"
    )
    KAFKA_TOPIC_RESULTS: str = Field(
        default="orchestrator-results",
        description="Topic for results (optional)"
    )
    KAFKA_CONSUMER_GROUP: str = Field(
        default="orchestrator-group",
        description="Consumer group ID"
    )
    KAFKA_ENABLE_AUTO_COMMIT: bool = Field(
        default=True,
        description="Enable auto commit for Kafka"
    )
    KAFKA_AUTO_OFFSET_RESET: str = Field(
        default="earliest",
        description="Offset reset policy: earliest, latest, none"
    )
    KAFKA_SECURITY_PROTOCOL: Optional[str] = Field(
        default=None,
        description="Security protocol: PLAINTEXT, SSL, SASL_PLAINTEXT"
    )
    KAFKA_SASL_MECHANISM: Optional[str] = Field(
        default=None,
        description="SASL mechanism: PLAIN, SCRAM-SHA-256, etc."
    )
    KAFKA_SASL_USERNAME: Optional[str] = Field(
        default=None,
        description="SASL username"
    )
    KAFKA_SASL_PASSWORD: Optional[str] = Field(
        default=None,
        description="SASL password"
    )
    
    # =========================
    # AGENT CONFIGURATION
    # =========================
    SPEC_AGENT_URL: str = Field(
        default="http://localhost:8001",
        description="Spec agent service URL"
    )
    CODER_AGENT_URL: str = Field(
        default="http://localhost:8002",
        description="Coder agent service URL"
    )
    TESTER_AGENT_URL: str = Field(
        default="http://localhost:8003",
        description="Tester agent service URL"
    )
    REVIEWER_AGENT_URL: str = Field(
        default="http://localhost:8004",
        description="Reviewer agent service URL"
    )
    
    AGENT_TIMEOUT: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Default agent timeout in seconds"
    )
    AGENT_MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries per agent call"
    )
    AGENT_RETRY_BACKOFF: float = Field(
        default=1.0,
        ge=0.5,
        le=30.0,
        description="Retry backoff multiplier"
    )
    AGENT_RETRYABLE_ERRORS: List[str] = Field(
        default=["timeout", "connection", "rate_limit", "503", "429"],
        description="Error patterns that trigger retry"
    )
    
    # =========================
    # ORCHESTRATOR CONFIGURATION
    # =========================
    MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries per step"
    )
    MAX_REGENERATIONS: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Maximum plan regenerations"
    )
    CONFIDENCE_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to consider step successful"
    )
    STEP_TIMEOUT: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="Maximum execution time per step in seconds"
    )
    RECURSION_LIMIT: int = Field(
        default=100,
        ge=10,
        le=500,
        description="LangGraph recursion limit"
    )
    DEAD_LETTER_ENABLED: bool = Field(
        default=True,
        description="Enable dead-letter queue for failed messages"
    )
    DEAD_LETTER_TOPIC: str = Field(
        default="orchestrator-dead-letter",
        description="Dead-letter topic name"
    )
    
    # =========================
    # WORKSPACE CONFIGURATION
    # =========================
    WORKSPACE_BASE_PATH: str = Field(
        default="/workspaces",
        description="Base directory for all workspaces"
    )
    WORKSPACE_CLEANUP_ON_COMPLETE: bool = Field(
        default=True,
        description="Delete workspace after successful completion"
    )
    WORKSPACE_CLEANUP_ON_FAILURE: bool = Field(
        default=False,
        description="Delete workspace after failure"
    )
    WORKSPACE_CLEANUP_DELAY_SECONDS: int = Field(
        default=3600,
        description="Delay before cleanup (for debugging)"
    )
    WORKSPACE_MAX_SIZE_MB: int = Field(
        default=1024,
        description="Maximum workspace size in MB"
    )
    
    # =========================
    # GITLAB CONFIGURATION
    # =========================
    GITLAB_URL: str = Field(
        default="https://gitlab.com",
        description="GitLab instance URL"
    )
    GITLAB_TOKEN: str = Field(
        default="",
        description="GitLab personal access token"
    )
    GITLAB_PROJECT_ID: Optional[int] = Field(
        default=None,
        description="GitLab project ID (if fixed)"
    )
    GITLAB_MERGE_REQUEST_TITLE_PREFIX: str = Field(
        default="[AI]",
        description="Prefix for MR titles"
    )
    GITLAB_MERGE_REQUEST_TARGET_BRANCH: str = Field(
        default="main",
        description="Default target branch for MR"
    )
    GITLAB_AUTO_ASSIGN_REVIEWER: bool = Field(
        default=True,
        description="Auto-assign reviewer to MR"
    )
    
    @validator("GITLAB_TOKEN")
    def validate_gitlab_token(cls, v):
        if v and not v.startswith("glpat-"):
            raise ValueError("GitLab token should start with 'glpat-'")
        return v
    
    # =========================
    # LLM CONFIGURATION
    # =========================
    LLM_PROVIDER: str = Field(
        default="openai",
        description="LLM provider: openai, anthropic, local, groq"
    )
    LLM_MODEL: str = Field(
        default="gpt-4",
        description="LLM model name"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature"
    )
    LLM_MAX_TOKENS: int = Field(
        default=4096,
        ge=1,
        le=32768,
        description="Maximum tokens per generation"
    )
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    OPENAI_BASE_URL: Optional[str] = Field(
        default=None,
        description="OpenAI base URL (for proxies)"
    )
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    LOCAL_LLM_URL: Optional[str] = Field(
        default=None,
        description="Local LLM endpoint URL"
    )
    GROQ_API_KEY: Optional[str] = Field(
    default=None,
    description="Groq API key"
)
    GROQ_MODEL: Optional[str] = Field(
    default=None,
    description="Groq model (overrides LLM_MODEL)"
)
    
    @validator("LLM_PROVIDER")
    def validate_llm_provider(cls, v):
        if v not in ["openai", "anthropic", "local","groq"]:
            raise ValueError(f"Invalid LLM provider: {v}. Must be openai, anthropic, or local")
        return v
    
    # =========================
    # LOGGING CONFIGURATION
    # =========================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format: json or text"
    )
    LOG_FILE: Optional[str] = Field(
        default=None,
        description="Log file path (None = console only)"
    )
    LOG_MAX_BYTES: int = Field(
        default=10485760,
        description="Maximum log file size in bytes"
    )
    LOG_BACKUP_COUNT: int = Field(
        default=5,
        description="Number of log backups to keep"
    )
    
    # =========================
    # API CONFIGURATION
    # =========================
    API_HOST: str = Field(
        default="0.0.0.0",
        description="API host"
    )
    API_PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="API port"
    )
    API_WORKERS: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Number of uvicorn workers"
    )
    API_RELOAD: bool = Field(
        default=False,
        description="Auto-reload on code changes (development)"
    )
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    API_RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        description="Rate limit requests per minute"
    )
    
    # =========================
    # MONITORING CONFIGURATION
    # =========================
    ENABLE_METRICS: bool = Field(
        default=True,
        description="Enable Prometheus metrics endpoint"
    )
    ENABLE_TRACING: bool = Field(
        default=False,
        description="Enable OpenTelemetry tracing"
    )
    METRICS_PORT: int = Field(
        default=9090,
        description="Prometheus metrics port"
    )
    TRACING_ENDPOINT: Optional[str] = Field(
        default=None,
        description="OpenTelemetry collector endpoint"
    )
    SERVICE_NAME: str = Field(
        default="orchestrator",
        description="Service name for tracing"
    )
    
    # =========================
    # DEVELOPMENT CONFIGURATION
    # =========================
    DEBUG: bool = Field(
        default=False,
        description="Debug mode"
    )
    MOCK_AGENTS: bool = Field(
        default=False,
        description="Mock agent calls (development)"
    )
    MOCK_GITLAB: bool = Field(
        default=False,
        description="Mock GitLab API (development)"
    )
    SKIP_WORKSPACE_VALIDATION: bool = Field(
        default=False,
        description="Skip workspace validation (development)"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# =========================
# SINGLETON INSTANCE
# =========================

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get singleton settings instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# =========================
# CONVENIENCE FUNCTIONS
# =========================

def is_development() -> bool:
    """Check if running in development mode."""
    settings = get_settings()
    return settings.DEBUG or settings.API_RELOAD


def is_production() -> bool:
    """Check if running in production mode."""
    return not is_development()


def get_agent_url(agent_name: str) -> str:
    """Get URL for a specific agent by name."""
    settings = get_settings()
    urls = {
        "spec": settings.SPEC_AGENT_URL,
        "coder": settings.CODER_AGENT_URL,
        "tester": settings.TESTER_AGENT_URL,
        "reviewer": settings.REVIEWER_AGENT_URL,
    }
    return urls.get(agent_name.lower(), "")