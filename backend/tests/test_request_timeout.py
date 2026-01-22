"""Tests for request timeout handling."""

import pytest
import time
from vista.request_timeout import TimeoutConfig, RequestTimeout, RequestTimeoutHandler


class TestTimeoutConfig:
    """Tests for TimeoutConfig class."""
    
    def test_default_config(self):
        """Test default timeout configuration."""
        config = TimeoutConfig()
        
        assert config.default_timeout == 120
        assert config.read_timeout == 30
        assert config.write_timeout == 30
        assert config.connect_timeout == 10
    
    def test_get_timeout_for_endpoint_default(self):
        """Test getting default timeout for endpoint."""
        config = TimeoutConfig()
        
        timeout = config.get_timeout_for_endpoint("/api/chat")
        assert timeout == 120
    
    def test_get_timeout_for_endpoint_override(self):
        """Test getting overridden timeout for endpoint."""
        config = TimeoutConfig(
            endpoint_timeouts={
                "/api/chat": 60,
                "/api/health": 10
            }
        )
        
        assert config.get_timeout_for_endpoint("/api/chat") == 60
        assert config.get_timeout_for_endpoint("/api/health") == 10
        assert config.get_timeout_for_endpoint("/api/other") == 120
    
    def test_validation_invalid_default_timeout(self):
        """Test validation fails with invalid default timeout."""
        config = TimeoutConfig(default_timeout=0)
        
        with pytest.raises(ValueError, match="default_timeout must be at least 1"):
            config.validate()
    
    def test_validation_invalid_read_timeout(self):
        """Test validation fails with invalid read timeout."""
        config = TimeoutConfig(read_timeout=0)
        
        with pytest.raises(ValueError, match="read_timeout must be at least 1"):
            config.validate()
    
    def test_validation_invalid_endpoint_timeout(self):
        """Test validation fails with invalid endpoint timeout."""
        config = TimeoutConfig(
            endpoint_timeouts={"/api/chat": 0}
        )
        
        with pytest.raises(ValueError, match="Timeout for endpoint /api/chat"):
            config.validate()


class TestRequestTimeout:
    """Tests for RequestTimeout class."""
    
    def test_request_timeout_creation(self):
        """Test creating request timeout."""
        start_time = time.time()
        timeout = RequestTimeout(
            request_id="req-123",
            endpoint="/api/chat",
            start_time=start_time,
            timeout_seconds=120
        )
        
        assert timeout.request_id == "req-123"
        assert timeout.endpoint == "/api/chat"
        assert timeout.timeout_seconds == 120
    
    def test_is_expired_not_expired(self):
        """Test request not expired."""
        timeout = RequestTimeout(
            request_id="req-123",
            endpoint="/api/chat",
            start_time=time.time(),
            timeout_seconds=120
        )
        
        assert timeout.is_expired() is False
    
    def test_is_expired_expired(self):
        """Test request expired."""
        timeout = RequestTimeout(
            request_id="req-123",
            endpoint="/api/chat",
            start_time=time.time() - 130,  # 130 seconds ago
            timeout_seconds=120
        )
        
        assert timeout.is_expired() is True
    
    def test_get_elapsed_time(self):
        """Test getting elapsed time."""
        timeout = RequestTimeout(
            request_id="req-123",
            endpoint="/api/chat",
            start_time=time.time() - 5,  # 5 seconds ago
            timeout_seconds=120
        )
        
        elapsed = timeout.get_elapsed_time()
        assert 4.9 < elapsed < 5.1  # Allow small variance
    
    def test_get_remaining_time(self):
        """Test getting remaining time."""
        timeout = RequestTimeout(
            request_id="req-123",
            endpoint="/api/chat",
            start_time=time.time() - 30,  # 30 seconds ago
            timeout_seconds=120
        )
        
        remaining = timeout.get_remaining_time()
        assert 89 < remaining < 91  # Allow small variance
    
    def test_get_remaining_time_expired(self):
        """Test remaining time when expired."""
        timeout = RequestTimeout(
            request_id="req-123",
            endpoint="/api/chat",
            start_time=time.time() - 130,  # 130 seconds ago
            timeout_seconds=120
        )
        
        remaining = timeout.get_remaining_time()
        assert remaining == 0


class TestRequestTimeoutHandler:
    """Tests for RequestTimeoutHandler class."""
    
    def test_handler_initialization(self):
        """Test handler initialization."""
        config = TimeoutConfig()
        handler = RequestTimeoutHandler(config)
        
        assert handler.get_active_request_count() == 0
        assert len(handler.get_timeout_events()) == 0
    
    def test_start_request(self):
        """Test starting request tracking."""
        config = TimeoutConfig()
        handler = RequestTimeoutHandler(config)
        
        timeout = handler.start_request("req-123", "/api/chat")
        
        assert timeout.request_id == "req-123"
        assert timeout.endpoint == "/api/chat"
        assert handler.get_active_request_count() == 1
    
    def test_end_request(self):
        """Test ending request tracking."""
        config = TimeoutConfig()
        handler = RequestTimeoutHandler(config)
        
        handler.start_request("req-123", "/api/chat")
        timeout = handler.end_request("req-123")
        
        assert timeout is not None
        assert timeout.request_id == "req-123"
        assert handler.get_active_request_count() == 0
    
    def test_end_request_not_found(self):
        """Test ending request that doesn't exist."""
        config = TimeoutConfig()
        handler = RequestTimeoutHandler(config)
        
        timeout = handler.end_request("req-999")
        
        assert timeout is None
    
    def test_check_timeout_not_expired(self):
        """Test checking timeout for non-expired request."""
        config = TimeoutConfig()
        handler = RequestTimeoutHandler(config)
        
        handler.start_request("req-123", "/api/chat")
        is_expired = handler.check_timeout("req-123")
        
        assert is_expired is False
    
    def test_check_timeout_expired(self):
        """Test checking timeout for expired request."""
        config = TimeoutConfig(default_timeout=1)
        handler = RequestTimeoutHandler(config)
        
        handler.start_request("req-123", "/api/chat")
        time.sleep(1.1)
        is_expired = handler.check_timeout("req-123")
        
        assert is_expired is True
        assert len(handler.get_timeout_events()) == 1
    
    def test_check_timeout_not_found(self):
        """Test checking timeout for non-existent request."""
        config = TimeoutConfig()
        handler = RequestTimeoutHandler(config)
        
        is_expired = handler.check_timeout("req-999")
        
        assert is_expired is False
    
    def test_get_request_timeout(self):
        """Test getting request timeout info."""
        config = TimeoutConfig()
        handler = RequestTimeoutHandler(config)
        
        handler.start_request("req-123", "/api/chat")
        timeout = handler.get_request_timeout("req-123")
        
        assert timeout is not None
        assert timeout.request_id == "req-123"
    
    def test_get_timeout_events(self):
        """Test getting timeout events."""
        config = TimeoutConfig(default_timeout=1)
        handler = RequestTimeoutHandler(config)
        
        handler.start_request("req-123", "/api/chat")
        time.sleep(1.1)
        handler.check_timeout("req-123")
        
        events = handler.get_timeout_events()
        assert len(events) == 1
        assert events[0]["request_id"] == "req-123"
    
    def test_clear_timeout_events(self):
        """Test clearing timeout events."""
        config = TimeoutConfig(default_timeout=1)
        handler = RequestTimeoutHandler(config)
        
        handler.start_request("req-123", "/api/chat")
        time.sleep(1.1)
        handler.check_timeout("req-123")
        
        assert len(handler.get_timeout_events()) == 1
        handler.clear_timeout_events()
        assert len(handler.get_timeout_events()) == 0
    
    def test_get_timeout_statistics(self):
        """Test getting timeout statistics."""
        config = TimeoutConfig(default_timeout=1)
        handler = RequestTimeoutHandler(config)
        
        # Create multiple timeouts
        for i in range(3):
            handler.start_request(f"req-{i}", "/api/chat")
            time.sleep(1.1)
            handler.check_timeout(f"req-{i}")
        
        stats = handler.get_timeout_statistics()
        
        assert stats["total_timeouts"] == 3
        assert "/api/chat" in stats["timeouts_by_endpoint"]
        assert stats["timeouts_by_endpoint"]["/api/chat"] == 3
        assert stats["average_timeout_seconds"] > 0
    
    def test_get_timeout_statistics_empty(self):
        """Test getting statistics with no timeouts."""
        config = TimeoutConfig()
        handler = RequestTimeoutHandler(config)
        
        stats = handler.get_timeout_statistics()
        
        assert stats["total_timeouts"] == 0
        assert stats["average_timeout_seconds"] == 0
    
    def test_endpoint_specific_timeout(self):
        """Test endpoint-specific timeout configuration."""
        config = TimeoutConfig(
            default_timeout=120,
            endpoint_timeouts={
                "/api/chat": 60,
                "/api/health": 10
            }
        )
        handler = RequestTimeoutHandler(config)
        
        timeout1 = handler.start_request("req-1", "/api/chat")
        timeout2 = handler.start_request("req-2", "/api/health")
        
        assert timeout1.timeout_seconds == 60
        assert timeout2.timeout_seconds == 10
