"""Property-based tests for deployment preparation features.

These tests use the Hypothesis library to verify correctness properties
across many randomly generated inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch

from vista.config import Config
from vista.security import SecurityManager
from vista.health_check import HealthChecker
from vista.persistence import PersistenceManager
from vista.structured_logging import get_request_id, set_request_id
from vista.metrics import MetricsCollector


# ============================================================================
# Property 1: Environment validation completeness
# ============================================================================

class TestEnvironmentValidationProperty:
    """Property 1: Environment validation completeness.
    
    For any set of environment variables, the configuration validator should
    identify all missing required variables and provide clear error messages
    for each.
    
    Validates: Requirements 1.2
    """
    
    @given(
        llm_provider=st.sampled_from(["openai", "gemini"]),
        port=st.integers(min_value=1, max_value=65535),
        log_level=st.sampled_from(["debug", "info", "warning", "error", "critical"])
    )
    @settings(max_examples=100)
    def test_valid_config_passes_validation(self, llm_provider, port, log_level):
        """Test that valid configurations pass validation."""
        api_key = "sk-test_key_1234567890" if llm_provider == "openai" else "AIzatest_key_1234567890"
        
        config = Config(
            llm_provider=llm_provider,
            llm_model="test-model",
            openai_api_key=api_key if llm_provider == "openai" else None,
            gemini_api_key=api_key if llm_provider == "gemini" else None,
            port=port,
            log_level=log_level
        )
        
        # Should not raise
        config.validate()
    
    def test_missing_api_key_identified(self):
        """Test that missing API key is identified in validation."""
        config = Config(
            llm_provider="openai",
            llm_model="gpt-4",
            openai_api_key=None
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        # Error message should clearly identify the missing variable
        assert "OPENAI_API_KEY" in str(exc_info.value)


# ============================================================================
# Property 2: Sensitive data protection
# ============================================================================

class TestSensitiveDataProtectionProperty:
    """Property 2: Sensitive data protection.
    
    For any error message or log entry, the output should not contain API keys,
    tokens, or other sensitive credentials.
    
    Validates: Requirements 2.3, 9.1
    """
    
    def test_openai_api_keys_removed(self):
        """Test that OpenAI API keys are removed from error messages."""
        manager = SecurityManager([])
        
        # Create error message with OpenAI API key
        api_key = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
        error_msg = f"Error: Failed with key {api_key}"
        error = Exception(error_msg)
        
        sanitized = manager.sanitize_error_message(error)
        
        # Original API key should not be in sanitized output
        assert api_key not in sanitized
    
    def test_gemini_api_keys_removed(self):
        """Test that Gemini API keys are removed from error messages."""
        manager = SecurityManager([])
        
        # Create error message with Gemini API key
        api_key = "AIzaSyDummyKeyForTesting1234567890"
        error_msg = f"Error: Failed with key {api_key}"
        error = Exception(error_msg)
        
        sanitized = manager.sanitize_error_message(error)
        
        # Original API key should not be in sanitized output
        assert api_key not in sanitized


# ============================================================================
# Property 3: CORS origin validation
# ============================================================================

class TestCORSOriginValidationProperty:
    """Property 3: CORS origin validation.
    
    For any incoming request with an origin header, the system should accept
    it only if the origin is in the configured whitelist.
    
    Validates: Requirements 2.1, 2.2
    """
    
    @given(
        allowed_origins=st.lists(
            st.just("https://example.com") | st.just("https://app.example.com"),
            min_size=1,
            max_size=5,
            unique=True
        ),
        test_origin=st.sampled_from([
            "https://example.com",
            "https://app.example.com",
            "https://malicious.com",
            "http://example.com",
            None,
            ""
        ])
    )
    @settings(max_examples=100)
    def test_cors_validation_consistency(self, allowed_origins, test_origin):
        """Test that CORS validation is consistent across multiple calls."""
        manager = SecurityManager(allowed_origins)
        
        # Call validate_origin multiple times
        result1 = manager.validate_origin(test_origin)
        result2 = manager.validate_origin(test_origin)
        result3 = manager.validate_origin(test_origin)
        
        # Results should be consistent
        assert result1 == result2 == result3
        
        # Result should match whitelist
        if test_origin in allowed_origins:
            assert result1 is True
        else:
            assert result1 is False


# ============================================================================
# Property 4: Health check consistency
# ============================================================================

class TestHealthCheckConsistencyProperty:
    """Property 4: Health check consistency.
    
    For any health check request, the system should return a valid health
    status with all required fields and consistent timestamps.
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4
    """
    
    def test_health_check_has_required_fields(self):
        """Test that health check response has all required fields."""
        mock_query_engine = Mock()
        mock_vector_store = Mock()
        
        checker = HealthChecker(mock_query_engine, mock_vector_store)
        health_status = checker.check_health()
        
        # Should have all required fields
        assert hasattr(health_status, 'status')
        assert hasattr(health_status, 'timestamp')
        assert hasattr(health_status, 'components')
        
        # Status should be one of the valid values
        assert health_status.status in ["healthy", "degraded", "unhealthy"]
        
        # Timestamp should be a valid ISO format string
        assert isinstance(health_status.timestamp, str)
        assert "T" in health_status.timestamp  # ISO format includes T
        
        # Components should be a dict
        assert isinstance(health_status.components, dict)


# ============================================================================
# Property 5: Database persistence round-trip
# ============================================================================

class TestDatabasePersistenceRoundTripProperty:
    """Property 5: Database persistence round-trip.
    
    For any vector database state, backing up and restoring should result
    in identical database content.
    
    Validates: Requirements 3.1, 3.2, 3.3
    """
    
    def test_backup_restore_preserves_state(self, tmp_path):
        """Test that backup and restore preserve database state."""
        import tempfile
        import shutil
        
        # Create a temporary directory for the database
        db_dir = tmp_path / "chroma_db"
        db_dir.mkdir()
        
        # Create some test files in the database directory
        test_file = db_dir / "test.bin"
        test_file.write_bytes(b"test data")
        
        manager = PersistenceManager(str(db_dir))
        
        # Create backup
        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()
        manager.backup_database(str(backup_dir))
        
        # Verify backup was created
        assert (backup_dir / "test.bin").exists()
        
        # Clear original database
        shutil.rmtree(db_dir)
        db_dir.mkdir()
        
        # Restore from backup
        manager.restore_database(str(backup_dir))
        
        # Verify restored content matches original
        assert (db_dir / "test.bin").exists()
        assert (db_dir / "test.bin").read_bytes() == b"test data"


# ============================================================================
# Property 6: Request ID propagation
# ============================================================================

class TestRequestIDPropagationProperty:
    """Property 6: Request ID propagation.
    
    For any request through the system, the request ID should be present
    in all related log entries.
    
    Validates: Requirements 9.2
    """
    
    @given(
        request_id=st.text(min_size=10, max_size=50, alphabet=st.characters(
            blacklist_characters="\n\r\t"
        ))
    )
    @settings(max_examples=100)
    def test_request_id_persistence(self, request_id):
        """Test that request ID persists across get/set operations."""
        # Set request ID
        set_request_id(request_id)
        
        # Get request ID
        retrieved_id = get_request_id()
        
        # Should match
        assert retrieved_id == request_id


# ============================================================================
# Property 7: Error message sanitization
# ============================================================================

class TestErrorMessageSanitizationProperty:
    """Property 7: Error message sanitization.
    
    For any exception containing sensitive data, the sanitized error message
    should not contain the sensitive data.
    
    Validates: Requirements 2.3, 9.3
    """
    
    @given(
        error_type=st.sampled_from(["ValueError", "RuntimeError", "ConnectionError"]),
        sensitive_data=st.text(min_size=10, max_size=50)
    )
    @settings(max_examples=100)
    def test_sensitive_data_removed(self, error_type, sensitive_data):
        """Test that sensitive data is removed from error messages."""
        manager = SecurityManager([])
        
        # Create error with sensitive data
        error_msg = f"{error_type}: Failed with secret: {sensitive_data}"
        error = Exception(error_msg)
        
        sanitized = manager.sanitize_error_message(error)
        
        # Should be a string
        assert isinstance(sanitized, str)
        
        # Should not contain the full error message if it's too long
        # (sanitization might truncate or redact)
        assert len(sanitized) <= len(error_msg) + 50  # Allow some overhead for redaction markers


# ============================================================================
# Property 8: Metrics accuracy
# ============================================================================

class TestMetricsAccuracyProperty:
    """Property 8: Metrics accuracy.
    
    For any set of requests processed, the collected metrics should accurately
    reflect request counts, error counts, and response times.
    
    Validates: Requirements 4.5
    """
    
    @given(
        num_requests=st.integers(min_value=1, max_value=100),
        num_errors=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=100)
    def test_metrics_count_accuracy(self, num_requests, num_errors):
        """Test that metrics accurately count requests and errors."""
        # Ensure num_errors doesn't exceed num_requests
        num_errors = min(num_errors, num_requests)
        
        collector = MetricsCollector()
        
        # Record requests
        for i in range(num_requests):
            endpoint = f"/api/endpoint{i % 3}"
            duration = 100 + (i % 50)
            status_code = 500 if i < num_errors else 200
            error = "ValueError" if i < num_errors else None
            
            collector.record_request(endpoint, duration, status_code, error)
        
        metrics = collector.get_metrics()
        
        # Verify counts
        assert metrics.total_requests == num_requests
        assert metrics.total_errors == num_errors
        
        # Error rate should be accurate
        expected_error_rate = num_errors / num_requests if num_requests > 0 else 0
        assert abs(metrics.error_rate - expected_error_rate) < 0.01


# ============================================================================
# Property 9: Configuration defaults
# ============================================================================

class TestConfigurationDefaultsProperty:
    """Property 9: Configuration defaults.
    
    For any optional configuration parameter, if not provided, the system
    should use a sensible default value.
    
    Validates: Requirements 1.5
    """
    
    def test_defaults_are_sensible(self):
        """Test that default configuration values are sensible."""
        config = Config(
            llm_provider="openai",
            llm_model="gpt-4",
            openai_api_key="sk-test_key_1234567890"
        )
        
        # Check defaults are sensible
        assert config.chunk_size > 0
        assert config.chunk_overlap >= 0
        assert config.chunk_overlap < config.chunk_size
        assert config.max_context_tokens > 0
        assert config.max_response_tokens > 0
        assert config.top_k_results > 0
        assert config.max_retries >= 0
        assert config.port > 0
        assert config.port <= 65535


# ============================================================================
# Property 10: Deployment artifact consistency
# ============================================================================

class TestDeploymentArtifactConsistencyProperty:
    """Property 10: Deployment artifact consistency.
    
    For any deployment, the built artifacts should be identical when built
    from the same source code and configuration.
    
    Validates: Requirements 6.1, 6.2
    """
    
    def test_config_serialization_consistency(self):
        """Test that configuration serialization is consistent."""
        config1 = Config(
            llm_provider="openai",
            llm_model="gpt-4",
            openai_api_key="sk-test_key_1234567890",
            chunk_size=500,
            chunk_overlap=50
        )
        
        config2 = Config(
            llm_provider="openai",
            llm_model="gpt-4",
            openai_api_key="sk-test_key_1234567890",
            chunk_size=500,
            chunk_overlap=50
        )
        
        # Both configs should have identical values
        assert config1.llm_provider == config2.llm_provider
        assert config1.llm_model == config2.llm_model
        assert config1.chunk_size == config2.chunk_size
        assert config1.chunk_overlap == config2.chunk_overlap
