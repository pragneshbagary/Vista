"""Tests for metrics collection system."""

import pytest
from vista.metrics import MetricsCollector, RequestMetrics, SystemMetrics


@pytest.fixture
def metrics_collector():
    """Create a metrics collector for testing."""
    return MetricsCollector()


class TestMetricsCollector:
    """Tests for MetricsCollector class."""
    
    def test_record_single_request(self, metrics_collector):
        """Test recording a single request."""
        metrics_collector.record_request("/api/test", 50.0, 200)
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.total_requests == 1
        assert metrics.total_errors == 0
        assert metrics.average_response_time_ms == 50.0
    
    def test_record_multiple_requests(self, metrics_collector):
        """Test recording multiple requests."""
        metrics_collector.record_request("/api/test", 50.0, 200)
        metrics_collector.record_request("/api/test", 60.0, 200)
        metrics_collector.record_request("/api/test", 40.0, 200)
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.total_requests == 3
        assert metrics.total_errors == 0
        assert metrics.average_response_time_ms == 50.0
    
    def test_record_request_with_error(self, metrics_collector):
        """Test recording a request with error."""
        metrics_collector.record_request("/api/test", 100.0, 500, error="Internal Server Error")
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.total_requests == 1
        assert metrics.total_errors == 1
        assert metrics.error_rate == 1.0
    
    def test_error_rate_calculation(self, metrics_collector):
        """Test error rate calculation."""
        metrics_collector.record_request("/api/test", 50.0, 200)
        metrics_collector.record_request("/api/test", 100.0, 500, error="Error")
        metrics_collector.record_request("/api/test", 60.0, 200)
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.total_requests == 3
        assert metrics.total_errors == 1
        assert metrics.error_rate == pytest.approx(1/3, rel=0.01)
    
    def test_percentile_calculation(self, metrics_collector):
        """Test percentile calculation."""
        # Record requests with known durations
        durations = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for duration in durations:
            metrics_collector.record_request("/api/test", float(duration), 200)
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.total_requests == 10
        assert metrics.p50_response_time_ms == 55.0  # Median of 10 values
        assert metrics.p95_response_time_ms > metrics.p50_response_time_ms
        assert metrics.p99_response_time_ms >= metrics.p95_response_time_ms
    
    def test_requests_by_endpoint(self, metrics_collector):
        """Test tracking requests by endpoint."""
        metrics_collector.record_request("/api/chat", 50.0, 200)
        metrics_collector.record_request("/api/chat", 60.0, 200)
        metrics_collector.record_request("/health", 10.0, 200)
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.requests_by_endpoint["/api/chat"] == 2
        assert metrics.requests_by_endpoint["/health"] == 1
    
    def test_errors_by_type(self, metrics_collector):
        """Test tracking errors by type."""
        metrics_collector.record_request("/api/test", 100.0, 500, error="Internal Server Error")
        metrics_collector.record_request("/api/test", 100.0, 400, error="Bad Request")
        metrics_collector.record_request("/api/test", 100.0, 500, error="Internal Server Error")
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.errors_by_type["Internal Server Error"] == 2
        assert metrics.errors_by_type["Bad Request"] == 1
    
    def test_uptime_tracking(self, metrics_collector):
        """Test uptime tracking."""
        metrics = metrics_collector.get_metrics()
        
        assert metrics.uptime_seconds >= 0
    
    def test_empty_metrics(self, metrics_collector):
        """Test getting metrics with no requests."""
        metrics = metrics_collector.get_metrics()
        
        assert metrics.total_requests == 0
        assert metrics.total_errors == 0
        assert metrics.average_response_time_ms == 0.0
        assert metrics.error_rate == 0.0
    
    def test_metrics_memory_limit(self, metrics_collector):
        """Test that metrics are limited to prevent memory bloat."""
        # Record more than 10000 requests
        for i in range(11000):
            metrics_collector.record_request("/api/test", 50.0, 200)
        
        # Should only keep last 10000
        assert len(metrics_collector.request_metrics) == 10000
    
    def test_reset_metrics(self, metrics_collector):
        """Test resetting metrics."""
        metrics_collector.record_request("/api/test", 50.0, 200)
        metrics_collector.record_request("/api/test", 60.0, 200)
        
        metrics_collector.reset_metrics()
        
        metrics = metrics_collector.get_metrics()
        assert metrics.total_requests == 0
        assert metrics.total_errors == 0


class TestRequestMetrics:
    """Tests for RequestMetrics dataclass."""
    
    def test_request_metrics_creation(self):
        """Test creating a RequestMetrics instance."""
        metric = RequestMetrics(
            endpoint="/api/test",
            duration_ms=50.0,
            status_code=200,
            error=None
        )
        
        assert metric.endpoint == "/api/test"
        assert metric.duration_ms == 50.0
        assert metric.status_code == 200
        assert metric.error is None
    
    def test_request_metrics_with_error(self):
        """Test creating a RequestMetrics with error."""
        metric = RequestMetrics(
            endpoint="/api/test",
            duration_ms=100.0,
            status_code=500,
            error="Internal Server Error"
        )
        
        assert metric.error == "Internal Server Error"


class TestSystemMetrics:
    """Tests for SystemMetrics dataclass."""
    
    def test_system_metrics_defaults(self):
        """Test SystemMetrics default values."""
        metrics = SystemMetrics()
        
        assert metrics.total_requests == 0
        assert metrics.total_errors == 0
        assert metrics.average_response_time_ms == 0.0
        assert metrics.error_rate == 0.0
        assert metrics.requests_by_endpoint == {}
        assert metrics.errors_by_type == {}


class TestMetricsEdgeCases:
    """Tests for edge cases in metrics collection."""
    
    def test_single_request_percentiles(self, metrics_collector):
        """Test percentile calculation with single request."""
        metrics_collector.record_request("/api/test", 50.0, 200)
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.p50_response_time_ms == 50.0
        assert metrics.p95_response_time_ms == 50.0
        assert metrics.p99_response_time_ms == 50.0
    
    def test_two_request_percentiles(self, metrics_collector):
        """Test percentile calculation with two requests."""
        metrics_collector.record_request("/api/test", 40.0, 200)
        metrics_collector.record_request("/api/test", 60.0, 200)
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.p50_response_time_ms == 50.0
        assert metrics.p95_response_time_ms >= 50.0
        assert metrics.p99_response_time_ms >= 50.0
    
    def test_all_errors(self, metrics_collector):
        """Test metrics when all requests are errors."""
        metrics_collector.record_request("/api/test", 100.0, 500, error="Error")
        metrics_collector.record_request("/api/test", 100.0, 500, error="Error")
        metrics_collector.record_request("/api/test", 100.0, 500, error="Error")
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.total_requests == 3
        assert metrics.total_errors == 3
        assert metrics.error_rate == 1.0
    
    def test_zero_duration_requests(self, metrics_collector):
        """Test handling requests with zero duration."""
        metrics_collector.record_request("/api/test", 0.0, 200)
        metrics_collector.record_request("/api/test", 100.0, 200)
        
        metrics = metrics_collector.get_metrics()
        
        assert metrics.total_requests == 2
        assert metrics.average_response_time_ms == 50.0
