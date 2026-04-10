"""
LLM Provider - Unified interface for Groq API only
"""

import os
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# =========================
# BASE PROVIDER
# =========================

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        format: Optional[str] = None,
        temperature: float = 0.1,
    ) -> str:
        """Send chat messages and return response."""
        pass


# =========================
# GROQ PROVIDER (API)
# =========================

class GroqProvider(BaseLLMProvider):
    """Groq API provider."""
    
    def __init__(self, model: str, api_key: str):
        from groq import Groq
        self.model = model
        self.client = Groq(api_key=api_key)
        logger.info(f"Groq provider initialized with model: {model}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        format: Optional[str] = None,
        temperature: float = 0.1,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"} if format == "json" else None,
        )
        return response.choices[0].message.content


# =========================
# FACTORY FUNCTION
# =========================

def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function that returns Groq provider.
    
    Environment variables required:
    - GROQ_API_KEY: Your Groq API key
    - SPEC_AGENT_LLM_MODEL: Model name (default: mixtral-8x7b-32768)
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable required for Groq provider")
    
    model = os.environ.get("SPEC_AGENT_LLM_MODEL", "mixtral-8x7b-32768")
    
    logger.info(f"Initializing Groq provider with model: {model}")
    
    return GroqProvider(model=model, api_key=api_key)