"""Graceful shutdown handling for production deployments."""

import signal
import asyncio
import logging
from typing import Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ShutdownContext:
    """Context for graceful shutdown."""
    
    is_shutting_down: bool = False
    shutdown_start_time: Optional[datetime] = None
    in_flight_requests: int = 0
    max_shutdown_time: int = 30  # seconds
    
    def is_timeout(self) -> bool:
        """Check if shutdown timeout has been exceeded.
        
        Returns:
            True if shutdown has exceeded max time
        """
        if not self.shutdown_start_time:
            return False
        
        elapsed = (datetime.now() - self.shutdown_start_time).total_seconds()
        return elapsed > self.max_shutdown_time


class GracefulShutdownHandler:
    """Handles graceful shutdown of the application."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize graceful shutdown handler.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.context = ShutdownContext()
        self.cleanup_callbacks: List[Callable] = []
        self.async_cleanup_callbacks: List[Callable] = []
    
    def register_cleanup(self, callback: Callable) -> None:
        """Register a synchronous cleanup callback.
        
        Args:
            callback: Function to call during shutdown
        """
        self.cleanup_callbacks.append(callback)
        self.logger.debug(f"Registered cleanup callback: {callback.__name__}")
    
    def register_async_cleanup(self, callback: Callable) -> None:
        """Register an asynchronous cleanup callback.
        
        Args:
            callback: Async function to call during shutdown
        """
        self.async_cleanup_callbacks.append(callback)
        self.logger.debug(f"Registered async cleanup callback: {callback.__name__}")
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown.
        
        Handles SIGTERM and SIGINT signals.
        """
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
            self.context.is_shutting_down = True
            self.context.shutdown_start_time = datetime.now()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        self.logger.info("Signal handlers registered for graceful shutdown")
    
    def increment_in_flight_requests(self) -> None:
        """Increment in-flight request counter."""
        self.context.in_flight_requests += 1
    
    def decrement_in_flight_requests(self) -> None:
        """Decrement in-flight request counter."""
        if self.context.in_flight_requests > 0:
            self.context.in_flight_requests -= 1
    
    def get_in_flight_requests(self) -> int:
        """Get current number of in-flight requests.
        
        Returns:
            Number of in-flight requests
        """
        return self.context.in_flight_requests
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress.
        
        Returns:
            True if shutdown is in progress
        """
        return self.context.is_shutting_down
    
    async def wait_for_in_flight_requests(self, check_interval: float = 0.1) -> None:
        """Wait for all in-flight requests to complete.
        
        Args:
            check_interval: Time to wait between checks (seconds)
        """
        self.logger.info("Waiting for in-flight requests to complete...")
        
        while self.context.in_flight_requests > 0:
            if self.context.is_timeout():
                self.logger.warning(
                    f"Shutdown timeout exceeded with {self.context.in_flight_requests} "
                    "in-flight requests still pending"
                )
                break
            
            self.logger.debug(f"Waiting for {self.context.in_flight_requests} in-flight requests...")
            await asyncio.sleep(check_interval)
        
        self.logger.info("All in-flight requests completed")
    
    def close_database_connections(self) -> None:
        """Close database connections.
        
        This is a placeholder that can be overridden or extended.
        """
        self.logger.info("Closing database connections...")
        # Actual implementation depends on the database client
    
    async def shutdown(self) -> None:
        """Execute graceful shutdown sequence.
        
        This method:
        1. Waits for in-flight requests to complete
        2. Executes async cleanup callbacks
        3. Executes sync cleanup callbacks
        4. Closes database connections
        """
        self.logger.info("Starting graceful shutdown sequence...")
        
        # Wait for in-flight requests
        await self.wait_for_in_flight_requests()
        
        # Execute async cleanup callbacks
        for callback in self.async_cleanup_callbacks:
            try:
                self.logger.debug(f"Executing async cleanup: {callback.__name__}")
                await callback()
            except Exception as e:
                self.logger.error(f"Error in async cleanup {callback.__name__}: {e}")
        
        # Execute sync cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                self.logger.debug(f"Executing cleanup: {callback.__name__}")
                callback()
            except Exception as e:
                self.logger.error(f"Error in cleanup {callback.__name__}: {e}")
        
        # Close database connections
        try:
            self.close_database_connections()
        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")
        
        self.logger.info("Graceful shutdown completed")
    
    def get_shutdown_status(self) -> dict:
        """Get current shutdown status.
        
        Returns:
            Dictionary with shutdown status information
        """
        elapsed_time = 0
        if self.context.shutdown_start_time:
            elapsed_time = (datetime.now() - self.context.shutdown_start_time).total_seconds()
        
        return {
            "is_shutting_down": self.context.is_shutting_down,
            "in_flight_requests": self.context.in_flight_requests,
            "elapsed_time_seconds": elapsed_time,
            "max_shutdown_time_seconds": self.context.max_shutdown_time,
            "is_timeout": self.context.is_timeout()
        }
