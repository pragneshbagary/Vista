"""Tests for ASGI server configuration."""

import pytest
import os
from vista.asgi_config import ASGIConfig


class TestASGIConfig:
    """Tests for ASGIConfig class."""
    
    def test_default_config(self):
        """Test default ASGI configuration."""
        config = ASGIConfig()
        
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.workers == 4
        assert config.timeout == 120
        assert config.graceful_timeout == 30
        assert config.keepalive == 5
    
    def test_config_from_env(self, monkeypatch):
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("HOST", "127.0.0.1")
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("WORKERS", "8")
        monkeypatch.setenv("TIMEOUT", "180")
        monkeypatch.setenv("GRACEFUL_TIMEOUT", "45")
        
        config = ASGIConfig.from_env()
        
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.workers == 8
        assert config.timeout == 180
        assert config.graceful_timeout == 45
    
    def test_config_validation_invalid_workers(self):
        """Test validation fails with invalid workers."""
        config = ASGIConfig(workers=0)
        
        with pytest.raises(ValueError, match="WORKERS must be at least 1"):
            config.validate()
    
    def test_config_validation_invalid_timeout(self):
        """Test validation fails with invalid timeout."""
        config = ASGIConfig(timeout=0)
        
        with pytest.raises(ValueError, match="TIMEOUT must be at least 1"):
            config.validate()
    
    def test_config_validation_graceful_timeout_exceeds_timeout(self):
        """Test validation fails when graceful timeout exceeds timeout."""
        config = ASGIConfig(timeout=30, graceful_timeout=60)
        
        with pytest.raises(ValueError, match="GRACEFUL_TIMEOUT.*must be less than TIMEOUT"):
            config.validate()
    
    def test_config_validation_invalid_port(self):
        """Test validation fails with invalid port."""
        config = ASGIConfig(port=0)
        
        with pytest.raises(ValueError, match="PORT must be between 1 and 65535"):
            config.validate()
    
    def test_config_validation_invalid_port_too_high(self):
        """Test validation fails with port too high."""
        config = ASGIConfig(port=70000)
        
        with pytest.raises(ValueError, match="PORT must be between 1 and 65535"):
            config.validate()
    
    def test_to_gunicorn_config(self):
        """Test conversion to Gunicorn configuration."""
        config = ASGIConfig(
            host="127.0.0.1",
            port=9000,
            workers=8,
            timeout=180
        )
        
        gunicorn_config = config.to_gunicorn_config()
        
        assert gunicorn_config["bind"] == "127.0.0.1:9000"
        assert gunicorn_config["workers"] == 8
        assert gunicorn_config["timeout"] == 180
        assert gunicorn_config["worker_class"] == "uvicorn.workers.UvicornWorker"
    
    def test_to_uvicorn_config(self):
        """Test conversion to Uvicorn configuration."""
        config = ASGIConfig(
            host="127.0.0.1",
            port=9000,
            keepalive=10
        )
        
        uvicorn_config = config.to_uvicorn_config()
        
        assert uvicorn_config["host"] == "127.0.0.1"
        assert uvicorn_config["port"] == 9000
        assert uvicorn_config["timeout_keep_alive"] == 10
    
    def test_get_recommended_workers(self):
        """Test getting recommended worker count."""
        config = ASGIConfig()
        recommended = config.get_recommended_workers()
        
        # Should be at least 1
        assert recommended >= 1
        # Should be reasonable (not more than 32 for typical systems)
        assert recommended <= 32
    
    def test_config_from_env_invalid_workers(self, monkeypatch):
        """Test loading config with invalid workers value."""
        monkeypatch.setenv("WORKERS", "invalid")
        
        with pytest.raises(ValueError, match="Invalid ASGI configuration"):
            ASGIConfig.from_env()
    
    def test_config_from_env_invalid_port(self, monkeypatch):
        """Test loading config with invalid port value."""
        monkeypatch.setenv("PORT", "invalid")
        
        with pytest.raises(ValueError, match="Invalid ASGI configuration"):
            ASGIConfig.from_env()
    
    def test_config_validation_invalid_worker_connections(self):
        """Test validation fails with invalid worker connections."""
        config = ASGIConfig(worker_connections=0)
        
        with pytest.raises(ValueError, match="WORKER_CONNECTIONS must be at least 1"):
            config.validate()
    
    def test_config_validation_invalid_backlog(self):
        """Test validation fails with invalid backlog."""
        config = ASGIConfig(backlog=0)
        
        with pytest.raises(ValueError, match="BACKLOG must be at least 1"):
            config.validate()
    
    def test_config_validation_negative_max_requests(self):
        """Test validation allows zero max_requests."""
        config = ASGIConfig(max_requests=0)
        
        # Should not raise - 0 is valid (means unlimited)
        config.validate()
    
    def test_config_validation_negative_keepalive(self):
        """Test validation allows zero keepalive."""
        config = ASGIConfig(keepalive=0)
        
        # Should not raise - 0 is valid
        config.validate()
