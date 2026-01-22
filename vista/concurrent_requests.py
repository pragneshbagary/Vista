"""Concurrent request handling for production deployments."""

import asyncio
import logging
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import time


@dataclass
class ConcurrentRequestConfig:
    """Configuration for concurrent request handling."""
    
    # Worker pool settings
    max_workers: int = 10
    queue_size: int = 100
    
    # Monitoring
    enable_queue_monitoring: bool = True
    queue_warning_threshold: float = 0.8  # Warn when queue is 80% full
    
    def validate(self) -> None:
        """Validate concurrent request configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        errors = []
        
        if self.max_workers < 1:
            errors.append(f"max_workers must be at least 1, got {self.max_workers}")
        
        if self.queue_size < 1:
            errors.append(f"queue_size must be at least 1, got {self.queue_size}")
        
        if not (0 < self.queue_warning_threshold <= 1):
            errors.append(f"queue_warning_threshold must be between 0 and 1, got {self.queue_warning_threshold}")
        
        if errors:
            error_message = "Concurrent request configuration validation failed:\n"
            for error in errors:
                error_message += f"  - {error}\n"
            raise ValueError(error_message)


@dataclass
class QueuedRequest:
    """Represents a queued request."""
    
    request_id: str
    endpoint: str
    enqueue_time: float
    priority: int = 0  # Higher priority = processed first
    
    def get_queue_wait_time(self) -> float:
        """Get time spent in queue.
        
        Returns:
            Time in seconds
        """
        return time.time() - self.enqueue_time


@dataclass
class ConcurrentRequestMetrics:
    """Metrics for concurrent request handling."""
    
    total_requests: int = 0
    active_requests: int = 0
    queued_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    average_queue_wait_ms: float = 0.0
    max_queue_depth: int = 0
    queue_wait_times: list = field(default_factory=list)
    
    def record_queue_wait(self, wait_time_ms: float) -> None:
        """Record queue wait time.
        
        Args:
            wait_time_ms: Wait time in milliseconds
        """
        self.queue_wait_times.append(wait_time_ms)
        
        # Keep only last 1000 measurements
        if len(self.queue_wait_times) > 1000:
            self.queue_wait_times = self.queue_wait_times[-1000:]
        
        # Update average
        if self.queue_wait_times:
            self.average_queue_wait_ms = sum(self.queue_wait_times) / len(self.queue_wait_times)
    
    def to_dict(self) -> dict:
        """Convert metrics to dictionary.
        
        Returns:
            Dictionary representation of metrics
        """
        return {
            "total_requests": self.total_requests,
            "active_requests": self.active_requests,
            "queued_requests": self.queued_requests,
            "completed_requests": self.completed_requests,
            "failed_requests": self.failed_requests,
            "average_queue_wait_ms": self.average_queue_wait_ms,
            "max_queue_depth": self.max_queue_depth
        }


class ConcurrentRequestHandler:
    """Handles concurrent request processing with queuing."""
    
    def __init__(self, config: ConcurrentRequestConfig, logger: Optional[logging.Logger] = None):
        """Initialize concurrent request handler.
        
        Args:
            config: ConcurrentRequestConfig instance
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.metrics = ConcurrentRequestMetrics()
        
        # Request queue
        self.request_queue: asyncio.Queue = asyncio.Queue(maxsize=config.queue_size)
        
        # Active requests tracking
        self.active_requests: dict[str, QueuedRequest] = {}
        
        # Semaphore to limit concurrent requests
        self.semaphore = asyncio.Semaphore(config.max_workers)
        
        # Validate configuration
        self.config.validate()
        
        self.logger.info(
            f"Concurrent request handler initialized with {config.max_workers} workers "
            f"and queue size {config.queue_size}"
        )
    
    async def enqueue_request(self, request_id: str, endpoint: str, priority: int = 0) -> bool:
        """Enqueue a request for processing.
        
        Args:
            request_id: Unique request identifier
            endpoint: API endpoint path
            priority: Request priority (higher = processed first)
            
        Returns:
            True if enqueued successfully, False if queue is full
        """
        queued_request = QueuedRequest(
            request_id=request_id,
            endpoint=endpoint,
            enqueue_time=time.time(),
            priority=priority
        )
        
        try:
            # Try to add to queue without blocking
            self.request_queue.put_nowait(queued_request)
            self.metrics.queued_requests += 1
            self.metrics.total_requests += 1
            
            # Update max queue depth
            if self.request_queue.qsize() > self.metrics.max_queue_depth:
                self.metrics.max_queue_depth = self.request_queue.qsize()
            
            # Check queue warning threshold
            queue_utilization = self.request_queue.qsize() / self.config.queue_size
            if queue_utilization > self.config.queue_warning_threshold:
                self.logger.warning(
                    f"Request queue utilization at {queue_utilization:.1%} "
                    f"({self.request_queue.qsize()}/{self.config.queue_size})"
                )
            
            self.logger.debug(f"Request {request_id} enqueued (queue size: {self.request_queue.qsize()})")
            return True
        
        except asyncio.QueueFull:
            self.logger.error(f"Request queue full, rejecting request {request_id}")
            self.metrics.failed_requests += 1
            return False
    
    async def dequeue_request(self) -> Optional[QueuedRequest]:
        """Dequeue a request for processing.
        
        Returns:
            QueuedRequest instance or None if queue is empty
        """
        try:
            queued_request = self.request_queue.get_nowait()
            self.metrics.queued_requests -= 1
            
            # Record queue wait time
            wait_time_ms = queued_request.get_queue_wait_time() * 1000
            self.metrics.record_queue_wait(wait_time_ms)
            
            self.logger.debug(
                f"Request {queued_request.request_id} dequeued after {wait_time_ms:.1f}ms wait"
            )
            
            return queued_request
        
        except asyncio.QueueEmpty:
            return None
    
    async def process_request(self, request_id: str, endpoint: str, handler: Callable) -> any:
        """Process a request with concurrency control.
        
        Args:
            request_id: Unique request identifier
            endpoint: API endpoint path
            handler: Async function to handle the request
            
        Returns:
            Result from handler function
            
        Raises:
            Exception: If handler raises an exception
        """
        # Acquire semaphore slot
        async with self.semaphore:
            self.metrics.active_requests += 1
            self.active_requests[request_id] = QueuedRequest(
                request_id=request_id,
                endpoint=endpoint,
                enqueue_time=time.time()
            )
            
            try:
                self.logger.debug(f"Processing request {request_id} (active: {self.metrics.active_requests})")
                result = await handler()
                self.metrics.completed_requests += 1
                return result
            
            except Exception as e:
                self.logger.error(f"Error processing request {request_id}: {e}")
                self.metrics.failed_requests += 1
                raise
            
            finally:
                self.metrics.active_requests -= 1
                self.active_requests.pop(request_id, None)
    
    def get_queue_depth(self) -> int:
        """Get current queue depth.
        
        Returns:
            Number of queued requests
        """
        return self.request_queue.qsize()
    
    def get_active_request_count(self) -> int:
        """Get number of active requests.
        
        Returns:
            Number of active requests
        """
        return self.metrics.active_requests
    
    def get_metrics(self) -> ConcurrentRequestMetrics:
        """Get concurrent request metrics.
        
        Returns:
            ConcurrentRequestMetrics instance
        """
        return self.metrics
    
    def get_queue_status(self) -> dict:
        """Get current queue status.
        
        Returns:
            Dictionary with queue status information
        """
        queue_size = self.request_queue.qsize()
        queue_utilization = queue_size / self.config.queue_size
        
        return {
            "queue_size": queue_size,
            "max_queue_size": self.config.queue_size,
            "queue_utilization": queue_utilization,
            "active_requests": self.metrics.active_requests,
            "max_workers": self.config.max_workers,
            "average_queue_wait_ms": self.metrics.average_queue_wait_ms,
            "max_queue_depth": self.metrics.max_queue_depth
        }
    
    async def wait_for_queue_to_drain(self, timeout: int = 30) -> bool:
        """Wait for request queue to drain.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if queue drained, False if timeout exceeded
        """
        start_time = time.time()
        
        while not self.request_queue.empty():
            if time.time() - start_time > timeout:
                self.logger.warning(f"Queue drain timeout after {timeout}s with {self.request_queue.qsize()} requests remaining")
                return False
            
            await asyncio.sleep(0.1)
        
        self.logger.info("Request queue drained successfully")
        return True


class ConcurrencyMiddleware:
    """ASGI middleware for concurrent request handling."""
    
    def __init__(self, app, request_handler: ConcurrentRequestHandler):
        """Initialize concurrency middleware.
        
        Args:
            app: ASGI application
            request_handler: ConcurrentRequestHandler instance
        """
        self.app = app
        self.request_handler = request_handler
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, scope, receive, send):
        """Handle ASGI request with concurrency control.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request_id = scope.get("headers", {}).get(b"x-request-id", b"unknown").decode()
        endpoint = scope.get("path", "unknown")
        
        # Try to enqueue request
        if not await self.request_handler.enqueue_request(request_id, endpoint):
            # Queue is full, return 503 Service Unavailable
            await send({
                "type": "http.response.start",
                "status": 503,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"detail": "Service temporarily unavailable - request queue full"}',
            })
            return
        
        # Process request with concurrency control
        async def handler():
            await self.app(scope, receive, send)
        
        try:
            await self.request_handler.process_request(request_id, endpoint, handler)
        except Exception as e:
            self.logger.error(f"Error processing request {request_id}: {e}")
            raise
