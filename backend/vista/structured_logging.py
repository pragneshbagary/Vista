"""Structured logging for production monitoring."""

import logging
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar

# Context variable for request ID
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def get_request_id() -> str:
    """Get current request ID or generate a new one.
    
    Returns:
        Request ID string
    """
    request_id = request_id_context.get()
    if not request_id:
        request_id = str(uuid.uuid4())
        request_id_context.set(request_id)
    return request_id


def set_request_id(request_id: str) -> None:
    """Set request ID for current context.
    
    Args:
        request_id: Request ID to set
    """
    request_id_context.set(request_id)


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class StructuredLogger:
    """Wrapper around standard logger for structured logging."""
    
    def __init__(self, name: str):
        """Initialize structured logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
    
    def info(self, message: str) -> None:
        """Log info message.
        
        Args:
            message: Message to log
        """
        self.logger.info(message)
    
    def error(self, message: str) -> None:
        """Log error message.
        
        Args:
            message: Message to log
        """
        self.logger.error(message)
    
    def warning(self, message: str) -> None:
        """Log warning message.
        
        Args:
            message: Message to log
        """
        self.logger.warning(message)
    
    def debug(self, message: str) -> None:
        """Log debug message.
        
        Args:
            message: Message to log
        """
        self.logger.debug(message)
    
    def log_request(self, method: str, path: str, query_params: Optional[Dict] = None) -> None:
        """Log incoming request.
        
        Args:
            method: HTTP method
            path: Request path
            query_params: Query parameters
        """
        extra_fields = {
            "event_type": "request",
            "method": method,
            "path": path,
        }
        if query_params:
            extra_fields["query_params"] = query_params
        
        self._log_with_extra("info", f"Incoming request: {method} {path}", extra_fields)
    
    def log_response(self, status_code: int, duration_ms: float, path: str) -> None:
        """Log outgoing response.
        
        Args:
            status_code: HTTP status code
            duration_ms: Response duration in milliseconds
            path: Request path
        """
        extra_fields = {
            "event_type": "response",
            "status_code": status_code,
            "duration_ms": duration_ms,
            "path": path,
        }
        
        self._log_with_extra("info", f"Response: {status_code} ({duration_ms:.2f}ms)", extra_fields)
    
    def log_error(self, error: Exception, context: Optional[Dict] = None) -> None:
        """Log error with context.
        
        Args:
            error: Exception that occurred
            context: Additional context information
        """
        extra_fields = {
            "event_type": "error",
            "error_type": type(error).__name__,
        }
        if context:
            extra_fields.update(context)
        
        self._log_with_extra("error", f"Error: {str(error)}", extra_fields, exc_info=True)
    
    def log_security_event(self, event_type: str, details: Optional[Dict] = None) -> None:
        """Log security-relevant events.
        
        Args:
            event_type: Type of security event
            details: Additional details about the event
        """
        extra_fields = {
            "event_type": f"security_{event_type}",
        }
        if details:
            extra_fields.update(details)
        
        self._log_with_extra("warning", f"Security event: {event_type}", extra_fields)
    
    def log_component_health(self, component: str, status: str, details: Optional[Dict] = None) -> None:
        """Log component health status.
        
        Args:
            component: Component name
            status: Health status
            details: Additional details
        """
        extra_fields = {
            "event_type": "component_health",
            "component": component,
            "status": status,
        }
        if details:
            extra_fields.update(details)
        
        self._log_with_extra("info", f"Component health: {component} = {status}", extra_fields)
    
    def _log_with_extra(self, level: str, message: str, extra_fields: Dict[str, Any], 
                       exc_info: bool = False) -> None:
        """Log with extra fields.
        
        Args:
            level: Log level
            message: Log message
            extra_fields: Extra fields to include
            exc_info: Whether to include exception info
        """
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.upper()),
            "(unknown file)",
            0,
            message,
            (),
            None
        )
        record.extra_fields = extra_fields
        
        if exc_info:
            import sys
            record.exc_info = sys.exc_info()
        
        self.logger.handle(record)


def setup_structured_logging(log_level: str = "info") -> None:
    """Set up structured logging for the application.
    
    Args:
        log_level: Logging level (debug, info, warning, error, critical)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with structured formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)
