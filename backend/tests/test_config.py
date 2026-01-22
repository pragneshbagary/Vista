"""Tests for configuration management."""

import pytest
import os
from vista.config import Config


def test_config_defaults():
    """Test that Config has sensible defaults."""
    # Set required parameters for validation
    config = Config(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        openai_api_key="sk-test_key_1234567890"
    )
    
    assert config.chunk_size == 500
    assert config.chunk_overlap == 50
    assert config.embedding_model == "all-MiniLM-L6-v2"
    assert config.llm_model == "gpt-4o-mini"
    assert config.top_k_results == 5
    assert config.data_directory == "./data"
    assert config.persist_directory == "./chroma_db"


def test_config_validation_missing_api_key():
    """Test that validation fails when API key is missing."""
    with pytest.raises(ValueError) as exc_info:
        config = Config(
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            openai_api_key=None
        )
        config.validate()
    
    assert "OPENAI_API_KEY is required" in str(exc_info.value)


def test_config_validation_invalid_chunk_size():
    """Test that validation fails for invalid chunk size."""
    with pytest.raises(ValueError) as exc_info:
        config = Config(
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            openai_api_key="sk-test_key_1234567890",
            chunk_size=0
        )
        config.validate()
    
    assert "CHUNK_SIZE must be positive" in str(exc_info.value)


def test_config_validation_invalid_overlap():
    """Test that validation fails when overlap >= chunk_size."""
    with pytest.raises(ValueError) as exc_info:
        config = Config(
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            openai_api_key="sk-test_key_1234567890",
            chunk_size=100,
            chunk_overlap=100
        )
        config.validate()
    
    assert "CHUNK_OVERLAP" in str(exc_info.value)
    assert "must be less than CHUNK_SIZE" in str(exc_info.value)


def test_config_from_env(monkeypatch):
    """Test loading configuration from environment variables."""
    # Set environment variables
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test_api_key_1234567890")
    monkeypatch.setenv("CHUNK_SIZE", "1000")
    monkeypatch.setenv("CHUNK_OVERLAP", "100")
    monkeypatch.setenv("EMBEDDING_MODEL", "custom-model")
    monkeypatch.setenv("TOP_K_RESULTS", "10")
    
    config = Config.from_env()
    
    assert config.openai_api_key == "sk-test_api_key_1234567890"
    assert config.chunk_size == 1000
    assert config.chunk_overlap == 100
    assert config.embedding_model == "custom-model"
    assert config.llm_model == "gpt-4"
    assert config.top_k_results == 10


def test_config_from_env_with_defaults(monkeypatch):
    """Test that from_env uses defaults when env vars not set."""
    # Only set required API key and provider
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test_api_key_1234567890")
    
    config = Config.from_env()
    
    assert config.openai_api_key == "sk-test_api_key_1234567890"
    assert config.chunk_size == 500  # default
    assert config.chunk_overlap == 50  # default
