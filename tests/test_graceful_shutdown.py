"""Tests for graceful shutdown handling."""

import pytest
import asyncio
import logging
from datetime import datetime, timedelta
from vista.graceful_shutdown import GracefulShutdownHandler, ShutdownContext


class TestShutdownContext:
    """Tests for ShutdownContext class."""
    
    def test_default_context(self):
        """Test default shutdown context."""
        context = ShutdownContext()
        
        assert context.is_shutting_down is False
        assert context.shutdown_start_time is None
        assert context.in_flight_requests == 0
        assert context.max_shutdown_time == 30
    
    def test_is_timeout_not_started(self):
        """Test timeout check when shutdown not started."""
        context = ShutdownContext()
        
        assert context.is_timeout() is False
    
    def test_is_timeout_within_limit(self):
        """Test timeout check within time limit."""
        context = ShutdownContext(
            shutdown_start_time=datetime.now(),
            max_shutdown_time=30
        )
        
        assert context.is_timeout() is False
    
    def test_is_timeout_exceeded(self):
        """Test timeout check when exceeded."""
        context = ShutdownContext(
            shutdown_start_time=datetime.now() - timedelta(seconds=35),
            max_shutdown_time=30
        )
        
        assert context.is_timeout() is True


class TestGracefulShutdownHandler:
    """Tests for GracefulShutdownHandler class."""
    
    def test_handler_initialization(self):
        """Test handler initialization."""
        handler = GracefulShutdownHandler()
        
        assert handler.context.is_shutting_down is False
        assert handler.context.in_flight_requests == 0
        assert len(handler.cleanup_callbacks) == 0
        assert len(handler.async_cleanup_callbacks) == 0
    
    def test_register_cleanup_callback(self):
        """Test registering cleanup callback."""
        handler = GracefulShutdownHandler()
        
        def cleanup():
            pass
        
        handler.register_cleanup(cleanup)
        
        assert len(handler.cleanup_callbacks) == 1
        assert handler.cleanup_callbacks[0] == cleanup
    
    def test_register_async_cleanup_callback(self):
        """Test registering async cleanup callback."""
        handler = GracefulShutdownHandler()
        
        async def async_cleanup():
            pass
        
        handler.register_async_cleanup(async_cleanup)
        
        assert len(handler.async_cleanup_callbacks) == 1
        assert handler.async_cleanup_callbacks[0] == async_cleanup
    
    def test_increment_in_flight_requests(self):
        """Test incrementing in-flight requests."""
        handler = GracefulShutdownHandler()
        
        handler.increment_in_flight_requests()
        assert handler.get_in_flight_requests() == 1
        
        handler.increment_in_flight_requests()
        assert handler.get_in_flight_requests() == 2
    
    def test_decrement_in_flight_requests(self):
        """Test decrementing in-flight requests."""
        handler = GracefulShutdownHandler()
        handler.increment_in_flight_requests()
        handler.increment_in_flight_requests()
        
        handler.decrement_in_flight_requests()
        assert handler.get_in_flight_requests() == 1
        
        handler.decrement_in_flight_requests()
        assert handler.get_in_flight_requests() == 0
    
    def test_decrement_in_flight_requests_below_zero(self):
        """Test decrementing in-flight requests doesn't go below zero."""
        handler = GracefulShutdownHandler()
        
        handler.decrement_in_flight_requests()
        assert handler.get_in_flight_requests() == 0
    
    def test_is_shutting_down(self):
        """Test shutdown status check."""
        handler = GracefulShutdownHandler()
        
        assert handler.is_shutting_down() is False
        
        handler.context.is_shutting_down = True
        assert handler.is_shutting_down() is True
    
    def test_wait_for_in_flight_requests_none(self):
        """Test waiting when no in-flight requests."""
        handler = GracefulShutdownHandler()
        
        # Should complete immediately
        import asyncio
        asyncio.run(handler.wait_for_in_flight_requests())
    
    def test_wait_for_in_flight_requests_with_requests(self):
        """Test waiting for in-flight requests to complete."""
        handler = GracefulShutdownHandler()
        handler.increment_in_flight_requests()
        handler.increment_in_flight_requests()
        
        # Decrement requests after a delay
        async def decrement_later():
            await asyncio.sleep(0.1)
            handler.decrement_in_flight_requests()
            handler.decrement_in_flight_requests()
        
        # Run both concurrently
        import asyncio
        async def run_test():
            await asyncio.gather(
                handler.wait_for_in_flight_requests(),
                decrement_later()
            )
        
        asyncio.run(run_test())
        
        assert handler.get_in_flight_requests() == 0
    
    def test_shutdown_sequence(self):
        """Test complete shutdown sequence."""
        handler = GracefulShutdownHandler()
        
        cleanup_called = []
        async_cleanup_called = []
        
        def sync_cleanup():
            cleanup_called.append(True)
        
        async def async_cleanup():
            async_cleanup_called.append(True)
        
        handler.register_cleanup(sync_cleanup)
        handler.register_async_cleanup(async_cleanup)
        
        import asyncio
        asyncio.run(handler.shutdown())
        
        assert len(cleanup_called) == 1
        assert len(async_cleanup_called) == 1
    
    def test_shutdown_with_error_in_cleanup(self):
        """Test shutdown continues even if cleanup fails."""
        handler = GracefulShutdownHandler()
        
        cleanup_called = []
        
        def failing_cleanup():
            raise Exception("Cleanup failed")
        
        def normal_cleanup():
            cleanup_called.append(True)
        
        handler.register_cleanup(failing_cleanup)
        handler.register_cleanup(normal_cleanup)
        
        # Should not raise
        import asyncio
        asyncio.run(handler.shutdown())
        
        # Normal cleanup should still be called
        assert len(cleanup_called) == 1
    
    def test_get_shutdown_status(self):
        """Test getting shutdown status."""
        handler = GracefulShutdownHandler()
        handler.context.is_shutting_down = True
        handler.context.shutdown_start_time = datetime.now()
        handler.increment_in_flight_requests()
        
        status = handler.get_shutdown_status()
        
        assert status["is_shutting_down"] is True
        assert status["in_flight_requests"] == 1
        assert status["elapsed_time_seconds"] >= 0
        assert status["max_shutdown_time_seconds"] == 30
    
    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        handler = GracefulShutdownHandler()
        
        # Should not raise
        handler.setup_signal_handlers()
    
    def test_wait_for_in_flight_requests_timeout(self):
        """Test timeout when waiting for in-flight requests."""
        handler = GracefulShutdownHandler()
        handler.context.max_shutdown_time = 1
        handler.context.shutdown_start_time = datetime.now() - timedelta(seconds=2)
        handler.increment_in_flight_requests()
        
        # Should complete even though request is still in flight
        import asyncio
        asyncio.run(handler.wait_for_in_flight_requests())
        
        # Request should still be in flight
        assert handler.get_in_flight_requests() == 1
