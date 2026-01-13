"""Performance benchmarks for deployment preparation.

These tests measure response times, throughput, and identify bottlenecks.
"""

import pytest
import time
from unittest.mock import Mock
from statistics import mean, stdev

from vista.config import Config
from vista.security import SecurityManager
from vista.health_check import HealthChecker
from vista.metrics import MetricsCollector
from vista.query_engine import QueryEngine
from vista.models import RetrievedChunk


class TestThroughputPerformance:
    """Benchmark throughput for high-volume operations."""
    
    def test_metrics_recording_throughput(self):
        """Benchmark metrics recording throughput."""
        collector = MetricsCollector()
        
        # Record 1000 requests and measure time
        start_time = time.time()
        
        for i in range(1000):
            endpoint = f"/api/endpoint{i % 10}"
            duration = 100 + (i % 50)
            status_code = 200 if i % 10 != 0 else 500
            error = "ServerError" if i % 10 == 0 else None
            
            collector.record_request(endpoint, duration, status_code, error)
        
        elapsed_time = time.time() - start_time
        
        # Should complete 1000 requests in reasonable time (< 1 second)
        assert elapsed_time < 1.0
        
        # Verify all requests were recorded
        metrics = collector.get_metrics()
        assert metrics.total_requests == 1000
    
    def test_cors_validation_throughput(self):
        """Benchmark CORS validation throughput."""
        manager = SecurityManager(["https://example.com", "https://app.example.com"])
        
        # Validate 1000 origins and measure time
        start_time = time.time()
        
        for i in range(1000):
            origin = f"https://example{i % 10}.com"
            manager.validate_origin(origin)
        
        elapsed_time = time.time() - start_time
        
        # Should complete 1000 validations in reasonable time (< 0.5 seconds)
        assert elapsed_time < 0.5


class TestResponseTimeDistribution:
    """Analyze response time distribution (p50, p95, p99)."""
    
    def test_metrics_percentile_calculation(self):
        """Test that metrics correctly calculate percentiles."""
        collector = MetricsCollector()
        
        # Record requests with varying response times
        response_times = []
        for i in range(100):
            duration = 50 + (i % 100)  # Range from 50 to 149ms
            response_times.append(duration)
            collector.record_request("/api/test", duration, 200)
        
        metrics = collector.get_metrics()
        
        # Verify percentiles are calculated
        assert metrics.p50_response_time_ms > 0
        assert metrics.p95_response_time_ms > 0
        assert metrics.p99_response_time_ms > 0
        
        # Verify percentile ordering
        assert metrics.p50_response_time_ms <= metrics.p95_response_time_ms
        assert metrics.p95_response_time_ms <= metrics.p99_response_time_ms
        
        # Verify percentiles are within expected range
        assert metrics.p50_response_time_ms >= min(response_times)
        assert metrics.p99_response_time_ms <= max(response_times)


class TestBottleneckIdentification:
    """Identify potential bottlenecks in the system."""
    
    def test_query_engine_performance(self):
        """Benchmark query engine performance."""
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
        
        query_engine = QueryEngine(
            vector_store=mock_vector_store,
            embedding_gen=mock_embedding_gen,
            llm_client=mock_llm_client,
            max_context_tokens=1000
        )
        
        # Measure query execution time
        start_time = time.time()
        
        for i in range(10):
            result = query_engine.query("What is my experience?", n_results=5)
        
        elapsed_time = time.time() - start_time
        avg_time = elapsed_time / 10
        
        # Average query time should be reasonable (< 100ms)
        assert avg_time < 0.1
        
        # Verify results are correct
        assert result.query == "What is my experience?"
        assert len(result.sources) > 0
    
    def test_config_validation_performance(self):
        """Benchmark configuration validation performance."""
        # Create a config
        config = Config(
            llm_provider="openai",
            llm_model="gpt-4",
            openai_api_key="sk-test_key_1234567890"
        )
        
        # Measure validation time
        start_time = time.time()
        
        for i in range(100):
            config.validate()
        
        elapsed_time = time.time() - start_time
        avg_time = elapsed_time / 100
        
        # Average validation time should be very fast (< 1ms)
        assert avg_time < 0.001


class TestMemoryEfficiency:
    """Test memory efficiency of key operations."""
    
    def test_metrics_memory_limit(self):
        """Test that metrics collector respects memory limits."""
        collector = MetricsCollector()
        
        # Record many requests
        for i in range(15000):
            endpoint = f"/api/endpoint{i % 10}"
            duration = 100 + (i % 50)
            collector.record_request(endpoint, duration, 200)
        
        # Metrics should limit stored requests to avoid memory bloat
        # (implementation keeps last 10000)
        metrics = collector.get_metrics()
        
        # Should have recorded requests but not all 15000
        assert metrics.total_requests <= 15000
        assert len(collector.request_metrics) <= 10000


class TestScalability:
    """Test system scalability with increasing load."""
    
    def test_metrics_collection_scalability(self):
        """Test metrics collection scales with request volume."""
        collector = MetricsCollector()
        
        # Record increasing volumes of requests
        volumes = [100, 500, 1000, 5000]
        times = []
        
        for volume in volumes:
            start_time = time.time()
            
            for i in range(volume):
                endpoint = f"/api/endpoint{i % 10}"
                duration = 100 + (i % 50)
                collector.record_request(endpoint, duration, 200)
            
            elapsed_time = time.time() - start_time
            times.append(elapsed_time)
        
        # Time should scale roughly linearly
        # (not exponentially, which would indicate a bottleneck)
        for i in range(1, len(times)):
            # Each 5x increase in volume should result in roughly 5x increase in time
            volume_ratio = volumes[i] / volumes[i-1]
            time_ratio = times[i] / times[i-1]
            
            # Allow some variance (0.5x to 2x the expected ratio)
            assert 0.5 * volume_ratio <= time_ratio <= 2.0 * volume_ratio


class TestConcurrencyPerformance:
    """Test performance under concurrent operations."""
    
    def test_concurrent_cors_validation(self):
        """Test CORS validation performance with concurrent-like operations."""
        manager = SecurityManager(["https://example.com", "https://app.example.com"])
        
        # Simulate concurrent validations
        origins = [
            "https://example.com",
            "https://app.example.com",
            "https://malicious.com",
            "http://example.com",
        ]
        
        start_time = time.time()
        
        for _ in range(250):
            for origin in origins:
                manager.validate_origin(origin)
        
        elapsed_time = time.time() - start_time
        
        # Should handle 1000 validations quickly
        assert elapsed_time < 0.5
    
    def test_concurrent_error_sanitization(self):
        """Test error sanitization performance with concurrent-like operations."""
        manager = SecurityManager([])
        
        errors = [
            Exception("Failed with API key sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"),
            Exception("Database connection failed: postgresql://user:password@localhost"),
            Exception("Authorization failed: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"),
        ]
        
        start_time = time.time()
        
        for _ in range(333):
            for error in errors:
                manager.sanitize_error_message(error)
        
        elapsed_time = time.time() - start_time
        
        # Should handle 1000 sanitizations quickly
        assert elapsed_time < 0.5
