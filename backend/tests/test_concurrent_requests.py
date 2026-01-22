"""Tests for concurrent request handling."""

import pytest
import asyncio
from vista.concurrent_requests import (
    ConcurrentRequestConfig,
    QueuedRequest,
    ConcurrentRequestMetrics,
    ConcurrentRequestHandler
)


class TestConcurrentRequestConfig:
    """Tests for ConcurrentRequestConfig class."""
    
    def test_default_config(self):
        """Test default concurrent request configuration."""
        config = ConcurrentRequestConfig()
        
        assert config.max_workers == 10
        assert config.queue_size == 100
        assert config.enable_queue_monitoring is True
        assert config.queue_warning_threshold == 0.8
    
    def test_validation_invalid_max_workers(self):
        """Test validation fails with invalid max workers."""
        config = ConcurrentRequestConfig(max_workers=0)
        
        with pytest.raises(ValueError, match="max_workers must be at least 1"):
            config.validate()
    
    def test_validation_invalid_queue_size(self):
        """Test validation fails with invalid queue size."""
        config = ConcurrentRequestConfig(queue_size=0)
        
        with pytest.raises(ValueError, match="queue_size must be at least 1"):
            config.validate()
    
    def test_validation_invalid_queue_warning_threshold(self):
        """Test validation fails with invalid warning threshold."""
        config = ConcurrentRequestConfig(queue_warning_threshold=1.5)
        
        with pytest.raises(ValueError, match="queue_warning_threshold must be between 0 and 1"):
            config.validate()
    
    def test_validation_invalid_queue_warning_threshold_zero(self):
        """Test validation fails with zero warning threshold."""
        config = ConcurrentRequestConfig(queue_warning_threshold=0)
        
        with pytest.raises(ValueError, match="queue_warning_threshold must be between 0 and 1"):
            config.validate()


class TestQueuedRequest:
    """Tests for QueuedRequest class."""
    
    def test_queued_request_creation(self):
        """Test creating queued request."""
        import time
        enqueue_time = time.time()
        request = QueuedRequest(
            request_id="req-123",
            endpoint="/api/chat",
            enqueue_time=enqueue_time,
            priority=1
        )
        
        assert request.request_id == "req-123"
        assert request.endpoint == "/api/chat"
        assert request.priority == 1
    
    def test_get_queue_wait_time(self):
        """Test getting queue wait time."""
        import time
        enqueue_time = time.time() - 5  # 5 seconds ago
        request = QueuedRequest(
            request_id="req-123",
            endpoint="/api/chat",
            enqueue_time=enqueue_time
        )
        
        wait_time = request.get_queue_wait_time()
        assert 4.9 < wait_time < 5.1  # Allow small variance


class TestConcurrentRequestMetrics:
    """Tests for ConcurrentRequestMetrics class."""
    
    def test_default_metrics(self):
        """Test default metrics."""
        metrics = ConcurrentRequestMetrics()
        
        assert metrics.total_requests == 0
        assert metrics.active_requests == 0
        assert metrics.queued_requests == 0
        assert metrics.completed_requests == 0
        assert metrics.failed_requests == 0
    
    def test_record_queue_wait(self):
        """Test recording queue wait time."""
        metrics = ConcurrentRequestMetrics()
        
        metrics.record_queue_wait(10.5)
        metrics.record_queue_wait(20.3)
        
        assert len(metrics.queue_wait_times) == 2
        assert metrics.average_queue_wait_ms == pytest.approx(15.4)
    
    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ConcurrentRequestMetrics(
            total_requests=100,
            active_requests=5,
            queued_requests=10
        )
        
        data = metrics.to_dict()
        
        assert data["total_requests"] == 100
        assert data["active_requests"] == 5
        assert data["queued_requests"] == 10


class TestConcurrentRequestHandler:
    """Tests for ConcurrentRequestHandler class."""
    
    def test_handler_initialization(self):
        """Test handler initialization."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        assert handler.get_queue_depth() == 0
        assert handler.get_active_request_count() == 0
    
    def test_enqueue_request(self):
        """Test enqueuing a request."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            result = await handler.enqueue_request("req-123", "/api/chat")
            return result
        
        import asyncio
        result = asyncio.run(run_test())
        
        assert result is True
        assert handler.get_queue_depth() == 1
    
    def test_enqueue_request_queue_full(self):
        """Test enqueuing when queue is full."""
        config = ConcurrentRequestConfig(queue_size=2)
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            # Fill the queue
            await handler.enqueue_request("req-1", "/api/chat")
            await handler.enqueue_request("req-2", "/api/chat")
            
            # Try to add one more
            result = await handler.enqueue_request("req-3", "/api/chat")
            return result
        
        import asyncio
        result = asyncio.run(run_test())
        
        assert result is False
        assert handler.get_queue_depth() == 2
    
    def test_dequeue_request(self):
        """Test dequeuing a request."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            await handler.enqueue_request("req-123", "/api/chat")
            queued_request = await handler.dequeue_request()
            return queued_request
        
        import asyncio
        queued_request = asyncio.run(run_test())
        
        assert queued_request is not None
        assert queued_request.request_id == "req-123"
        assert handler.get_queue_depth() == 0
    
    def test_dequeue_request_empty_queue(self):
        """Test dequeuing from empty queue."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            queued_request = await handler.dequeue_request()
            return queued_request
        
        import asyncio
        queued_request = asyncio.run(run_test())
        
        assert queued_request is None
    
    def test_process_request(self):
        """Test processing a request."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            async def mock_handler():
                return "success"
            
            result = await handler.process_request("req-123", "/api/chat", mock_handler)
            return result
        
        import asyncio
        result = asyncio.run(run_test())
        
        assert result == "success"
        assert handler.get_active_request_count() == 0
        assert handler.get_metrics().completed_requests == 1
    
    def test_process_request_with_error(self):
        """Test processing request that raises error."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            async def failing_handler():
                raise ValueError("Test error")
            
            try:
                await handler.process_request("req-123", "/api/chat", failing_handler)
            except ValueError:
                pass
        
        import asyncio
        asyncio.run(run_test())
        
        assert handler.get_active_request_count() == 0
        assert handler.get_metrics().failed_requests == 1
    
    def test_process_request_concurrency_limit(self):
        """Test that concurrency is limited by max workers."""
        config = ConcurrentRequestConfig(max_workers=2)
        handler = ConcurrentRequestHandler(config)
        
        active_counts = []
        
        async def run_test():
            async def mock_handler():
                active_counts.append(handler.get_active_request_count())
                await asyncio.sleep(0.1)
            
            # Process 4 requests concurrently
            tasks = [
                handler.process_request(f"req-{i}", "/api/chat", mock_handler)
                for i in range(4)
            ]
            
            await asyncio.gather(*tasks)
        
        import asyncio
        asyncio.run(run_test())
        
        # Max active should not exceed 2
        assert max(active_counts) <= 2
    
    def test_get_queue_status(self):
        """Test getting queue status."""
        config = ConcurrentRequestConfig(queue_size=100)
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            await handler.enqueue_request("req-1", "/api/chat")
            await handler.enqueue_request("req-2", "/api/chat")
        
        import asyncio
        asyncio.run(run_test())
        
        status = handler.get_queue_status()
        
        assert status["queue_size"] == 2
        assert status["max_queue_size"] == 100
        assert status["queue_utilization"] == 0.02
        assert status["active_requests"] == 0
    
    def test_get_metrics(self):
        """Test getting metrics."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            async def mock_handler():
                pass
            
            await handler.process_request("req-1", "/api/chat", mock_handler)
        
        import asyncio
        asyncio.run(run_test())
        
        metrics = handler.get_metrics()
        
        assert metrics.completed_requests == 1
    
    def test_wait_for_queue_to_drain(self):
        """Test waiting for queue to drain."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            await handler.enqueue_request("req-1", "/api/chat")
            
            # Dequeue in background
            async def dequeue_later():
                await asyncio.sleep(0.1)
                await handler.dequeue_request()
            
            # Wait for queue to drain
            task1 = asyncio.create_task(handler.wait_for_queue_to_drain())
            task2 = asyncio.create_task(dequeue_later())
            
            result = await asyncio.gather(task1, task2)
            return result[0]
        
        import asyncio
        result = asyncio.run(run_test())
        
        assert result is True
    
    def test_wait_for_queue_to_drain_timeout(self):
        """Test queue drain timeout."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            await handler.enqueue_request("req-1", "/api/chat")
            
            # Don't dequeue, so queue never drains
            result = await handler.wait_for_queue_to_drain(timeout=1)
            return result
        
        import asyncio
        result = asyncio.run(run_test())
        
        assert result is False
    
    def test_max_queue_depth_tracking(self):
        """Test tracking maximum queue depth."""
        config = ConcurrentRequestConfig()
        handler = ConcurrentRequestHandler(config)
        
        async def run_test():
            for i in range(5):
                await handler.enqueue_request(f"req-{i}", "/api/chat")
        
        import asyncio
        asyncio.run(run_test())
        
        metrics = handler.get_metrics()
        assert metrics.max_queue_depth == 5
