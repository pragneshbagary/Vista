"""Configuration management for the Vista."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

@dataclass
class Config:
    """System configuration loaded from environment variables."""
    
    # LLM Configuration (required fields first)
    llm_provider: str  # 'openai' or 'gemini'
    llm_model: str
    
    # Environment Configuration
    environment: str = "development"
    port: int = 8000
    log_level: str = "info"
    
    # API Keys
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
    # Security Configuration
    allowed_origins: Optional[List[str]] = None
    
    # Embedding Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Directory Configuration
    data_directory: str = "./data"
    persist_directory: str = "./chroma_db"
    
    # Chunking Configuration
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Query Configuration
    max_context_tokens: int = 3000
    max_response_tokens: int = 500
    top_k_results: int = 5
    
    # Retry Configuration
    max_retries: int = 3
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.allowed_origins is None:
            self.allowed_origins = []
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.
        
        Returns:
            Config instance with values from environment
            
        Raises:
            ValueError: If required environment variables are missing or invalid
        """
        load_dotenv()
        
        # Get environment mode
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        # Get port
        try:
            port = int(os.getenv("PORT", "8000"))
        except ValueError:
            raise ValueError("PORT must be a valid integer")
        
        # Get log level
        log_level = os.getenv("LOG_LEVEL", "info").lower()
        
        # Get LLM provider (default to gemini)
        llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        
        # Load API keys
        openai_api_key = os.getenv("OPENAI_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Get model name with provider-specific defaults
        if llm_provider == "openai":
            default_model = "gpt-4o-mini"
        elif llm_provider == "gemini":
            default_model = "gemini-2.5-flash"
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}. Must be 'openai' or 'gemini'")
        
        llm_model = os.getenv("LLM_MODEL", default_model)
        
        # Get CORS origins
        allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
        allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]
        
        config = cls(
            environment=environment,
            port=port,
            log_level=log_level,
            llm_provider=llm_provider,
            llm_model=llm_model,
            openai_api_key=openai_api_key,
            gemini_api_key=gemini_api_key,
            allowed_origins=allowed_origins,
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            data_directory=os.getenv("DATA_DIRECTORY", "./data"),
            persist_directory=os.getenv("PERSIST_DIRECTORY", "./chroma_db"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
            max_context_tokens=int(os.getenv("MAX_CONTEXT_TOKENS", "3000")),
            max_response_tokens=int(os.getenv("MAX_RESPONSE_TOKENS", "500")),
            top_k_results=int(os.getenv("TOP_K_RESULTS", "5")),
            max_retries=int(os.getenv("MAX_RETRIES", "3"))
        )
        
        # Validate configuration
        config.validate()
        
        return config
    
    def validate(self) -> None:
        """Validate configuration for production readiness.
        
        Raises:
            ValueError: If configuration is invalid
        """
        errors = []
        
        # Validate environment
        if self.environment not in ["development", "staging", "production"]:
            errors.append(f"ENVIRONMENT must be 'development', 'staging', or 'production', got '{self.environment}'")
        
        # Validate port
        if not (1 <= self.port <= 65535):
            errors.append(f"PORT must be between 1 and 65535, got {self.port}")
        
        # Validate log level
        valid_log_levels = ["debug", "info", "warning", "error", "critical"]
        if self.log_level not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of {valid_log_levels}, got '{self.log_level}'")
        
        # Validate LLM provider
        if self.llm_provider not in ["openai", "gemini"]:
            errors.append(f"LLM_PROVIDER must be 'openai' or 'gemini', got '{self.llm_provider}'")
        
        # Validate API keys for selected provider
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                errors.append("OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'")
            elif not self._is_valid_openai_key(self.openai_api_key):
                errors.append("OPENAI_API_KEY format is invalid (should start with 'sk-')")
        elif self.llm_provider == "gemini":
            if not self.gemini_api_key:
                errors.append("GEMINI_API_KEY is required when LLM_PROVIDER is 'gemini'")
            elif not self._is_valid_gemini_key(self.gemini_api_key):
                errors.append("GEMINI_API_KEY format is invalid (should start with 'AIza')")
        
        # Validate CORS origins in production
        if self.environment == "production":
            if not self.allowed_origins:
                errors.append("ALLOWED_ORIGINS is required in production mode")
            else:
                for origin in self.allowed_origins:
                    if not self._is_valid_url(origin):
                        errors.append(f"ALLOWED_ORIGINS contains invalid URL: '{origin}'")
                    if self.environment == "production" and not origin.startswith("https://"):
                        errors.append(f"ALLOWED_ORIGINS must use HTTPS in production: '{origin}'")
        
        # Validate numeric parameters
        if self.chunk_size <= 0:
            errors.append(f"CHUNK_SIZE must be positive, got {self.chunk_size}")
        
        if self.chunk_overlap < 0:
            errors.append(f"CHUNK_OVERLAP must be non-negative, got {self.chunk_overlap}")
        
        if self.chunk_overlap >= self.chunk_size:
            errors.append(f"CHUNK_OVERLAP ({self.chunk_overlap}) must be less than CHUNK_SIZE ({self.chunk_size})")
        
        if self.max_context_tokens <= 0:
            errors.append(f"MAX_CONTEXT_TOKENS must be positive, got {self.max_context_tokens}")
        
        if self.max_response_tokens <= 0:
            errors.append(f"MAX_RESPONSE_TOKENS must be positive, got {self.max_response_tokens}")
        
        if self.top_k_results <= 0:
            errors.append(f"TOP_K_RESULTS must be positive, got {self.top_k_results}")
        
        if self.max_retries < 0:
            errors.append(f"MAX_RETRIES must be non-negative, got {self.max_retries}")
        
        # Validate paths
        if not self.data_directory:
            errors.append("DATA_DIRECTORY is required")
        
        if not self.persist_directory:
            errors.append("PERSIST_DIRECTORY is required")
        
        if errors:
            error_message = "Configuration validation failed:\n"
            for error in errors:
                error_message += f"  - {error}\n"
            raise ValueError(error_message)
    
    @staticmethod
    def _is_valid_openai_key(key: str) -> bool:
        """Check if OpenAI API key format is valid."""
        return key.startswith("sk-") and len(key) > 10
    
    @staticmethod
    def _is_valid_gemini_key(key: str) -> bool:
        """Check if Gemini API key format is valid."""
        return key.startswith("AIza") and len(key) > 10
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if URL format is valid."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP address
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$',
            re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    def get_api_key(self) -> str:
        """Get the API key for the configured LLM provider.
        
        Returns:
            API key for the current provider
            
        Raises:
            ValueError: If API key is not set
        """
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            return self.openai_api_key
        elif self.llm_provider == "gemini":
            if not self.gemini_api_key:
                raise ValueError("Gemini API key not configured")
            return self.gemini_api_key
        else:
            raise ValueError(f"Unknown provider: {self.llm_provider}")
