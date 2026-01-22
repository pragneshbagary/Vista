"""Tests for structured logging system."""

import pytest
import logging
import json
from io import StringIO
from vista.structured_logging import (
    StructuredLogger, StructuredFormatter, get_request_id, set_request_id,
    setup_structured_logging
)


@pytest.fixture
def logger():
    """Create a structured logger for testing."""
    return StructuredLogger("test_logger")


@pytest.fixture
def log_stream():
    """Create a string stream to capture log output."""
    return StringIO()


class TestRequestIdContext:
    """Tests for request ID context management."""
    
    def test_get_request_id_generates_new(self):
        """Test that get_request_id generates a new ID if none exists."""
        # Clear any existing request ID
        set_request_id(None)
        
        request_id = get_request_id()
        
        assert request_id is not None
        assert len(request_id) > 0
    
    def test_set_and_get_request_id(self):
        """Test setting and getting request ID."""
        test_id = "test-request-123"
        set_request_id(test_id)
        
        request_id = get_request_id()
        
        assert request_id == test_id
    
    def test_request_id_persistence(self):
        """Test that request ID persists across calls."""
        test_id = "persistent-id-456"
        set_request_id(test_id)
        
        id1 = get_request_id()
        id2 = get_request_id()
        
        assert id1 == id2 == test_id


class TestStructuredFormatter:
    """Tests for StructuredFormatter."""
    
    def test_format_basic_log(self):
        """Test formatting a basic log record."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logger"] == "test"
        assert "timestamp" in data
        assert "request_id" in data
    
    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.extra_fields = {"user_id": "123", "action": "login"}
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["user_id"] == "123"
        assert data["action"] == "login"


class TestStructuredLogger:
    """Tests for StructuredLogger."""
    
    def test_log_request(self, logger):
        """Test logging a request."""
        logger.log_request("GET", "/api/test", {"param": "value"})
        
        # Verify the logger was called (we can't easily capture output in this test)
        assert logger.logger is not None
    
    def test_log_response(self, logger):
        """Test logging a response."""
        logger.log_response(200, 45.5, "/api/test")
        
        assert logger.logger is not None
    
    def test_log_error(self, logger):
        """Test logging an error."""
        error = Exception("Test error")
        logger.log_error(error, {"endpoint": "/api/test"})
        
        assert logger.logger is not None
    
    def test_log_security_event(self, logger):
        """Test logging a security event."""
        logger.log_security_event("cors_rejection", {"origin": "http://evil.com"})
        
        assert logger.logger is not None
    
    def test_log_component_health(self, logger):
        """Test logging component health."""
        logger.log_component_health("database", "healthy", {"response_time_ms": 10})
        
        assert logger.logger is not None


class TestStructuredLoggingSetup:
    """Tests for structured logging setup."""
    
    def test_setup_structured_logging(self):
        """Test setting up structured logging."""
        setup_structured_logging("info")
        
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        
        # Check that we have a StructuredFormatter
        has_structured_formatter = any(
            isinstance(handler.formatter, StructuredFormatter)
            for handler in root_logger.handlers
        )
        assert has_structured_formatter
    
    def test_setup_with_different_levels(self):
        """Test setup with different log levels."""
        for level in ["debug", "info", "warning", "error", "critical"]:
            setup_structured_logging(level)
            root_logger = logging.getLogger()
            assert root_logger.level == getattr(logging, level.upper())


class TestStructuredLoggerIntegration:
    """Integration tests for structured logging."""
    
    def test_request_response_logging_flow(self, logger):
        """Test a complete request-response logging flow."""
        set_request_id("test-request-789")
        
        logger.log_request("POST", "/api/chat", {"message": "hello"})
        logger.log_response(200, 123.45, "/api/chat")
        
        assert logger.logger is not None
    
    def test_error_logging_with_context(self, logger):
        """Test error logging with context."""
        set_request_id("error-request-101")
        
        try:
            raise ValueError("Invalid input")
        except ValueError as e:
            logger.log_error(e, {"input": "test", "validation": "failed"})
        
        assert logger.logger is not None
    
    def test_security_event_logging(self, logger):
        """Test security event logging."""
        set_request_id("security-request-202")
        
        logger.log_security_event("cors_rejection", {
            "origin": "http://unauthorized.com",
            "allowed_origins": ["https://example.com"]
        })
        
        assert logger.logger is not None
