"""
Unified LLM Client for Mises Data Curator Agents.

Provides a consistent interface for multiple LLM providers using LiteLLM.
Compatible with OpenRouter, Ollama, OpenAI, Azure, Anthropic, and more.

Inspired by Data Formulator's client_utils.py pattern.
"""

import os
import logging
from typing import Dict, Any, Optional, Union, List, Generator
from dataclasses import dataclass

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    provider: str  # 'openrouter', 'ollama', 'openai', 'azure', 'anthropic'
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.3
    
    @classmethod
    def from_env(cls) -> 'ModelConfig':
        """Create config from environment variables."""
        provider = os.getenv('LLM_PROVIDER', 'ollama').lower()
        
        if provider == 'openrouter':
            return cls(
                provider='openrouter',
                model=os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet'),
                api_key=os.getenv('OPENROUTER_API_KEY'),
                api_base='https://openrouter.ai/api/v1',
            )
        elif provider == 'ollama':
            return cls(
                provider='ollama',
                model=os.getenv('OLLAMA_MODEL', 'llama3.1'),
                api_base=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
                api_key=os.getenv('OLLAMA_API_KEY', ''),
            )
        elif provider == 'openai':
            return cls(
                provider='openai',
                model=os.getenv('OPENAI_MODEL', 'gpt-4o'),
                api_key=os.getenv('OPENAI_API_KEY'),
            )
        elif provider == 'anthropic':
            return cls(
                provider='anthropic',
                model=os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
                api_key=os.getenv('ANTHROPIC_API_KEY'),
            )
        else:
            # Default to ollama
            return cls(
                provider='ollama',
                model='llama3.1',
                api_base='http://localhost:11434',
            )
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'ModelConfig':
        """Create config from dictionary."""
        return cls(
            provider=config.get('provider', config.get('endpoint', 'ollama')),
            model=config.get('model', 'llama3.1'),
            api_key=config.get('api_key'),
            api_base=config.get('api_base'),
            api_version=config.get('api_version'),
            max_tokens=config.get('max_tokens', 4000),
            temperature=config.get('temperature', 0.3),
        )


class MisesLLMClient:
    """
    Unified LLM client for Mises agents.
    
    Provides a consistent interface similar to Data Formulator's Client class,
    supporting multiple providers through LiteLLM.
    
    Example:
        >>> client = MisesLLMClient.from_env()
        >>> response = client.get_completion([
        ...     {"role": "system", "content": "You are a data analyst."},
        ...     {"role": "user", "content": "Analyze this data..."}
        ... ])
        >>> print(response.choices[0].message.content)
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize the LLM client.
        
        Args:
            config: ModelConfig instance with provider settings.
        """
        self.config = config
        self.model = self._normalize_model_name()
        self.params = self._build_params()
        
        # Suppress verbose logging from LiteLLM
        if LITELLM_AVAILABLE:
            litellm.set_verbose = False
            logging.getLogger('litellm').setLevel(logging.WARNING)
            logging.getLogger('httpx').setLevel(logging.WARNING)
    
    @classmethod
    def from_env(cls) -> 'MisesLLMClient':
        """Create client from environment variables."""
        config = ModelConfig.from_env()
        return cls(config)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MisesLLMClient':
        """Create client from configuration dictionary."""
        config = ModelConfig.from_dict(config_dict)
        return cls(config)
    
    def _normalize_model_name(self) -> str:
        """
        Normalize model name for LiteLLM format.
        
        LiteLLM expects specific prefixes for each provider.
        """
        model = self.config.model
        provider = self.config.provider.lower()
        
        if provider == 'openrouter':
            # OpenRouter uses openrouter/ prefix
            if not model.startswith('openrouter/'):
                return f"openrouter/{model}"
        elif provider == 'ollama':
            if not model.startswith('ollama/'):
                return f"ollama/{model}"
        elif provider == 'anthropic':
            if not model.startswith('anthropic/'):
                return f"anthropic/{model}"
        elif provider == 'azure':
            if not model.startswith('azure/'):
                return f"azure/{model}"
        # OpenAI doesn't need prefix
        
        return model
    
    def _build_params(self) -> Dict[str, Any]:
        """Build parameters for LiteLLM calls."""
        params = {
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
        }
        
        if self.config.api_key:
            params['api_key'] = self.config.api_key
        
        if self.config.api_base:
            params['api_base'] = self.config.api_base
        
        if self.config.api_version:
            params['api_version'] = self.config.api_version
        
        return params
    
    def get_completion(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        Get completion from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            stream: Whether to stream the response.
            **kwargs: Additional parameters to pass to the model.
            
        Returns:
            Response object with choices[].message.content structure.
        """
        if not LITELLM_AVAILABLE:
            raise RuntimeError(
                "LiteLLM not installed. Install with: pip install litellm"
            )
        
        # Merge params with kwargs (kwargs override)
        call_params = {**self.params, **kwargs}
        
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                stream=stream,
                drop_params=True,  # Drop unsupported params for provider
                **call_params
            )
            return response
            
        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            raise
    
    def get_completion_text(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Convenience method to get completion text directly.
        
        Args:
            messages: List of message dicts.
            **kwargs: Additional parameters.
            
        Returns:
            Response text string.
        """
        response = self.get_completion(messages, stream=False, **kwargs)
        return response.choices[0].message.content
    
    def stream_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream completion chunks.
        
        Args:
            messages: List of message dicts.
            **kwargs: Additional parameters.
            
        Yields:
            Text chunks as they arrive.
        """
        response = self.get_completion(messages, stream=True, **kwargs)
        
        for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the LLM connection.
        
        Returns:
            Dict with status and details.
        """
        try:
            response = self.get_completion([
                {"role": "user", "content": "Responde solo: OK"}
            ])
            
            text = response.choices[0].message.content
            return {
                "status": "ok",
                "provider": self.config.provider,
                "model": self.config.model,
                "response": text[:50]
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": self.config.provider,
                "model": self.config.model,
                "error": str(e)
            }


# Convenience function for quick client creation
def get_default_client() -> MisesLLMClient:
    """Get the default LLM client from environment."""
    return MisesLLMClient.from_env()


# Test function
def test_client():
    """Test the LLM client."""
    print("🧪 Testing Mises LLM Client")
    print("=" * 50)
    
    client = get_default_client()
    print(f"Provider: {client.config.provider}")
    print(f"Model: {client.config.model}")
    
    result = client.test_connection()
    if result['status'] == 'ok':
        print(f"✅ Connection OK: {result['response']}")
    else:
        print(f"❌ Connection failed: {result['error']}")
    
    return result


if __name__ == "__main__":
    test_client()
