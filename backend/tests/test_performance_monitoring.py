"""Tests for performance monitoring system."""

import pytest
from datetime import datetime, timedelta
from vista.performance_monitoring import (
    PerformanceMonitor, PerformanceMetric, PerformanceStats, ResourceUsage,
    get_performance_monitor, setup_performance_monitoring
)


@pytest.fixture
def performance_monitor():
    """Create a performance monitor for testing."""
    return PerformanceMonitor()


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class."""
    
    def test_monitor_initialization(self, performance_monitor):
        """Test monitor initializes correctly."""
        assert len(performance_monitor.metrics) == 0
        assert performance_monitor.max_metrics == 10000
    
    def test_record_metric(self, performance_monitor):
        """Test recording a performance metric."""
        metric = performance_monitor.record_metric("/api/chat", 50.0, 200)
        
        assert metric.endpoint == "/api/chat"
        assert metric.response_time_ms == 50.0
        assert metric.status_code == 200
        assert len(performance_monitor.metrics) == 1
    
    def test_record_multiple_metrics(self, performance_monitor):
        """Test recording multiple metrics."""
        performance_monitor.record_metric("/api/chat", 50.0, 200)
        performance_monitor.record_metric("/api/chat", 60.0, 200)
        performance_monitor.record_metric("/health", 10.0, 200)
        
        assert len(performance_monitor.metrics) == 3
    
    def test_get_stats_for_endpoint(self, performance_monitor):
        """Test getting stats for a specific endpoint."""
        performance_monitor.record_metric("/api/chat", 50.0, 200)
        performance_monitor.record_metric("/api/chat", 60.0, 200)
        performance_monitor.record_metric("/api/chat", 40.0, 200)
        
        stats = performance_monitor.get_stats_for_endpoint("/api/chat")
        
        assert stats.endpoint == "/api/chat"
        assert stats.total_requests == 3
        assert stats.average_response_time_ms == 50.0
        assert stats.min_response_time_ms == 40.0
        assert stats.max_response_time_ms == 60.0
    
    def test_get_stats_with_errors(self, performance_monitor):
        """Test stats calculation with error responses."""
        performance_monitor.record_metric("/api/chat", 50.0, 200)
        performance_monitor.record_metric("/api/chat", 100.0, 500)
        performance_monitor.record_metric("/api/chat", 60.0, 200)
        
        stats = performance_monitor.get_stats_for_endpoint("/api/chat")
        
        assert stats.total_requests == 3
        assert stats.error_rate == pytest.approx(1/3, rel=0.01)
    
    def test_get_all_stats(self, performance_monitor):
        """Test getting stats for all endpoints."""
        performance_monitor.record_metric("/api/chat", 50.0, 200)
        performance_monitor.record_metric("/api/chat", 60.0, 200)
        performance_monitor.record_metric("/health", 10.0, 200)
        
        all_stats = performance_monitor.get_all_stats()
        
        assert len(all_stats) == 2
        assert "/api/chat" in all_stats
        assert "/health" in all_stats
    
    def test_get_slowest_endpoints(self, performance_monitor):
        """Test getting slowest endpoints."""
        performance_monitor.record_metric("/api/chat", 100.0, 200)
        performance_monitor.record_metric("/api/chat", 110.0, 200)
        performance_monitor.record_metric("/health", 10.0, 200)
        performance_monitor.record_metric("/health", 15.0, 200)
        
        slowest = performance_monitor.get_slowest_endpoints(limit=2)
        
        assert len(slowest) == 2
        assert slowest[0].endpoint == "/api/chat"
        assert slowest[1].endpoint == "/health"
    
    def test_get_error_prone_endpoints(self, performance_monitor):
        """Test getting error-prone endpoints."""
        # /api/chat: 2 errors out of 3 = 66% error rate
        performance_monitor.record_metric("/api/chat", 50.0, 500)
        performance_monitor.record_metric("/api/chat", 60.0, 500)
        performance_monitor.record_metric("/api/chat", 40.0, 200)
        
        # /health: 0 errors out of 2 = 0% error rate
        performance_monitor.record_metric("/health", 10.0, 200)
        performance_monitor.record_metric("/health", 15.0, 200)
        
        error_prone = performance_monitor.get_error_prone_endpoints(limit=2)
        
        assert len(error_prone) == 2
        assert error_prone[0].endpoint == "/api/chat"
        assert error_prone[0].error_rate > error_prone[1].error_rate
    
    def test_percentile_calculation(self, performance_monitor):
        """Test percentile calculation."""
        # Record 100 requests with known durations
        for i in range(100):
            performance_monitor.record_metric("/api/test", float(i + 1), 200)
        
        stats = performance_monitor.get_stats_for_endpoint("/api/test")
        
        assert stats.p95_response_time_ms > stats.median_response_time_ms
        assert stats.p99_response_time_ms >= stats.p95_response_time_ms
    
    def test_metric_limit(self, performance_monitor):
        """Test that metrics are limited to prevent memory bloat."""
        # Create monitor with small limit
        monitor = PerformanceMonitor(max_metrics=100)
        
        # Add more than limit
        for i in range(150):
            monitor.record_metric("/api/test", float(i), 200)
        
        # Should only keep last 100
        assert len(monitor.metrics) == 100
    
    def test_record_resource_usage(self, performance_monitor):
        """Test recording resource usage."""
        usage = performance_monitor.record_resource_usage()
        
        if usage:  # May be None if psutil fails
            assert usage.cpu_percent >= 0
            assert usage.memory_percent >= 0
            assert usage.disk_percent >= 0
    
    def test_get_resource_stats(self, performance_monitor):
        """Test getting resource statistics."""
        # Record some resource usage
        performance_monitor.record_resource_usage()
        
        stats = performance_monitor.get_resource_stats(time_window_minutes=60)
        
        assert "cpu_percent_avg" in stats
        assert "memory_percent_avg" in stats
        assert "disk_percent_avg" in stats
    
    def test_get_performance_report(self, performance_monitor):
        """Test getting comprehensive performance report."""
        performance_monitor.record_metric("/api/chat", 50.0, 200)
        performance_monitor.record_metric("/api/chat", 60.0, 500)
        performance_monitor.record_metric("/health", 10.0, 200)
        
        report = performance_monitor.get_performance_report()
        
        assert "summary" in report
        assert "endpoints" in report
        assert "slowest_endpoints" in report
        assert "error_prone_endpoints" in report
        assert "resources" in report
        assert report["summary"]["total_requests"] == 3
    
    def test_reset(self, performance_monitor):
        """Test resetting performance monitor."""
        performance_monitor.record_metric("/api/chat", 50.0, 200)
        performance_monitor.record_metric("/api/chat", 60.0, 200)
        
        assert len(performance_monitor.metrics) == 2
        
        performance_monitor.reset()
        
        assert len(performance_monitor.metrics) == 0


class TestPerformanceMetric:
    """Tests for PerformanceMetric dataclass."""
    
    def test_metric_creation(self):
        """Test creating performance metric."""
        metric = PerformanceMetric(
            endpoint="/api/test",
            response_time_ms=50.0,
            timestamp=datetime.utcnow(),
            status_code=200
        )
        
        assert metric.endpoint == "/api/test"
        assert metric.response_time_ms == 50.0
        assert metric.status_code == 200
    
    def test_metric_to_dict(self):
        """Test converting metric to dictionary."""
        metric = PerformanceMetric(
            endpoint="/api/test",
            response_time_ms=50.0,
            timestamp=datetime.utcnow(),
            status_code=200,
            memory_usage_mb=100.0,
            cpu_percent=25.0
        )
        
        data = metric.to_dict()
        
        assert data["endpoint"] == "/api/test"
        assert data["response_time_ms"] == 50.0
        assert data["status_code"] == 200
        assert data["memory_usage_mb"] == 100.0
        assert data["cpu_percent"] == 25.0


class TestPerformanceStats:
    """Tests for PerformanceStats dataclass."""
    
    def test_stats_creation(self):
        """Test creating performance stats."""
        stats = PerformanceStats(
            endpoint="/api/test",
            total_requests=100,
            average_response_time_ms=50.0,
            error_rate=0.05
        )
        
        assert stats.endpoint == "/api/test"
        assert stats.total_requests == 100
        assert stats.average_response_time_ms == 50.0
        assert stats.error_rate == 0.05
    
    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = PerformanceStats(
            endpoint="/api/test",
            total_requests=100,
            average_response_time_ms=50.0
        )
        
        data = stats.to_dict()
        
        assert data["endpoint"] == "/api/test"
        assert data["total_requests"] == 100
        assert data["average_response_time_ms"] == 50.0


class TestResourceUsage:
    """Tests for ResourceUsage dataclass."""
    
    def test_resource_usage_creation(self):
        """Test creating resource usage."""
        usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=25.0,
            memory_percent=50.0,
            memory_mb=1024.0,
            disk_percent=60.0,
            disk_mb_free=100000.0
        )
        
        assert usage.cpu_percent == 25.0
        assert usage.memory_percent == 50.0
        assert usage.memory_mb == 1024.0
    
    def test_resource_usage_to_dict(self):
        """Test converting resource usage to dictionary."""
        usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=25.0,
            memory_percent=50.0,
            memory_mb=1024.0,
            disk_percent=60.0,
            disk_mb_free=100000.0
        )
        
        data = usage.to_dict()
        
        assert data["cpu_percent"] == 25.0
        assert data["memory_percent"] == 50.0
        assert data["memory_mb"] == 1024.0


class TestGlobalInstances:
    """Tests for global performance monitor instances."""
    
    def test_get_performance_monitor_singleton(self):
        """Test that get_performance_monitor returns singleton."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2
    
    def test_setup_performance_monitoring(self):
        """Test setting up performance monitoring."""
        monitor = setup_performance_monitoring()
        
        assert monitor is not None
        assert isinstance(monitor, PerformanceMonitor)


class TestPerformanceMonitoringEdgeCases:
    """Tests for edge cases in performance monitoring."""
    
    def test_empty_endpoint_stats(self, performance_monitor):
        """Test stats for non-existent endpoint."""
        stats = performance_monitor.get_stats_for_endpoint("/nonexistent")
        
        assert stats.endpoint == "/nonexistent"
        assert stats.total_requests == 0
    
    def test_single_request_stats(self, performance_monitor):
        """Test stats with single request."""
        performance_monitor.record_metric("/api/test", 50.0, 200)
        
        stats = performance_monitor.get_stats_for_endpoint("/api/test")
        
        assert stats.total_requests == 1
        assert stats.average_response_time_ms == 50.0
        assert stats.min_response_time_ms == 50.0
        assert stats.max_response_time_ms == 50.0
    
    def test_all_error_responses(self, performance_monitor):
        """Test stats when all responses are errors."""
        performance_monitor.record_metric("/api/test", 50.0, 500)
        performance_monitor.record_metric("/api/test", 60.0, 500)
        performance_monitor.record_metric("/api/test", 40.0, 500)
        
        stats = performance_monitor.get_stats_for_endpoint("/api/test")
        
        assert stats.error_rate == 1.0
    
    def test_zero_response_times(self, performance_monitor):
        """Test handling zero response times."""
        performance_monitor.record_metric("/api/test", 0.0, 200)
        performance_monitor.record_metric("/api/test", 0.0, 200)
        
        stats = performance_monitor.get_stats_for_endpoint("/api/test")
        
        assert stats.average_response_time_ms == 0.0
        assert stats.min_response_time_ms == 0.0
    
    def test_very_high_response_times(self, performance_monitor):
        """Test handling very high response times."""
        performance_monitor.record_metric("/api/test", 10000.0, 200)
        performance_monitor.record_metric("/api/test", 20000.0, 200)
        
        stats = performance_monitor.get_stats_for_endpoint("/api/test")
        
        assert stats.average_response_time_ms == 15000.0
        assert stats.max_response_time_ms == 20000.0
    
    def test_mixed_status_codes(self, performance_monitor):
        """Test handling mixed status codes."""
        performance_monitor.record_metric("/api/test", 50.0, 200)
        performance_monitor.record_metric("/api/test", 60.0, 201)
        performance_monitor.record_metric("/api/test", 70.0, 400)
        performance_monitor.record_metric("/api/test", 80.0, 500)
        
        stats = performance_monitor.get_stats_for_endpoint("/api/test")
        
        assert stats.total_requests == 4
        assert stats.error_rate == 0.5  # 2 errors out of 4
