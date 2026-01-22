"""Log aggregation and management for production."""

import logging
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """Represents a single log entry."""
    timestamp: datetime
    level: str
    logger_name: str
    message: str
    request_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "logger_name": self.logger_name,
            "message": self.message,
            "request_id": self.request_id,
            "context": self.context
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class LogStats:
    """Statistics about logs."""
    total_logs: int = 0
    logs_by_level: Dict[str, int] = field(default_factory=dict)
    logs_by_logger: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    debug_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_logs": self.total_logs,
            "logs_by_level": self.logs_by_level,
            "logs_by_logger": self.logs_by_logger,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "debug_count": self.debug_count
        }


class LogAggregator:
    """Aggregates and manages logs."""
    
    def __init__(self, max_logs: int = 50000, retention_days: int = 7):
        """Initialize log aggregator.
        
        Args:
            max_logs: Maximum number of logs to keep in memory
            retention_days: Number of days to retain logs
        """
        self.logger = logging.getLogger(__name__)
        self.max_logs = max_logs
        self.retention_days = retention_days
        self.logs: List[LogEntry] = []
        self.start_time = datetime.utcnow()
    
    def add_log(self, level: str, logger_name: str, message: str,
               request_id: Optional[str] = None, context: Optional[Dict] = None) -> LogEntry:
        """Add a log entry.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            logger_name: Name of the logger
            message: Log message
            request_id: Request ID for tracing
            context: Additional context
            
        Returns:
            LogEntry instance
        """
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            logger_name=logger_name,
            message=message,
            request_id=request_id,
            context=context or {}
        )
        
        self.logs.append(entry)
        
        # Keep only max_logs
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        return entry
    
    def get_stats(self, time_window_minutes: int = 60) -> LogStats:
        """Get log statistics.
        
        Args:
            time_window_minutes: Time window for statistics
            
        Returns:
            LogStats instance
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_logs = [l for l in self.logs if l.timestamp > cutoff_time]
        
        stats = LogStats()
        stats.total_logs = len(self.logs)
        
        # Count logs by level
        logs_by_level = defaultdict(int)
        logs_by_logger = defaultdict(int)
        
        for log in self.logs:
            logs_by_level[log.level] += 1
            logs_by_logger[log.logger_name] += 1
        
        stats.logs_by_level = dict(logs_by_level)
        stats.logs_by_logger = dict(logs_by_logger)
        stats.error_count = logs_by_level.get("ERROR", 0)
        stats.warning_count = logs_by_level.get("WARNING", 0)
        stats.info_count = logs_by_level.get("INFO", 0)
        stats.debug_count = logs_by_level.get("DEBUG", 0)
        
        return stats
    
    def search_logs(self, query: str, limit: int = 100) -> List[LogEntry]:
        """Search logs by message content.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching LogEntry instances
        """
        query_lower = query.lower()
        matching = [
            l for l in self.logs
            if query_lower in l.message.lower() or query_lower in l.logger_name.lower()
        ]
        return matching[-limit:]
    
    def search_by_level(self, level: str, limit: int = 100) -> List[LogEntry]:
        """Search logs by level.
        
        Args:
            level: Log level to filter by
            limit: Maximum number of results
            
        Returns:
            List of matching LogEntry instances
        """
        matching = [l for l in self.logs if l.level == level]
        return matching[-limit:]
    
    def search_by_logger(self, logger_name: str, limit: int = 100) -> List[LogEntry]:
        """Search logs by logger name.
        
        Args:
            logger_name: Logger name to filter by
            limit: Maximum number of results
            
        Returns:
            List of matching LogEntry instances
        """
        matching = [l for l in self.logs if l.logger_name == logger_name]
        return matching[-limit:]
    
    def search_by_request_id(self, request_id: str) -> List[LogEntry]:
        """Search logs by request ID.
        
        Args:
            request_id: Request ID to filter by
            
        Returns:
            List of matching LogEntry instances
        """
        return [l for l in self.logs if l.request_id == request_id]
    
    def get_recent_logs(self, limit: int = 100) -> List[LogEntry]:
        """Get most recent logs.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of LogEntry instances
        """
        return self.logs[-limit:]
    
    def get_errors(self, limit: int = 100) -> List[LogEntry]:
        """Get error logs.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of error LogEntry instances
        """
        errors = [l for l in self.logs if l.level in ("ERROR", "CRITICAL")]
        return errors[-limit:]
    
    def get_warnings(self, limit: int = 100) -> List[LogEntry]:
        """Get warning logs.
        
        Args:
            limit: Maximum number of warnings to return
            
        Returns:
            List of warning LogEntry instances
        """
        warnings = [l for l in self.logs if l.level == "WARNING"]
        return warnings[-limit:]
    
    def clear_old_logs(self, days: Optional[int] = None) -> int:
        """Clear logs older than specified days.
        
        Args:
            days: Number of days to keep (uses retention_days if not specified)
            
        Returns:
            Number of logs removed
        """
        days = days or self.retention_days
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        original_count = len(self.logs)
        self.logs = [l for l in self.logs if l.timestamp > cutoff_time]
        removed = original_count - len(self.logs)
        self.logger.info(f"Cleared {removed} logs older than {days} days")
        return removed
    
    def export_logs(self, filepath: str, format: str = "json") -> int:
        """Export logs to file.
        
        Args:
            filepath: Path to export file
            format: Export format ("json" or "csv")
            
        Returns:
            Number of logs exported
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            if format == "json":
                with open(filepath, 'w') as f:
                    for log in self.logs:
                        f.write(log.to_json() + '\n')
            elif format == "csv":
                import csv
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=["timestamp", "level", "logger_name", "message", "request_id"]
                    )
                    writer.writeheader()
                    for log in self.logs:
                        writer.writerow({
                            "timestamp": log.timestamp.isoformat(),
                            "level": log.level,
                            "logger_name": log.logger_name,
                            "message": log.message,
                            "request_id": log.request_id or ""
                        })
            
            self.logger.info(f"Exported {len(self.logs)} logs to {filepath}")
            return len(self.logs)
        except Exception as e:
            self.logger.error(f"Failed to export logs: {e}")
            return 0
    
    def reset(self) -> None:
        """Reset all logs."""
        self.logs = []
        self.start_time = datetime.utcnow()
        self.logger.info("Log aggregation reset")


class LogSearchEngine:
    """Provides advanced log search capabilities."""
    
    def __init__(self, aggregator: LogAggregator):
        """Initialize log search engine.
        
        Args:
            aggregator: LogAggregator instance
        """
        self.logger = logging.getLogger(__name__)
        self.aggregator = aggregator
    
    def search(self, query: str, level: Optional[str] = None,
              logger_name: Optional[str] = None, limit: int = 100) -> List[LogEntry]:
        """Advanced log search with multiple filters.
        
        Args:
            query: Search query string
            level: Optional log level filter
            logger_name: Optional logger name filter
            limit: Maximum number of results
            
        Returns:
            List of matching LogEntry instances
        """
        results = self.aggregator.search_logs(query, limit=limit * 2)
        
        if level:
            results = [l for l in results if l.level == level]
        
        if logger_name:
            results = [l for l in results if l.logger_name == logger_name]
        
        return results[-limit:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors.
        
        Returns:
            Dictionary with error summary
        """
        errors = self.aggregator.get_errors(limit=1000)
        
        error_types = defaultdict(int)
        error_loggers = defaultdict(int)
        
        for error in errors:
            # Extract error type from message
            if ":" in error.message:
                error_type = error.message.split(":")[0]
            else:
                error_type = "Unknown"
            
            error_types[error_type] += 1
            error_loggers[error.logger_name] += 1
        
        return {
            "total_errors": len(errors),
            "error_types": dict(error_types),
            "error_loggers": dict(error_loggers),
            "recent_errors": [e.to_dict() for e in errors[-10:]]
        }
    
    def get_request_logs(self, request_id: str) -> Dict[str, Any]:
        """Get all logs for a specific request.
        
        Args:
            request_id: Request ID to search for
            
        Returns:
            Dictionary with request logs
        """
        logs = self.aggregator.search_by_request_id(request_id)
        
        return {
            "request_id": request_id,
            "total_logs": len(logs),
            "logs": [l.to_dict() for l in logs],
            "has_errors": any(l.level in ("ERROR", "CRITICAL") for l in logs)
        }


# Global log aggregator instance
_log_aggregator: Optional[LogAggregator] = None
_log_search_engine: Optional[LogSearchEngine] = None


def get_log_aggregator() -> LogAggregator:
    """Get or create global log aggregator.
    
    Returns:
        LogAggregator instance
    """
    global _log_aggregator
    if _log_aggregator is None:
        _log_aggregator = LogAggregator()
    return _log_aggregator


def get_log_search_engine() -> LogSearchEngine:
    """Get or create global log search engine.
    
    Returns:
        LogSearchEngine instance
    """
    global _log_search_engine
    if _log_search_engine is None:
        aggregator = get_log_aggregator()
        _log_search_engine = LogSearchEngine(aggregator)
    return _log_search_engine


def setup_log_aggregation(retention_days: int = 7) -> LogAggregator:
    """Set up log aggregation system.
    
    Args:
        retention_days: Number of days to retain logs
        
    Returns:
        Configured LogAggregator instance
    """
    aggregator = LogAggregator(retention_days=retention_days)
    logger.info(f"Log aggregation system initialized with {retention_days} day retention")
    return aggregator
