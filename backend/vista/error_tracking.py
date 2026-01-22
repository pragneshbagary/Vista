"""Error tracking and dashboard configuration for production."""

import logging
import traceback
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorEvent:
    """Represents a single error event."""
    error_type: str
    message: str
    timestamp: datetime
    severity: ErrorSeverity
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "request_id": self.request_id,
            "endpoint": self.endpoint,
            "user_id": self.user_id
        }


@dataclass
class ErrorStats:
    """Statistics about errors."""
    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_endpoint: Dict[str, int] = field(default_factory=dict)
    recent_errors: List[ErrorEvent] = field(default_factory=list)
    error_rate_per_minute: float = 0.0
    most_common_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_errors": self.total_errors,
            "errors_by_type": self.errors_by_type,
            "errors_by_severity": self.errors_by_severity,
            "errors_by_endpoint": self.errors_by_endpoint,
            "recent_errors": [e.to_dict() for e in self.recent_errors],
            "error_rate_per_minute": self.error_rate_per_minute,
            "most_common_error": self.most_common_error
        }


class ErrorTracker:
    """Tracks and aggregates error events."""
    
    def __init__(self, max_events: int = 10000):
        """Initialize error tracker.
        
        Args:
            max_events: Maximum number of events to keep in memory
        """
        self.logger = logging.getLogger(__name__)
        self.max_events = max_events
        self.error_events: List[ErrorEvent] = []
        self.start_time = datetime.utcnow()
    
    def track_error(self, error: Exception, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                   context: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None,
                   endpoint: Optional[str] = None, user_id: Optional[str] = None) -> ErrorEvent:
        """Track an error event.
        
        Args:
            error: Exception that occurred
            severity: Error severity level
            context: Additional context information
            request_id: Request ID for tracing
            endpoint: API endpoint where error occurred
            user_id: User ID if applicable
            
        Returns:
            ErrorEvent instance
        """
        error_type = type(error).__name__
        message = str(error)
        stack_trace = traceback.format_exc()
        
        event = ErrorEvent(
            error_type=error_type,
            message=message,
            timestamp=datetime.utcnow(),
            severity=severity,
            stack_trace=stack_trace,
            context=context or {},
            request_id=request_id,
            endpoint=endpoint,
            user_id=user_id
        )
        
        self.error_events.append(event)
        
        # Keep only max_events
        if len(self.error_events) > self.max_events:
            self.error_events = self.error_events[-self.max_events:]
        
        self.logger.error(f"Error tracked: {error_type} - {message}")
        
        return event
    
    def get_stats(self, time_window_minutes: int = 60) -> ErrorStats:
        """Get error statistics.
        
        Args:
            time_window_minutes: Time window for statistics (in minutes)
            
        Returns:
            ErrorStats instance
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_events = [e for e in self.error_events if e.timestamp > cutoff_time]
        
        stats = ErrorStats()
        stats.total_errors = len(self.error_events)
        
        # Count errors by type
        errors_by_type = defaultdict(int)
        errors_by_severity = defaultdict(int)
        errors_by_endpoint = defaultdict(int)
        
        for event in self.error_events:
            errors_by_type[event.error_type] += 1
            errors_by_severity[event.severity] += 1
            if event.endpoint:
                errors_by_endpoint[event.endpoint] += 1
        
        stats.errors_by_type = dict(errors_by_type)
        stats.errors_by_severity = dict(errors_by_severity)
        stats.errors_by_endpoint = dict(errors_by_endpoint)
        
        # Get recent errors (last 100)
        stats.recent_errors = recent_events[-100:]
        
        # Calculate error rate per minute
        if recent_events:
            time_span_minutes = (recent_events[-1].timestamp - recent_events[0].timestamp).total_seconds() / 60
            if time_span_minutes > 0:
                stats.error_rate_per_minute = len(recent_events) / time_span_minutes
        
        # Find most common error
        if errors_by_type:
            stats.most_common_error = max(errors_by_type, key=errors_by_type.get)
        
        return stats
    
    def get_errors_by_type(self, error_type: str, limit: int = 100) -> List[ErrorEvent]:
        """Get errors of a specific type.
        
        Args:
            error_type: Error type to filter by
            limit: Maximum number of errors to return
            
        Returns:
            List of ErrorEvent instances
        """
        matching = [e for e in self.error_events if e.error_type == error_type]
        return matching[-limit:]
    
    def get_errors_by_severity(self, severity: ErrorSeverity, limit: int = 100) -> List[ErrorEvent]:
        """Get errors of a specific severity.
        
        Args:
            severity: Error severity to filter by
            limit: Maximum number of errors to return
            
        Returns:
            List of ErrorEvent instances
        """
        matching = [e for e in self.error_events if e.severity == severity]
        return matching[-limit:]
    
    def get_errors_by_endpoint(self, endpoint: str, limit: int = 100) -> List[ErrorEvent]:
        """Get errors from a specific endpoint.
        
        Args:
            endpoint: Endpoint to filter by
            limit: Maximum number of errors to return
            
        Returns:
            List of ErrorEvent instances
        """
        matching = [e for e in self.error_events if e.endpoint == endpoint]
        return matching[-limit:]
    
    def get_errors_by_request_id(self, request_id: str) -> List[ErrorEvent]:
        """Get all errors for a specific request.
        
        Args:
            request_id: Request ID to filter by
            
        Returns:
            List of ErrorEvent instances
        """
        return [e for e in self.error_events if e.request_id == request_id]
    
    def get_recent_errors(self, limit: int = 100) -> List[ErrorEvent]:
        """Get most recent errors.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of ErrorEvent instances
        """
        return self.error_events[-limit:]
    
    def clear_old_errors(self, days: int = 7) -> int:
        """Clear errors older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of errors removed
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        original_count = len(self.error_events)
        self.error_events = [e for e in self.error_events if e.timestamp > cutoff_time]
        removed = original_count - len(self.error_events)
        self.logger.info(f"Cleared {removed} errors older than {days} days")
        return removed
    
    def reset(self) -> None:
        """Reset all error tracking."""
        self.error_events = []
        self.start_time = datetime.utcnow()
        self.logger.info("Error tracking reset")


class ErrorDashboard:
    """Provides error dashboard data and visualization."""
    
    def __init__(self, error_tracker: ErrorTracker):
        """Initialize error dashboard.
        
        Args:
            error_tracker: ErrorTracker instance
        """
        self.logger = logging.getLogger(__name__)
        self.error_tracker = error_tracker
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data.
        
        Returns:
            Dictionary with dashboard data
        """
        stats = self.error_tracker.get_stats()
        
        return {
            "summary": {
                "total_errors": stats.total_errors,
                "error_rate_per_minute": stats.error_rate_per_minute,
                "most_common_error": stats.most_common_error
            },
            "by_type": stats.errors_by_type,
            "by_severity": stats.errors_by_severity,
            "by_endpoint": stats.errors_by_endpoint,
            "recent_errors": [e.to_dict() for e in stats.recent_errors[-20:]],
            "critical_errors": [
                e.to_dict() for e in self.error_tracker.get_errors_by_severity(ErrorSeverity.CRITICAL, limit=10)
            ]
        }
    
    def get_error_trend(self, hours: int = 24, interval_minutes: int = 60) -> Dict[str, Any]:
        """Get error trend over time.
        
        Args:
            hours: Number of hours to analyze
            interval_minutes: Interval for bucketing errors
            
        Returns:
            Dictionary with error trend data
        """
        now = datetime.utcnow()
        start_time = now - timedelta(hours=hours)
        
        # Create time buckets
        buckets = {}
        current = start_time
        while current < now:
            bucket_key = current.isoformat()
            buckets[bucket_key] = 0
            current += timedelta(minutes=interval_minutes)
        
        # Count errors in each bucket
        for event in self.error_tracker.error_events:
            if event.timestamp >= start_time:
                bucket_time = event.timestamp.replace(
                    minute=(event.timestamp.minute // interval_minutes) * interval_minutes,
                    second=0,
                    microsecond=0
                )
                bucket_key = bucket_time.isoformat()
                if bucket_key in buckets:
                    buckets[bucket_key] += 1
        
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": now.isoformat()
            },
            "interval_minutes": interval_minutes,
            "data": buckets
        }
    
    def get_error_summary_by_type(self) -> List[Dict[str, Any]]:
        """Get error summary grouped by type.
        
        Returns:
            List of error summaries
        """
        stats = self.error_tracker.get_stats()
        summaries = []
        
        for error_type, count in sorted(stats.errors_by_type.items(), key=lambda x: x[1], reverse=True):
            errors = self.error_tracker.get_errors_by_type(error_type, limit=5)
            summaries.append({
                "error_type": error_type,
                "count": count,
                "percentage": (count / stats.total_errors * 100) if stats.total_errors > 0 else 0,
                "recent_examples": [e.to_dict() for e in errors]
            })
        
        return summaries
    
    def get_error_summary_by_endpoint(self) -> List[Dict[str, Any]]:
        """Get error summary grouped by endpoint.
        
        Returns:
            List of error summaries
        """
        stats = self.error_tracker.get_stats()
        summaries = []
        
        for endpoint, count in sorted(stats.errors_by_endpoint.items(), key=lambda x: x[1], reverse=True):
            errors = self.error_tracker.get_errors_by_endpoint(endpoint, limit=5)
            summaries.append({
                "endpoint": endpoint,
                "count": count,
                "percentage": (count / stats.total_errors * 100) if stats.total_errors > 0 else 0,
                "recent_examples": [e.to_dict() for e in errors]
            })
        
        return summaries


# Global error tracker instance
_error_tracker: Optional[ErrorTracker] = None
_error_dashboard: Optional[ErrorDashboard] = None


def get_error_tracker() -> ErrorTracker:
    """Get or create global error tracker.
    
    Returns:
        ErrorTracker instance
    """
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


def get_error_dashboard() -> ErrorDashboard:
    """Get or create global error dashboard.
    
    Returns:
        ErrorDashboard instance
    """
    global _error_dashboard
    if _error_dashboard is None:
        tracker = get_error_tracker()
        _error_dashboard = ErrorDashboard(tracker)
    return _error_dashboard


def setup_error_tracking() -> ErrorTracker:
    """Set up error tracking system.
    
    Returns:
        Configured ErrorTracker instance
    """
    tracker = get_error_tracker()
    logger.info("Error tracking system initialized")
    return tracker
