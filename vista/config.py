# """Configuration management for the Vista."""

# from dataclasses import dataclass, field
# from pathlib import Path
# from typing import Optional
# import os
# from dotenv import load_dotenv


# @dataclass
# class Config:
#     """Configuration for the Vista.
    
#     Attributes:
#         chunk_size: Maximum size of text chunks in characters
#         chunk_overlap: Number of overlapping characters between consecutive chunks
#         embedding_model: Name of the sentence-transformers model to use
#         llm_model: Name of the LLM model to use (OpenAI)
#         n_retrieval_results: Number of similar chunks to retrieve for each query
#         data_directory: Path to directory containing personal data files
#         persist_directory: Path to directory for ChromaDB persistence
#         openai_api_key: OpenAI API key for LLM access
#         max_context_tokens: Maximum number of tokens for context sent to LLM
#         max_response_tokens: Maximum number of tokens for LLM response
#         max_retries: Maximum number of retry attempts for API calls
#     """
    
#     # Chunking parameters
#     chunk_size: int = 500
#     chunk_overlap: int = 50
    
#     # Model parameters
#     embedding_model: str = "all-MiniLM-L6-v2"

#     llm_provider: str  # 'openai' or 'gemini'
#     openai_api_key: Optional[str] = None
#     gemini_api_key: Optional[str] = None

#     llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
#     if llm_provider == "openai":
#         default_model = "gpt-5-mini-2025-08-07"
#     elif llm_provider == "gemini":
#         default_model = "gemini-2.5-flash"
#     else:
#         raise ValueError(f"Unsupported LLM provider: {llm_provider}")
    
#     llm_model: str = default_model
    
#     # Retrieval parameters
#     n_retrieval_results: int = 5
    
#     # Directory paths
#     data_directory: str = "./data"
#     persist_directory: str = "./chroma_db"
    
#     # Token limits
#     max_context_tokens: int = 3000
#     max_response_tokens: int = 500
    
#     # Retry configuration
#     max_retries: int = 3
    
#     def __post_init__(self):
#         """Validate configuration after initialization."""
#         self.validate()
    
#     def validate(self) -> None:
#         """Validate that all required configuration parameters are present and valid.
        
#         Raises:
#             ValueError: If required parameters are missing or invalid
#         """
#         errors = []
        
#         # Validate required parameters
#         if self.llm_provider == "openai" and not self.openai_api_key:
#             raise ValueError(
#                 "OPENAI_API_KEY environment variable is required when using OpenAI provider"
#             )
#         elif self.llm_provider == "gemini" and not self.gemini_api_key:
#             raise ValueError(
#                 "GEMINI_API_KEY environment variable is required when using Gemini provider"
#             )
#         # Validate numeric parameters
#         if self.chunk_size <= 0:
#             errors.append(f"chunk_size must be positive, got {self.chunk_size}")
        
#         if self.chunk_overlap < 0:
#             errors.append(f"chunk_overlap must be non-negative, got {self.chunk_overlap}")
        
#         if self.chunk_overlap >= self.chunk_size:
#             errors.append(f"chunk_overlap ({self.chunk_overlap}) must be less than chunk_size ({self.chunk_size})")
        
#         if self.n_retrieval_results <= 0:
#             errors.append(f"n_retrieval_results must be positive, got {self.n_retrieval_results}")
        
#         if self.max_context_tokens <= 0:
#             errors.append(f"max_context_tokens must be positive, got {self.max_context_tokens}")
        
#         if self.max_response_tokens <= 0:
#             errors.append(f"max_response_tokens must be positive, got {self.max_response_tokens}")
        
#         if self.max_retries < 0:
#             errors.append(f"max_retries must be non-negative, got {self.max_retries}")
        
#         # Validate paths
#         if not self.data_directory:
#             errors.append("data_directory is required")
        
#         if not self.persist_directory:
#             errors.append("persist_directory is required")
        
#         if errors:
#             raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors))
    
#     @classmethod
#     def from_env(cls) -> 'Config':
#         """Load configuration from environment variables.
        
#         Loads .env file if present, then reads configuration from environment variables.
#         Falls back to default values for optional parameters.
        
#         Returns:
#             Config instance with values from environment
#         """
#         # Load .env file if it exists
#         load_dotenv()
        
#         return cls(
#             chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
#             chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
#             embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
#             llm_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
#             n_retrieval_results=int(os.getenv("N_RETRIEVAL_RESULTS", "5")),
#             data_directory=os.getenv("DATA_DIRECTORY", "./data"),
#             persist_directory=os.getenv("PERSIST_DIRECTORY", "./chroma_db"),
#             openai_api_key=os.getenv("OPENAI_API_KEY"),
#             gemini_api_key=os.getenv("GEMINI_API_KEY"),
#             max_context_tokens=int(os.getenv("MAX_CONTEXT_TOKENS", "3000")),
#             max_response_tokens=int(os.getenv("MAX_RESPONSE_TOKENS", "500")),
#             max_retries=int(os.getenv("MAX_RETRIES", "3")),
#         )




# ========================================================================================================================================================================================================================================================
# config.py
"""Configuration management for the Vista."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

@dataclass
class Config:
    """System configuration loaded from environment variables."""
    
    # LLM Configuration
    llm_provider: str  # 'openai' or 'gemini'
    llm_model: str
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
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
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.
        
        Returns:
            Config instance with values from environment
            
        Raises:
            ValueError: If required environment variables are missing
        """

        load_dotenv()
        # Get LLM provider (default to gemini)
        llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        
        # Load API keys
        openai_api_key = os.getenv("OPENAI_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Validate that the required API key exists for the selected provider
        if llm_provider == "openai" and not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required when using OpenAI provider"
            )
        elif llm_provider == "gemini" and not gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required when using Gemini provider"
            )
        
        # Get model name with provider-specific defaults
        if llm_provider == "openai":
            default_model = "gpt-4o-mini"
        elif llm_provider == "gemini":
            default_model = "gemini-2.5-flash"
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        
        llm_model = os.getenv("LLM_MODEL", default_model)
        
        return cls(
            llm_provider=llm_provider,
            llm_model=llm_model,
            openai_api_key=openai_api_key,
            gemini_api_key=gemini_api_key,
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            data_directory=os.getenv("DATA_DIRECTORY", "./data"),
            persist_directory=os.getenv("PERSIST_DIRECTORY", "./chroma_db"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
            max_context_tokens=int(os.getenv("MAX_CONTEXT_TOKENS", "3000")),
            max_response_tokens=int(os.getenv("MAX_RESPONSE_TOKENS", "500")),
            top_k_results=int(os.getenv("TOP_K_RESULTS", "5"))
        )
    
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