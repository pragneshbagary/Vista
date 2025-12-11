# llm_factory.py
"""Factory for creating LLM client instances."""

import logging
from typing import Optional
from vista.llm_base import BaseLLMClient
from vista.llm_openai import OpenAILLMClient
from vista.llm_gemini import GeminiLLMClient

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory class for creating LLM client instances."""
    
    # Registry of available LLM providers
    _providers = {
        'openai': OpenAILLMClient,
        'gemini': GeminiLLMClient,
    }
    
    @classmethod
    def create_llm_client(
        cls,
        provider: str,
        api_key: str,
        model: Optional[str] = None
    ) -> BaseLLMClient:
        """Create an LLM client based on the provider name.
        
        Args:
            provider: Name of the LLM provider ('openai', 'gemini')
            api_key: API key for the provider
            model: Optional model name (uses provider default if not specified)
            
        Returns:
            Initialized LLM client instance
            
        Raises:
            ValueError: If provider is not supported
        """
        provider_lower = provider.lower()
        
        if provider_lower not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unsupported LLM provider: '{provider}'. "
                f"Available providers: {available}"
            )
        
        client_class = cls._providers[provider_lower]
        
        # Create client with or without model specification
        if model:
            client = client_class(api_key=api_key, model=model)
        else:
            client = client_class(api_key=api_key)
        
        logger.info(f"Created {provider} LLM client with model: {client.model_name}")
        return client
    
    @classmethod
    def register_provider(cls, name: str, client_class: type) -> None:
        """Register a new LLM provider.
        
        Args:
            name: Provider name
            client_class: LLM client class (must inherit from BaseLLMClient)
        """
        if not issubclass(client_class, BaseLLMClient):
            raise TypeError(
                f"Client class must inherit from BaseLLMClient, "
                f"got {client_class.__name__}"
            )
        
        cls._providers[name.lower()] = client_class
        logger.info(f"Registered new LLM provider: {name}")
    
    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of available provider names.
        
        Returns:
            List of registered provider names
        """
        return list(cls._providers.keys())