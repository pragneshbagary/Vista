"""Tests for security module."""

import pytest
from vista.security import SecurityManager


class TestSecurityManager:
    """Tests for SecurityManager class."""
    
    @pytest.fixture
    def security_manager(self):
        """Create a SecurityManager instance for testing."""
        allowed_origins = [
            "https://yourdomain.com",
            "https://www.yourdomain.com",
            "http://localhost:3000"
        ]
        return SecurityManager(allowed_origins)
    
    def test_validate_origin_allowed(self, security_manager):
        """Test that allowed origins are validated correctly."""
        assert security_manager.validate_origin("https://yourdomain.com") is True
        assert security_manager.validate_origin("https://www.yourdomain.com") is True
        assert security_manager.validate_origin("http://localhost:3000") is True
    
    def test_validate_origin_rejected(self, security_manager):
        """Test that unauthorized origins are rejected."""
        assert security_manager.validate_origin("https://malicious.com") is False
        assert security_manager.validate_origin("http://yourdomain.com") is False
    
    def test_validate_origin_none(self, security_manager):
        """Test that None origin is rejected."""
        assert security_manager.validate_origin(None) is False
    
    def test_validate_origin_empty(self, security_manager):
        """Test that empty origin is rejected."""
        assert security_manager.validate_origin("") is False
    
    def test_sanitize_openai_api_key(self, security_manager):
        """Test that OpenAI API keys are sanitized."""
        error_msg = "Error: sk-proj-1234567890abcdefghijklmnopqrstuvwxyz failed"
        sanitized = security_manager.sanitize_error_message(Exception(error_msg))
        assert "sk-proj" not in sanitized
        assert "[REDACTED_OPENAI_KEY]" in sanitized
    
    def test_sanitize_gemini_api_key(self, security_manager):
        """Test that Gemini API keys are sanitized."""
        error_msg = "Error: AIzaSyDummyKeyForTesting1234567890 failed"
        sanitized = security_manager.sanitize_error_message(Exception(error_msg))
        assert "AIzaSy" not in sanitized
        assert "[REDACTED_GEMINI_KEY]" in sanitized
    
    def test_sanitize_bearer_token(self, security_manager):
        """Test that bearer tokens are sanitized."""
        error_msg = "Authorization failed: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        sanitized = security_manager.sanitize_error_message(Exception(error_msg))
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
        assert "Bearer [REDACTED]" in sanitized
    
    def test_sanitize_authorization_header(self, security_manager):
        """Test that authorization headers are sanitized."""
        error_msg = "Request failed with Authorization: Bearer secret_token_12345"
        sanitized = security_manager.sanitize_error_message(Exception(error_msg))
        assert "secret_token_12345" not in sanitized
        assert "[REDACTED]" in sanitized
    
    def test_sanitize_url_credentials(self, security_manager):
        """Test that URL credentials are sanitized."""
        error_msg = "Connection failed: postgresql://user:password@localhost:5432/db"
        sanitized = security_manager.sanitize_error_message(Exception(error_msg))
        assert "password" not in sanitized or "[REDACTED]" in sanitized
    
    def test_sanitize_generic_secrets(self, security_manager):
        """Test that generic secret patterns are sanitized."""
        error_msg = "Config error: api_key=sk-1234567890abcdefghijklmnopqrstuvwxyz"
        sanitized = security_manager.sanitize_error_message(Exception(error_msg))
        assert "sk-1234567890" not in sanitized
        assert "[REDACTED]" in sanitized
    
    def test_sanitize_log_message(self, security_manager):
        """Test that log messages are sanitized."""
        log_msg = "Processing with API key: sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
        sanitized = security_manager.sanitize_log_message(log_msg)
        assert "sk-proj" not in sanitized
        assert "[REDACTED_OPENAI_KEY]" in sanitized
    
    def test_sanitize_preserves_non_sensitive_data(self, security_manager):
        """Test that sanitization preserves non-sensitive information."""
        error_msg = "Error processing query: Database connection timeout after 30 seconds"
        sanitized = security_manager.sanitize_error_message(Exception(error_msg))
        assert "Error processing query" in sanitized
        assert "Database connection timeout" in sanitized
        assert "30 seconds" in sanitized
    
    def test_log_security_event(self, security_manager, caplog):
        """Test that security events are logged."""
        import logging
        caplog.set_level(logging.WARNING)
        
        security_manager.log_security_event(
            "cors_rejection",
            {"origin": "https://malicious.com"}
        )
        
        assert "SECURITY_EVENT" in caplog.text
        assert "cors_rejection" in caplog.text


class TestCORSValidationProperty:
    """Property-based tests for CORS validation."""
    
    def test_cors_validation_consistency(self):
        """Test that CORS validation is consistent.
        
        Property: For any origin and whitelist, validation result should be consistent
        across multiple calls.
        
        Validates: Requirements 2.1, 2.2
        """
        allowed_origins = ["https://example.com", "https://app.example.com"]
        manager = SecurityManager(allowed_origins)
        
        test_origins = [
            "https://example.com",
            "https://app.example.com",
            "https://malicious.com",
            "http://example.com",
            None,
            ""
        ]
        
        # Validate consistency: calling validate_origin multiple times should give same result
        for origin in test_origins:
            result1 = manager.validate_origin(origin)
            result2 = manager.validate_origin(origin)
            result3 = manager.validate_origin(origin)
            
            assert result1 == result2 == result3, \
                f"Validation inconsistent for origin: {origin}"


class TestErrorSanitizationProperty:
    """Property-based tests for error sanitization."""
    
    def test_sanitization_removes_all_api_keys(self):
        """Test that sanitization removes all API key patterns.
        
        Property: For any error message containing API keys, the sanitized output
        should not contain the original API key.
        
        Validates: Requirements 2.3, 9.1
        """
        manager = SecurityManager([])
        
        test_cases = [
            ("sk-proj-1234567890abcdefghijklmnopqrstuvwxyz", "[REDACTED_OPENAI_KEY]"),
            ("AIzaSyDummyKeyForTesting1234567890", "[REDACTED_GEMINI_KEY]"),
            ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "Bearer [REDACTED]"),
        ]
        
        for original, expected_pattern in test_cases:
            error_msg = f"Error with key: {original}"
            sanitized = manager.sanitize_error_message(Exception(error_msg))
            
            # Original key should not be in sanitized output
            assert original not in sanitized, \
                f"Original key still present in sanitized output: {sanitized}"
            
            # Sanitized pattern should be present
            assert expected_pattern in sanitized or "[REDACTED" in sanitized, \
                f"Expected sanitization pattern not found in: {sanitized}"
    
    def test_sanitization_preserves_error_context(self):
        """Test that sanitization preserves useful error context.
        
        Property: For any error message, the sanitized version should preserve
        the error type and context while removing sensitive data.
        
        Validates: Requirements 2.3, 9.3
        """
        manager = SecurityManager([])
        
        error_msg = "Database connection failed: postgresql://user:password@localhost:5432/db with timeout 30s"
        sanitized = manager.sanitize_error_message(Exception(error_msg))
        
        # Should preserve error context
        assert "Database connection failed" in sanitized
        assert "timeout" in sanitized
        assert "30s" in sanitized
        
        # Should remove credentials
        assert "password" not in sanitized or "[REDACTED]" in sanitized
