"""
Agent HTTP Client
Handles all HTTP communication with the 4 agents (spec, coder, tester, reviewer).
"""

import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from shared.schemas.agent_io import AgentInput, AgentOutput

# =========================
# LOGGING SETUP
# =========================

logger = logging.getLogger(__name__)


# =========================
# AGENT CLIENT
# =========================

class AgentClient:
    """
    HTTP client for calling agent services.
    Each agent is a separate FastAPI service.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize agent client with configuration.
        
        Args:
            config: Dictionary with agent URLs, timeouts, etc.
                Example:
                {
                    "agents": {
                        "spec": {"url": "http://localhost:8001", "timeout": 60},
                        "coder": {"url": "http://localhost:8002", "timeout": 120},
                        "tester": {"url": "http://localhost:8003", "timeout": 180},
                        "reviewer": {"url": "http://localhost:8004", "timeout": 90}
                    }
                }
        """
        self.config = config or {}
        self._default_timeout = 60
        self._agent_defaults = {
            "spec": {"url": "http://localhost:8001", "timeout": 60},
            "coder": {"url": "http://localhost:8002", "timeout": 120},
            "tester": {"url": "http://localhost:8003", "timeout": 180},
            "reviewer": {"url": "http://localhost:8004", "timeout": 90},
        }
    
    def call_agent(
        self,
        agent_name: str,
        step_id: str,
        context: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Call an agent service.
        
        Args:
            agent_name: Name of agent (spec, coder, tester, reviewer)
            step_id: Current step ID (for logging)
            context: Context dictionary with ticket, workspace, previous outputs
            timeout: Request timeout in seconds (overrides config)
        
        Returns:
            Agent result dictionary with status, output, etc.
        
        Raises:
            ValueError: Invalid agent name or invalid response format
            requests.Timeout: Agent request timed out
            requests.RequestException: HTTP error
        """
        if agent_name not in self._agent_defaults:
            raise ValueError(f"Unknown agent: {agent_name}. Valid agents: {list(self._agent_defaults.keys())}")
        
        from shared.config.settings import get_settings
        settings = get_settings()
        if settings.MOCK_AGENTS:
            return {"status": "success", "output": {"mock": True}, "confidence": 0.9, "step_id": step_id}
        
        # Get agent endpoint from config or default
        agent_config = self.config.get("agents", {}).get(agent_name, {})
        agent_url = agent_config.get("url", self._agent_defaults[agent_name]["url"])
        agent_timeout = timeout or agent_config.get("timeout", self._agent_defaults[agent_name]["timeout"])
        
        # Build request payload using AgentInput schema
        payload = self._build_payload(step_id, context)
        
        logger.info(f"Calling agent '{agent_name}' at {agent_url} (timeout: {agent_timeout}s)")
        
        try:
            response = requests.post(
                f"{agent_url}/execute",
                json=payload,
                timeout=agent_timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Agent '{agent_name}' responded with status: {result.get('status', 'unknown')}")
            
            # Validate response against AgentOutput schema
            validated_result = self._validate_response(result)
            
            # Normalize and return
            return self._normalize_result(validated_result, step_id)
            
        except requests.Timeout:
            logger.error(f"Agent '{agent_name}' timed out after {agent_timeout}s")
            raise
        except requests.RequestException as e:
            logger.error(f"Agent '{agent_name}' request failed: {e}")
            raise
        except ValueError as e:
            logger.error(f"Agent '{agent_name}' response validation failed: {e}")
            raise
    
    def _build_payload(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build request payload for agent using AgentInput schema.
        Validates the payload before sending.
        """
        try:
            payload = AgentInput(
                step_id=step_id,
                agent_type=context.get("agent_type"),
                workspace_path=context.get("workspace_path"),
                ticket=context.get("ticket", {}),
                ticket_summary=context.get("ticket_summary", {}),
                step_description=context.get("step_description", ""),
                previous_outputs=context.get("previous_outputs", {}),
                metadata=context.get("metadata", {}),
            )
            return payload.dict()
        except Exception as e:
            logger.error(f"Failed to build payload with AgentInput schema: {e}")
            raise ValueError(f"Invalid agent input format: {e}")
    
    def _validate_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate agent response against AgentOutput schema.
        
        Args:
            result: Raw response from agent
        
        Returns:
            Validated response as dict
        
        Raises:
            ValueError: If response doesn't match AgentOutput schema
        """
        try:
            validated = AgentOutput(**result)
            return validated.dict()
        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            raise ValueError(f"Invalid agent response format: {e}")
    
    def _normalize_result(self, result: Dict[str, Any], step_id: str) -> Dict[str, Any]:
        """
        Normalize agent result to standard format.
        """
        # Ensure required fields
        normalized = {
            "status": result.get("status", "success"),
            "output": result.get("output", result),
            "confidence": result.get("confidence", 0.5),
            "step_id": step_id,
            "completed_at": datetime.utcnow().isoformat(),
        }
        
        # Preserve any additional fields
        for key, value in result.items():
            if key not in normalized:
                normalized[key] = value
        
        return normalized
    
    def health_check(self, agent_name: str) -> bool:
        """
        Check if an agent is healthy.
        
        Args:
            agent_name: Name of agent to check
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            agent_config = self.config.get("agents", {}).get(agent_name, {})
            agent_url = agent_config.get("url", self._agent_defaults[agent_name]["url"])
            
            response = requests.get(f"{agent_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


# =========================
# SINGLETON INSTANCE
# =========================

_default_client: Optional[AgentClient] = None


def get_agent_client(config: Optional[Dict[str, Any]] = None) -> AgentClient:
    """
    Get singleton agent client instance.
    """
    global _default_client
    if _default_client is None or config is not None:
        _default_client = AgentClient(config)
    return _default_client