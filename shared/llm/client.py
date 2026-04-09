"""
LLM Client Module
Supports multiple LLM providers: OpenAI, Anthropic, Azure, Local, Groq, Cohere, Together.
Configuration comes from environment variables via settings.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from shared.config.settings import get_settings


logger = logging.getLogger(__name__)


# =========================
# BASE CLIENT
# =========================

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text response."""
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate JSON response."""
        pass


# =========================
# OPENAI CLIENT
# =========================

class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""
    
    def __init__(
        self,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        timeout: int = 60,
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        client_kwargs = {
            "api_key": api_key,
            "timeout": timeout,
        }
        if base_url:
            client_kwargs["base_url"] = base_url
        if organization:
            client_kwargs["organization"] = organization
        
        self.client = OpenAI(**client_kwargs)
    
    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return response.choices[0].message.content
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        
        # Check for empty responses
        if not content or not content.strip():
            raise ValueError("LLM returned empty response")
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}, content: {content[:200]}")
            raise ValueError(f"Invalid JSON response from LLM: {content[:200]}")


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client."""
    
    def __init__(
        self,
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
    
    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.messages.create(
            model=kwargs.get("model", self.model),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return response.content[0].text
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        json_prompt = f"""You must respond with ONLY valid JSON. No other text.

{prompt}

RESPONSE (JSON only):"""
        
        response = self.generate(json_prompt, **kwargs)
        print("=" * 50)
        print("GROQ RAW RESPONSE:")
        print("=" * 50)
        print(f"Type: {type(response)}")
        print(f"Length: {len(response)}")
        print(f"First 500 chars:\n{repr(response[:500])}")
        print(f"Last 200 chars:\n{repr(response[-200:])}")
        print("=" * 50)
    # ========== END DEBUG ==========
        
        # Extract JSON from response
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {response[:200]}")


# =========================
# AZURE OPENAI CLIENT
# =========================

class AzureOpenAIClient(BaseLLMClient):
    """Azure OpenAI API client."""
    
    def __init__(
        self,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_version: str = "2024-02-15-preview",
        timeout: int = 60,
    ):
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            timeout=timeout,
        )
    
    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return response.choices[0].message.content
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        
        # Check for empty responses
        if not content or not content.strip():
            raise ValueError("LLM returned empty response")
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}, content: {content[:200]}")
            raise ValueError(f"Invalid JSON response from LLM: {content[:200]}")


# =========================
# LOCAL LLM CLIENT (Ollama)
# =========================

class LocalLLMClient(BaseLLMClient):
    """Local LLM client (Ollama, LM Studio, vLLM)."""
    
    def __init__(
        self,
        model: str = "llama2",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
    ):
        import requests
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.timeout = timeout
        self.requests = requests
    
    def _call(self, prompt: str, **kwargs) -> Dict[str, Any]:
        response = self.requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": kwargs.get("model", self.model),
                "prompt": prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "stream": False,
            },
            timeout=kwargs.get("timeout", self.timeout),
        )
        response.raise_for_status()
        return response.json()
    
    def generate(self, prompt: str, **kwargs) -> str:
        result = self._call(prompt, **kwargs)
        return result.get("response", "")
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        json_prompt = f"Respond with ONLY valid JSON. No other text.\n\n{prompt}"
        response = self.generate(json_prompt, **kwargs)
        
        # Check for empty responses
        if not response or not response.strip():
            raise ValueError("LLM returned empty response")
        
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}, response: {response[:200]}")
            raise ValueError(f"Invalid JSON response from LLM: {response[:200]}")


# =========================
# GROQ CLIENT
# =========================

class GroqClient(BaseLLMClient):
    """Groq API client (fast inference)."""
    
    def __init__(
        self,
        model: str = "mixtral-8x7b-32768",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Groq package not installed. Run: pip install groq")
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = Groq(api_key=api_key, timeout=timeout)
    
    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return response.choices[0].message.content
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        json_prompt = f"""You must respond with ONLY valid JSON. No other text.

{prompt}

RESPONSE (JSON only):"""
        
        response = self.generate(json_prompt, **kwargs)
        
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {response[:200]}")


# =========================
# FACTORY FUNCTION
# =========================

def get_llm_client(**kwargs) -> BaseLLMClient:
    """
    Get LLM client based on provider from settings or kwargs.
    
    Args:
        **kwargs: Override settings (provider, model, temperature, etc.)
    
    Returns:
        LLM client instance
    
    Examples:
        # Use settings from .env
        client = get_llm_client()
        
        # Override provider
        client = get_llm_client(provider="anthropic")
        
        # Override everything
        client = get_llm_client(
            provider="openai",
            model="gpt-4",
            temperature=0.5,
            api_key="sk-xxx"
        )
    """
    settings = get_settings()
    
    # Get values from kwargs or settings
    provider = kwargs.get("provider", settings.LLM_PROVIDER)
    model = kwargs.get("model", settings.LLM_MODEL)
    temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
    max_tokens = kwargs.get("max_tokens", settings.LLM_MAX_TOKENS)
    timeout = kwargs.get("timeout", getattr(settings, "LLM_REQUEST_TIMEOUT", 60))
    
    logger.info(f"Initializing LLM client: provider={provider}, model={model}")
    
    if provider == "openai":
        return OpenAIClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=kwargs.get("api_key", settings.OPENAI_API_KEY),
            base_url=kwargs.get("base_url", getattr(settings, "OPENAI_BASE_URL", None)),
            organization=kwargs.get("organization", getattr(settings, "OPENAI_ORGANIZATION", None)),
            timeout=timeout,
        )
    
    elif provider == "anthropic":
        return AnthropicClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=kwargs.get("api_key", settings.ANTHROPIC_API_KEY),
            timeout=timeout,
        )
    
    elif provider == "azure":
        return AzureOpenAIClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=kwargs.get("api_key", settings.AZURE_OPENAI_API_KEY),
            endpoint=kwargs.get("endpoint", settings.AZURE_OPENAI_ENDPOINT),
            api_version=kwargs.get("api_version", getattr(settings, "AZURE_OPENAI_API_VERSION", "2024-02-15-preview")),
            timeout=timeout,
        )
    
    elif provider == "local":
        return LocalLLMClient(
            model=kwargs.get("model", getattr(settings, "LOCAL_LLM_MODEL", model)),
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=kwargs.get("base_url", settings.LOCAL_LLM_URL),
            timeout=timeout,
        )
    
    elif provider == "groq":
        return GroqClient(
            model=kwargs.get("model", settings.LLM_MODEL),
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=kwargs.get("api_key", settings.GROQ_API_KEY),
            timeout=timeout,
        )
    
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Supported providers: openai, anthropic, azure, local, groq"
        )


# =========================
# RETRY WRAPPER
# =========================

def with_retry(client: BaseLLMClient, prompt: str, max_retries: int = 3, **kwargs) -> Dict[str, Any]:
    """
    Call LLM with automatic retry on failure.
    """
    settings = get_settings()
    max_retries = max_retries or settings.LLM_MAX_RETRIES
    backoff = settings.LLM_RETRY_BACKOFF
    
    for attempt in range(max_retries):
        try:
            return client.generate_json(prompt, **kwargs)
        except Exception as e:
            logger.warning(f"LLM attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(backoff * (2 ** attempt))
            else:
                raise
    
    raise RuntimeError(f"LLM failed after {max_retries} attempts")