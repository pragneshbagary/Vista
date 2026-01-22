"""Request timeout handling for production deployments."""

import asyncio
import logging
import time
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class TimeoutConfig:
    """Configuration for request timeout handling."""
    
    # Global timeout settings (in seconds)
    default_timeout: int = 120
    read_timeout: int = 30
    write_timeout: int = 30
    connect_timeout: int = 10
    
    # Per-endpoint timeout overrides
    endpoint_timeouts: dict = field(default_factory=dict)
    
    def get_timeout_for_endpoint(self, endpoint: str) -> int:
        """Get timeout for specific endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Timeout in seconds
        """
        return self.endpoint_timeouts.get(endpoint, self.default_timeout)
    
    def validate(self) -> None:
        """Validate timeout configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        errors = []
        
        if self.default_timeout < 1:
            errors.append(f"default_timeout must be at least 1 second, got {self.default_timeout}")
        
        if self.read_timeout < 1:
            errors.append(f"read_timeout must be at least 1 second, got {self.read_timeout}")
        
        if self.write_timeout < 1:
            errors.append(f"write_timeout must be at least 1 second, got {self.write_timeout}")
        
        if self.connect_timeout < 1:
            errors.append(f"connect_timeout must be at least 1 second, got {self.connect_timeout}")
        
        for endpoint, timeout in self.endpoint_timeouts.items():
            if timeout < 1:
                errors.append(f"Timeout for endpoint {endpoint} must be at least 1 second, got {timeout}")
        
        if errors:
            error_message = "Timeout configuration validation failed:\n"
            for error in errors:
                error_message += f"  - {error}\n"
            raise ValueError(error_message)


@dataclass
class RequestTimeout:
    """Tracks timeout information for a request."""
    
    request_id: str
    endpoint: str
    start_time: float
    timeout_seconds: int
    
    def is_expired(self) -> bool:
        """Check if request has exceeded timeout.
        
        Returns:
            True if request has timed out
        """
        elapsed = time.time() - self.start_time
        return elapsed > self.timeout_seconds
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time for request.
        
        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time
    
    def get_remaining_time(self) -> float:
        """Get remaining time before timeout.
        
        Returns:
            Remaining time in seconds (0 if expired)
        """
        remaining = self.timeout_seconds - self.get_elapsed_time()
        return max(0, remaining)


class RequestTimeoutHandler:
    """Handles request timeout tracking and enforcement."""
    
    def __init__(self, config: TimeoutConfig, logger: Optional[logging.Logger] = None):
        """Initialize request timeout handler.
        
        Args:
            config: TimeoutConfig instance
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.active_requests: dict[str, RequestTimeout] = {}
        self.timeout_events: list[dict] = []
        
        # Validate configuration
        self.config.validate()
    
    def start_request(self, request_id: str, endpoint: str) -> RequestTimeout:
        """Start tracking a request timeout.
        
        Args:
            request_id: Unique request identifier
            endpoint: API endpoint path
            
        Returns:
            RequestTimeout instance
        """
        timeout_seconds = self.config.get_timeout_for_endpoint(endpoint)
        
        request_timeout = RequestTimeout(
            request_id=request_id,
            endpoint=endpoint,
            start_time=time.time(),
            timeout_seconds=timeout_seconds
        )
        
        self.active_requests[request_id] = request_timeout
        self.logger.debug(f"Started tracking request {request_id} with {timeout_seconds}s timeout")
        
        return request_timeout
    
    def end_request(self, request_id: str) -> Optional[RequestTimeout]:
        """Stop tracking a request timeout.
        
        Args:
            request_id: Unique request identifier
            
        Returns:
            RequestTimeout instance or None if not found
        """
        request_timeout = self.active_requests.pop(request_id, None)
        
        if request_timeout:
            elapsed = request_timeout.get_elapsed_time()
            self.logger.debug(f"Ended request {request_id} after {elapsed:.2f}s")
        
        return request_timeout
    
    def check_timeout(self, request_id: str) -> bool:
        """Check if a request has timed out.
        
        Args:
            request_id: Unique request identifier
            
        Returns:
            True if request has timed out
        """
        request_timeout = self.active_requests.get(request_id)
        
        if not request_timeout:
            return False
        
        if request_timeout.is_expired():
            self.logger.warning(
                f"Request {request_id} exceeded timeout of {request_timeout.timeout_seconds}s"
            )
            self._record_timeout_event(request_timeout)
            return True
        
        return False
    
    def get_request_timeout(self, request_id: str) -> Optional[RequestTimeout]:
        """Get timeout information for a request.
        
        Args:
            request_id: Unique request identifier
            
        Returns:
            RequestTimeout instance or None if not found
        """
        return self.active_requests.get(request_id)
    
    def get_active_request_count(self) -> int:
        """Get number of active requests being tracked.
        
        Returns:
            Number of active requests
        """
        return len(self.active_requests)
    
    def get_timeout_events(self) -> list[dict]:
        """Get recorded timeout events.
        
        Returns:
            List of timeout event dictionaries
        """
        return self.timeout_events.copy()
    
    def clear_timeout_events(self) -> None:
        """Clear recorded timeout events."""
        self.timeout_events.clear()
    
    def _record_timeout_event(self, request_timeout: RequestTimeout) -> None:
        """Record a timeout event.
        
        Args:
            request_timeout: RequestTimeout instance
        """
        event = {
            "request_id": request_timeout.request_id,
            "endpoint": request_timeout.endpoint,
            "timeout_seconds": request_timeout.timeout_seconds,
            "elapsed_seconds": request_timeout.get_elapsed_time(),
            "timestamp": datetime.now().isoformat()
        }
        
        self.timeout_events.append(event)
        self.logger.warning(f"Timeout event recorded: {event}")
    
    def get_timeout_statistics(self) -> dict:
        """Get statistics about timeout events.
        
        Returns:
            Dictionary with timeout statistics
        """
        if not self.timeout_events:
            return {
                "total_timeouts": 0,
                "timeouts_by_endpoint": {},
                "average_timeout_seconds": 0
            }
        
        timeouts_by_endpoint = defaultdict(int)
        total_elapsed = 0
        
        for event in self.timeout_events:
            timeouts_by_endpoint[event["endpoint"]] += 1
            total_elapsed += event["elapsed_seconds"]
        
        return {
            "total_timeouts": len(self.timeout_events),
            "timeouts_by_endpoint": dict(timeouts_by_endpoint),
            "average_timeout_seconds": total_elapsed / len(self.timeout_events)
        }


class TimeoutMiddleware:
    """ASGI middleware for request timeout handling."""
    
    def __init__(self, app, timeout_handler: RequestTimeoutHandler):
        """Initialize timeout middleware.
        
        Args:
            app: ASGI application
            timeout_handler: RequestTimeoutHandler instance
        """
        self.app = app
        self.timeout_handler = timeout_handler
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, scope, receive, send):
        """Handle ASGI request with timeout.
        
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
        
        # Start tracking timeout
        request_timeout = self.timeout_handler.start_request(request_id, endpoint)
        
        try:
            # Check timeout before processing
            if self.timeout_handler.check_timeout(request_id):
                await send({
                    "type": "http.response.start",
                    "status": 504,
                    "headers": [[b"content-type", b"application/json"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail": "Request timeout"}',
                })
                return
            
            # Process request with timeout
            await asyncio.wait_for(
                self.app(scope, receive, send),
                timeout=request_timeout.get_remaining_time()
            )
        
        except asyncio.TimeoutError:
            self.logger.error(f"Request {request_id} timed out")
            self.timeout_handler._record_timeout_event(request_timeout)
            
            try:
                await send({
                    "type": "http.response.start",
                    "status": 504,
                    "headers": [[b"content-type", b"application/json"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail": "Request timeout"}',
                })
            except Exception as e:
                self.logger.error(f"Error sending timeout response: {e}")
        
        finally:
            # Stop tracking timeout
            self.timeout_handler.end_request(request_id)
