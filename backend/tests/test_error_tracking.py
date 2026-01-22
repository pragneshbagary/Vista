"""Tests for error tracking system."""

import pytest
from datetime import datetime, timedelta
from vista.error_tracking import (
    ErrorTracker, ErrorDashboard, ErrorEvent, ErrorSeverity, ErrorStats,
    get_error_tracker, get_error_dashboard, setup_error_tracking
)


@pytest.fixture
def error_tracker():
    """Create an error tracker for testing."""
    return ErrorTracker()


@pytest.fixture
def error_dashboard(error_tracker):
    """Create an error dashboard for testing."""
    return ErrorDashboard(error_tracker)


class TestErrorTracker:
    """Tests for ErrorTracker class."""
    
    def test_error_tracker_initialization(self, error_tracker):
        """Test error tracker initializes correctly."""
        assert len(error_tracker.error_events) == 0
        assert error_tracker.max_events == 10000
    
    def test_track_error_basic(self, error_tracker):
        """Test tracking a basic error."""
        error = ValueError("Test error")
        event = error_tracker.track_error(error)
        
        assert event.error_type == "ValueError"
        assert event.message == "Test error"
        assert event.severity == ErrorSeverity.MEDIUM
        assert len(error_tracker.error_events) == 1
    
    def test_track_error_with_severity(self, error_tracker):
        """Test tracking error with custom severity."""
        error = RuntimeError("Critical error")
        event = error_tracker.track_error(error, severity=ErrorSeverity.CRITICAL)
        
        assert event.severity == ErrorSeverity.CRITICAL
    
    def test_track_error_with_context(self, error_tracker):
        """Test tracking error with context."""
        error = Exception("Test")
        context = {"user_id": "123", "action": "login"}
        event = error_tracker.track_error(error, context=context)
        
        assert event.context == context
    
    def test_track_error_with_request_id(self, error_tracker):
        """Test tracking error with request ID."""
        error = Exception("Test")
        event = error_tracker.track_error(error, request_id="req-123")
        
        assert event.request_id == "req-123"
    
    def test_track_error_with_endpoint(self, error_tracker):
        """Test tracking error with endpoint."""
        error = Exception("Test")
        event = error_tracker.track_error(error, endpoint="/api/chat")
        
        assert event.endpoint == "/api/chat"
    
    def test_track_multiple_errors(self, error_tracker):
        """Test tracking multiple errors."""
        error_tracker.track_error(ValueError("Error 1"))
        error_tracker.track_error(RuntimeError("Error 2"))
        error_tracker.track_error(TypeError("Error 3"))
        
        assert len(error_tracker.error_events) == 3
    
    def test_get_stats(self, error_tracker):
        """Test getting error statistics."""
        error_tracker.track_error(ValueError("Error 1"))
        error_tracker.track_error(ValueError("Error 2"))
        error_tracker.track_error(RuntimeError("Error 3"))
        
        stats = error_tracker.get_stats()
        
        assert stats.total_errors == 3
        assert stats.errors_by_type["ValueError"] == 2
        assert stats.errors_by_type["RuntimeError"] == 1
        assert stats.most_common_error == "ValueError"
    
    def test_get_stats_by_severity(self, error_tracker):
        """Test getting statistics by severity."""
        error_tracker.track_error(ValueError("Error 1"), severity=ErrorSeverity.LOW)
        error_tracker.track_error(RuntimeError("Error 2"), severity=ErrorSeverity.CRITICAL)
        error_tracker.track_error(TypeError("Error 3"), severity=ErrorSeverity.HIGH)
        
        stats = error_tracker.get_stats()
        
        assert stats.errors_by_severity[ErrorSeverity.LOW] == 1
        assert stats.errors_by_severity[ErrorSeverity.CRITICAL] == 1
        assert stats.errors_by_severity[ErrorSeverity.HIGH] == 1
    
    def test_get_stats_by_endpoint(self, error_tracker):
        """Test getting statistics by endpoint."""
        error_tracker.track_error(ValueError("Error 1"), endpoint="/api/chat")
        error_tracker.track_error(RuntimeError("Error 2"), endpoint="/api/chat")
        error_tracker.track_error(TypeError("Error 3"), endpoint="/health")
        
        stats = error_tracker.get_stats()
        
        assert stats.errors_by_endpoint["/api/chat"] == 2
        assert stats.errors_by_endpoint["/health"] == 1
    
    def test_get_errors_by_type(self, error_tracker):
        """Test filtering errors by type."""
        error_tracker.track_error(ValueError("Error 1"))
        error_tracker.track_error(ValueError("Error 2"))
        error_tracker.track_error(RuntimeError("Error 3"))
        
        value_errors = error_tracker.get_errors_by_type("ValueError")
        
        assert len(value_errors) == 2
        assert all(e.error_type == "ValueError" for e in value_errors)
    
    def test_get_errors_by_severity(self, error_tracker):
        """Test filtering errors by severity."""
        error_tracker.track_error(ValueError("Error 1"), severity=ErrorSeverity.CRITICAL)
        error_tracker.track_error(RuntimeError("Error 2"), severity=ErrorSeverity.CRITICAL)
        error_tracker.track_error(TypeError("Error 3"), severity=ErrorSeverity.LOW)
        
        critical_errors = error_tracker.get_errors_by_severity(ErrorSeverity.CRITICAL)
        
        assert len(critical_errors) == 2
        assert all(e.severity == ErrorSeverity.CRITICAL for e in critical_errors)
    
    def test_get_errors_by_endpoint(self, error_tracker):
        """Test filtering errors by endpoint."""
        error_tracker.track_error(ValueError("Error 1"), endpoint="/api/chat")
        error_tracker.track_error(RuntimeError("Error 2"), endpoint="/api/chat")
        error_tracker.track_error(TypeError("Error 3"), endpoint="/health")
        
        chat_errors = error_tracker.get_errors_by_endpoint("/api/chat")
        
        assert len(chat_errors) == 2
        assert all(e.endpoint == "/api/chat" for e in chat_errors)
    
    def test_get_errors_by_request_id(self, error_tracker):
        """Test filtering errors by request ID."""
        error_tracker.track_error(ValueError("Error 1"), request_id="req-123")
        error_tracker.track_error(RuntimeError("Error 2"), request_id="req-123")
        error_tracker.track_error(TypeError("Error 3"), request_id="req-456")
        
        req_errors = error_tracker.get_errors_by_request_id("req-123")
        
        assert len(req_errors) == 2
        assert all(e.request_id == "req-123" for e in req_errors)
    
    def test_get_recent_errors(self, error_tracker):
        """Test getting recent errors."""
        for i in range(150):
            error_tracker.track_error(ValueError(f"Error {i}"))
        
        recent = error_tracker.get_recent_errors(limit=50)
        
        assert len(recent) == 50
    
    def test_error_event_limit(self, error_tracker):
        """Test that error events are limited to prevent memory bloat."""
        # Create tracker with small limit
        tracker = ErrorTracker(max_events=100)
        
        # Add more than limit
        for i in range(150):
            tracker.track_error(ValueError(f"Error {i}"))
        
        # Should only keep last 100
        assert len(tracker.error_events) == 100
    
    def test_clear_old_errors(self, error_tracker):
        """Test clearing old errors."""
        # Add old error
        old_event = ErrorEvent(
            error_type="ValueError",
            message="Old error",
            timestamp=datetime.utcnow() - timedelta(days=10),
            severity=ErrorSeverity.LOW
        )
        error_tracker.error_events.append(old_event)
        
        # Add recent error
        error_tracker.track_error(ValueError("Recent error"))
        
        assert len(error_tracker.error_events) == 2
        
        # Clear errors older than 7 days
        removed = error_tracker.clear_old_errors(days=7)
        
        assert removed == 1
        assert len(error_tracker.error_events) == 1
    
    def test_reset(self, error_tracker):
        """Test resetting error tracker."""
        error_tracker.track_error(ValueError("Error 1"))
        error_tracker.track_error(RuntimeError("Error 2"))
        
        assert len(error_tracker.error_events) == 2
        
        error_tracker.reset()
        
        assert len(error_tracker.error_events) == 0


class TestErrorEvent:
    """Tests for ErrorEvent dataclass."""
    
    def test_error_event_creation(self):
        """Test creating error event."""
        event = ErrorEvent(
            error_type="ValueError",
            message="Test error",
            timestamp=datetime.utcnow(),
            severity=ErrorSeverity.MEDIUM
        )
        
        assert event.error_type == "ValueError"
        assert event.message == "Test error"
        assert event.severity == ErrorSeverity.MEDIUM
    
    def test_error_event_to_dict(self):
        """Test converting error event to dictionary."""
        event = ErrorEvent(
            error_type="ValueError",
            message="Test error",
            timestamp=datetime.utcnow(),
            severity=ErrorSeverity.MEDIUM,
            request_id="req-123"
        )
        
        data = event.to_dict()
        
        assert data["error_type"] == "ValueError"
        assert data["message"] == "Test error"
        assert data["request_id"] == "req-123"


class TestErrorStats:
    """Tests for ErrorStats dataclass."""
    
    def test_error_stats_defaults(self):
        """Test ErrorStats default values."""
        stats = ErrorStats()
        
        assert stats.total_errors == 0
        assert stats.errors_by_type == {}
        assert stats.errors_by_severity == {}
        assert stats.error_rate_per_minute == 0.0
    
    def test_error_stats_to_dict(self):
        """Test converting error stats to dictionary."""
        stats = ErrorStats(
            total_errors=10,
            errors_by_type={"ValueError": 5},
            error_rate_per_minute=0.5
        )
        
        data = stats.to_dict()
        
        assert data["total_errors"] == 10
        assert data["errors_by_type"]["ValueError"] == 5
        assert data["error_rate_per_minute"] == 0.5


class TestErrorDashboard:
    """Tests for ErrorDashboard class."""
    
    def test_dashboard_initialization(self, error_dashboard):
        """Test dashboard initializes correctly."""
        assert error_dashboard.error_tracker is not None
    
    def test_get_dashboard_data(self, error_tracker, error_dashboard):
        """Test getting dashboard data."""
        error_tracker.track_error(ValueError("Error 1"))
        error_tracker.track_error(RuntimeError("Error 2"))
        
        data = error_dashboard.get_dashboard_data()
        
        assert "summary" in data
        assert "by_type" in data
        assert "by_severity" in data
        assert "recent_errors" in data
        assert data["summary"]["total_errors"] == 2
    
    def test_get_error_trend(self, error_tracker, error_dashboard):
        """Test getting error trend."""
        error_tracker.track_error(ValueError("Error 1"))
        error_tracker.track_error(RuntimeError("Error 2"))
        
        trend = error_dashboard.get_error_trend(hours=1, interval_minutes=60)
        
        assert "time_range" in trend
        assert "data" in trend
        assert trend["interval_minutes"] == 60
    
    def test_get_error_summary_by_type(self, error_tracker, error_dashboard):
        """Test getting error summary by type."""
        error_tracker.track_error(ValueError("Error 1"))
        error_tracker.track_error(ValueError("Error 2"))
        error_tracker.track_error(RuntimeError("Error 3"))
        
        summary = error_dashboard.get_error_summary_by_type()
        
        assert len(summary) == 2
        assert summary[0]["error_type"] == "ValueError"
        assert summary[0]["count"] == 2
    
    def test_get_error_summary_by_endpoint(self, error_tracker, error_dashboard):
        """Test getting error summary by endpoint."""
        error_tracker.track_error(ValueError("Error 1"), endpoint="/api/chat")
        error_tracker.track_error(RuntimeError("Error 2"), endpoint="/api/chat")
        error_tracker.track_error(TypeError("Error 3"), endpoint="/health")
        
        summary = error_dashboard.get_error_summary_by_endpoint()
        
        assert len(summary) == 2
        assert summary[0]["endpoint"] == "/api/chat"
        assert summary[0]["count"] == 2


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""
    
    def test_error_severity_values(self):
        """Test error severity enum values."""
        assert ErrorSeverity.LOW == "low"
        assert ErrorSeverity.MEDIUM == "medium"
        assert ErrorSeverity.HIGH == "high"
        assert ErrorSeverity.CRITICAL == "critical"


class TestGlobalInstances:
    """Tests for global error tracking instances."""
    
    def test_get_error_tracker_singleton(self):
        """Test that get_error_tracker returns singleton."""
        tracker1 = get_error_tracker()
        tracker2 = get_error_tracker()
        
        assert tracker1 is tracker2
    
    def test_get_error_dashboard_singleton(self):
        """Test that get_error_dashboard returns singleton."""
        dashboard1 = get_error_dashboard()
        dashboard2 = get_error_dashboard()
        
        assert dashboard1 is dashboard2
    
    def test_setup_error_tracking(self):
        """Test setting up error tracking."""
        tracker = setup_error_tracking()
        
        assert tracker is not None
        assert isinstance(tracker, ErrorTracker)


class TestErrorTrackingEdgeCases:
    """Tests for edge cases in error tracking."""
    
    def test_track_error_with_all_parameters(self, error_tracker):
        """Test tracking error with all parameters."""
        error = ValueError("Test error")
        context = {"key": "value"}
        event = error_tracker.track_error(
            error,
            severity=ErrorSeverity.CRITICAL,
            context=context,
            request_id="req-123",
            endpoint="/api/test",
            user_id="user-456"
        )
        
        assert event.error_type == "ValueError"
        assert event.severity == ErrorSeverity.CRITICAL
        assert event.context == context
        assert event.request_id == "req-123"
        assert event.endpoint == "/api/test"
        assert event.user_id == "user-456"
    
    def test_error_rate_calculation(self, error_tracker):
        """Test error rate calculation."""
        # Add errors with timestamps
        for i in range(10):
            error_tracker.track_error(ValueError(f"Error {i}"))
        
        stats = error_tracker.get_stats(time_window_minutes=60)
        
        # Error rate should be calculated
        assert stats.error_rate_per_minute >= 0
    
    def test_empty_error_stats(self, error_tracker):
        """Test stats with no errors."""
        stats = error_tracker.get_stats()
        
        assert stats.total_errors == 0
        assert stats.errors_by_type == {}
        assert stats.most_common_error is None
    
    def test_filter_with_no_matches(self, error_tracker):
        """Test filtering with no matching errors."""
        error_tracker.track_error(ValueError("Error 1"))
        
        runtime_errors = error_tracker.get_errors_by_type("RuntimeError")
        
        assert len(runtime_errors) == 0
    
    def test_error_event_with_stack_trace(self, error_tracker):
        """Test that stack trace is captured."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            event = error_tracker.track_error(e)
        
        assert event.stack_trace is not None
        assert "ValueError" in event.stack_trace
