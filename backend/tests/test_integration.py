"""Integration tests for deployment scenarios.

These tests verify end-to-end flows and deployment scenarios.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vista.config import Config
from vista.security import SecurityManager
from vista.health_check import HealthChecker
from vista.persistence import PersistenceManager
from vista.structured_logging import setup_structured_logging, get_request_id, set_request_id
from vista.metrics import MetricsCollector
from vista.query_engine import QueryEngine
from vista.models import RetrievedChunk, QueryResponse


class TestConfigurationIntegration:
    """Integration tests for configuration management."""
    
    def test_config_from_env_and_validation(self, monkeypatch):
        """Test loading config from environment and validating it."""
        # Set environment variables
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("PORT", "8000")
        monkeypatch.setenv("LOG_LEVEL", "info")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test_key_1234567890")
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.com,https://app.example.com")
        monkeypatch.setenv("CHUNK_SIZE", "1000")
        monkeypatch.setenv("CHUNK_OVERLAP", "100")
        
        # Load config
        config = Config.from_env()
        
        # Verify all values loaded correctly
        assert config.environment == "production"
        assert config.port == 8000
        assert config.log_level == "info"
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.openai_api_key == "sk-test_key_1234567890"
        assert len(config.allowed_origins) == 2
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 100
        
        # Validate should pass
        config.validate()


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    def test_cors_validation_with_security_manager(self):
        """Test CORS validation in security manager."""
        allowed_origins = ["https://example.com", "https://app.example.com"]
        manager = SecurityManager(allowed_origins)
        
        # Test allowed origins
        assert manager.validate_origin("https://example.com") is True
        assert manager.validate_origin("https://app.example.com") is True
        
        # Test rejected origins
        assert manager.validate_origin("https://malicious.com") is False
        assert manager.validate_origin("http://example.com") is False
        assert manager.validate_origin(None) is False
    
    def test_error_sanitization_in_security_manager(self):
        """Test error sanitization in security manager."""
        manager = SecurityManager([])
        
        # Test API key sanitization
        error_with_key = Exception("Failed with API key sk-proj-1234567890abcdefghijklmnopqrstuvwxyz")
        sanitized = manager.sanitize_error_message(error_with_key)
        
        assert "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz" not in sanitized
        assert "[REDACTED" in sanitized or "Failed" in sanitized


class TestHealthCheckIntegration:
    """Integration tests for health checks."""
    
    def test_health_check_with_all_components(self):
        """Test health check with all components."""
        mock_query_engine = Mock()
        mock_vector_store = Mock()
        
        checker = HealthChecker(mock_query_engine, mock_vector_store)
        
        # Get health status
        health_status = checker.check_health()
        
        # Verify response structure
        assert health_status.status in ["healthy", "degraded", "unhealthy"]
        assert health_status.timestamp is not None
        assert isinstance(health_status.components, dict)
        
        # Should have at least API component
        assert len(health_status.components) > 0


class TestPersistenceIntegration:
    """Integration tests for database persistence."""
    
    def test_persistence_directory_management(self):
        """Test persistence directory creation and management."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_dir = Path(tmpdir) / "chroma_db"
            
            manager = PersistenceManager(str(persist_dir))
            
            # Ensure directory is created
            manager.ensure_persistence_directory()
            
            assert persist_dir.exists()
            assert persist_dir.is_dir()
    
    def test_backup_and_restore_flow(self):
        """Test backup and restore workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_dir = Path(tmpdir) / "chroma_db"
            db_dir.mkdir()
            
            # Create test data
            test_file = db_dir / "test.bin"
            test_file.write_bytes(b"test data")
            
            manager = PersistenceManager(str(db_dir))
            
            # Create backup
            backup_dir = Path(tmpdir) / "backup"
            backup_dir.mkdir()
            manager.backup_database(str(backup_dir))
            
            # Verify backup exists
            assert (backup_dir / "test.bin").exists()
            
            # Clear original
            shutil.rmtree(db_dir)
            db_dir.mkdir()
            
            # Restore
            manager.restore_database(str(backup_dir))
            
            # Verify restoration
            assert (db_dir / "test.bin").exists()
            assert (db_dir / "test.bin").read_bytes() == b"test data"


class TestLoggingIntegration:
    """Integration tests for structured logging."""
    
    def test_request_id_propagation_flow(self):
        """Test request ID propagation through logging."""
        # Set request ID
        request_id = "test-request-123"
        set_request_id(request_id)
        
        # Get request ID
        retrieved_id = get_request_id()
        
        # Should match
        assert retrieved_id == request_id
    
    def test_structured_logging_setup(self):
        """Test structured logging setup."""
        # Setup logging
        setup_structured_logging("info")
        
        # Get logger
        import logging
        logger = logging.getLogger("test")
        
        # Should return a logger
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')


class TestMetricsIntegration:
    """Integration tests for metrics collection."""
    
    def test_metrics_collection_flow(self):
        """Test metrics collection workflow."""
        collector = MetricsCollector()
        
        # Record some requests
        for i in range(10):
            endpoint = f"/api/endpoint{i % 3}"
            duration = 100 + (i * 10)
            status_code = 200 if i % 2 == 0 else 500
            error = "ServerError" if i % 2 == 1 else None
            
            collector.record_request(endpoint, duration, status_code, error)
        
        # Get metrics
        metrics = collector.get_metrics()
        
        # Verify metrics
        assert metrics.total_requests == 10
        assert metrics.total_errors == 5
        assert metrics.error_rate == 0.5
        assert metrics.average_response_time_ms > 0
        assert len(metrics.requests_by_endpoint) == 3
        assert metrics.errors_by_type.get("ServerError", 0) == 5


class TestQueryEngineIntegration:
    """Integration tests for query engine."""
    
    def test_query_with_context_flow(self):
        """Test query processing with context."""
        mock_vector_store = Mock()
        mock_embedding_gen = Mock()
        mock_llm_client = Mock()
        
        # Setup mocks
        query_embedding = [0.1, 0.2, 0.3]
        retrieved_chunks = [
            RetrievedChunk(
                text="I have 5 years of experience.",
                metadata={"category": "experience", "filename": "work.txt"},
                similarity_score=0.9
            )
        ]
        
        mock_embedding_gen.generate_embedding.return_value = query_embedding
        mock_vector_store.query.return_value = retrieved_chunks
        mock_llm_client.generate_response.return_value = "Based on the context, you have 5 years of experience."
        
        # Create query engine
        query_engine = QueryEngine(
            vector_store=mock_vector_store,
            embedding_gen=mock_embedding_gen,
            llm_client=mock_llm_client,
            max_context_tokens=1000
        )
        
        # Execute query
        result = query_engine.query("What is my experience?", n_results=5)
        
        # Verify result
        assert isinstance(result, QueryResponse)
        assert result.query == "What is my experience?"
        assert len(result.sources) > 0
        assert "5 years" in result.answer
    
    def test_query_without_context_flow(self):
        """Test query processing without context."""
        mock_vector_store = Mock()
        mock_embedding_gen = Mock()
        mock_llm_client = Mock()
        
        # Setup mocks - no results
        query_embedding = [0.1, 0.2, 0.3]
        mock_embedding_gen.generate_embedding.return_value = query_embedding
        mock_vector_store.query.return_value = []
        mock_llm_client.generate_response.return_value = "I don't have information about that."
        
        # Create query engine
        query_engine = QueryEngine(
            vector_store=mock_vector_store,
            embedding_gen=mock_embedding_gen,
            llm_client=mock_llm_client,
            max_context_tokens=1000
        )
        
        # Execute query
        result = query_engine.query("What is my favorite color?")
        
        # Verify result
        assert isinstance(result, QueryResponse)
        assert result.query == "What is my favorite color?"
        assert len(result.sources) == 0


class TestDeploymentScenarios:
    """Integration tests for deployment scenarios."""
    
    def test_production_configuration_scenario(self, monkeypatch):
        """Test production configuration scenario."""
        # Set production environment variables
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "AIzatest_key_1234567890")
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.com")
        
        # Load config
        config = Config.from_env()
        
        # Validate for production
        config.validate()
        
        # Verify production settings
        assert config.environment == "production"
        assert config.llm_provider == "gemini"
        assert len(config.allowed_origins) > 0
    
    def test_error_handling_scenario(self):
        """Test error handling in deployment scenario."""
        manager = SecurityManager([])
        
        # Simulate error with sensitive data
        error_msg = "Database connection failed: postgresql://user:password@localhost:5432/db"
        error = Exception(error_msg)
        
        # Sanitize error
        sanitized = manager.sanitize_error_message(error)
        
        # Verify sensitive data is removed
        assert "password" not in sanitized or "[REDACTED]" in sanitized
        
        # Verify useful context is preserved
        assert "Database connection failed" in sanitized
    
    def test_monitoring_scenario(self):
        """Test monitoring scenario."""
        # Create health checker
        mock_query_engine = Mock()
        mock_vector_store = Mock()
        checker = HealthChecker(mock_query_engine, mock_vector_store)
        
        # Create metrics collector
        collector = MetricsCollector()
        
        # Simulate requests
        for i in range(5):
            collector.record_request(f"/api/query", 100 + i * 10, 200)
        
        # Get health and metrics
        health = checker.check_health()
        metrics = collector.get_metrics()
        
        # Verify monitoring data
        assert health.status in ["healthy", "degraded", "unhealthy"]
        assert metrics.total_requests == 5
        assert metrics.total_errors == 0
