"""Performance monitoring for production."""

import logging
import time
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from statistics import mean, median

logger = logging.getLogger(__name__)

# Try to import psutil, but make it optional
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not installed - resource monitoring will be limited")


@dataclass
class PerformanceMetric:
    """Represents a single performance metric."""
    endpoint: str
    response_time_ms: float
    timestamp: datetime
    status_code: int
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "endpoint": self.endpoint,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.status_code,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_percent": self.cpu_percent
        }


@dataclass
class PerformanceStats:
    """Statistics about performance."""
    endpoint: str
    total_requests: int = 0
    average_response_time_ms: float = 0.0
    median_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    error_rate: float = 0.0
    average_memory_usage_mb: float = 0.0
    average_cpu_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "endpoint": self.endpoint,
            "total_requests": self.total_requests,
            "average_response_time_ms": self.average_response_time_ms,
            "median_response_time_ms": self.median_response_time_ms,
            "p95_response_time_ms": self.p95_response_time_ms,
            "p99_response_time_ms": self.p99_response_time_ms,
            "min_response_time_ms": self.min_response_time_ms,
            "max_response_time_ms": self.max_response_time_ms,
            "error_rate": self.error_rate,
            "average_memory_usage_mb": self.average_memory_usage_mb,
            "average_cpu_percent": self.average_cpu_percent
        }


@dataclass
class ResourceUsage:
    """System resource usage."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_percent: float
    disk_mb_free: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_mb": self.memory_mb,
            "disk_percent": self.disk_percent,
            "disk_mb_free": self.disk_mb_free
        }


class PerformanceMonitor:
    """Monitors application performance metrics."""
    
    def __init__(self, max_metrics: int = 10000):
        """Initialize performance monitor.
        
        Args:
            max_metrics: Maximum number of metrics to keep in memory
        """
        self.logger = logging.getLogger(__name__)
        self.max_metrics = max_metrics
        self.metrics: List[PerformanceMetric] = []
        self.resource_history: List[ResourceUsage] = []
        self.start_time = datetime.utcnow()
        self.process = psutil.Process(os.getpid()) if HAS_PSUTIL else None
    
    def record_metric(self, endpoint: str, response_time_ms: float, status_code: int) -> PerformanceMetric:
        """Record a performance metric.
        
        Args:
            endpoint: API endpoint
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            
        Returns:
            PerformanceMetric instance
        """
        # Get resource usage
        memory_mb = 0.0
        cpu_percent = 0.0
        
        if HAS_PSUTIL and self.process:
            try:
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                cpu_percent = self.process.cpu_percent(interval=0.1)
            except Exception as e:
                self.logger.debug(f"Failed to get resource usage: {e}")
        
        metric = PerformanceMetric(
            endpoint=endpoint,
            response_time_ms=response_time_ms,
            timestamp=datetime.utcnow(),
            status_code=status_code,
            memory_usage_mb=memory_mb,
            cpu_percent=cpu_percent
        )
        
        self.metrics.append(metric)
        
        # Keep only max_metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
        
        return metric
    
    def get_stats_for_endpoint(self, endpoint: str) -> PerformanceStats:
        """Get performance statistics for an endpoint.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            PerformanceStats instance
        """
        endpoint_metrics = [m for m in self.metrics if m.endpoint == endpoint]
        
        if not endpoint_metrics:
            return PerformanceStats(endpoint=endpoint)
        
        response_times = [m.response_time_ms for m in endpoint_metrics]
        error_count = sum(1 for m in endpoint_metrics if m.status_code >= 400)
        memory_usages = [m.memory_usage_mb for m in endpoint_metrics if m.memory_usage_mb > 0]
        cpu_percents = [m.cpu_percent for m in endpoint_metrics if m.cpu_percent > 0]
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        
        stats = PerformanceStats(
            endpoint=endpoint,
            total_requests=len(endpoint_metrics),
            average_response_time_ms=mean(response_times),
            median_response_time_ms=median(response_times),
            p95_response_time_ms=sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1],
            p99_response_time_ms=sorted_times[p99_idx] if p99_idx < len(sorted_times) else sorted_times[-1],
            min_response_time_ms=min(response_times),
            max_response_time_ms=max(response_times),
            error_rate=error_count / len(endpoint_metrics) if endpoint_metrics else 0.0,
            average_memory_usage_mb=mean(memory_usages) if memory_usages else 0.0,
            average_cpu_percent=mean(cpu_percents) if cpu_percents else 0.0
        )
        
        return stats
    
    def get_all_stats(self) -> Dict[str, PerformanceStats]:
        """Get performance statistics for all endpoints.
        
        Returns:
            Dictionary mapping endpoint to PerformanceStats
        """
        endpoints = set(m.endpoint for m in self.metrics)
        return {endpoint: self.get_stats_for_endpoint(endpoint) for endpoint in endpoints}
    
    def get_slowest_endpoints(self, limit: int = 10) -> List[PerformanceStats]:
        """Get slowest endpoints by average response time.
        
        Args:
            limit: Maximum number of endpoints to return
            
        Returns:
            List of PerformanceStats sorted by response time
        """
        all_stats = self.get_all_stats()
        sorted_stats = sorted(all_stats.values(), key=lambda s: s.average_response_time_ms, reverse=True)
        return sorted_stats[:limit]
    
    def get_error_prone_endpoints(self, limit: int = 10) -> List[PerformanceStats]:
        """Get endpoints with highest error rates.
        
        Args:
            limit: Maximum number of endpoints to return
            
        Returns:
            List of PerformanceStats sorted by error rate
        """
        all_stats = self.get_all_stats()
        sorted_stats = sorted(all_stats.values(), key=lambda s: s.error_rate, reverse=True)
        return sorted_stats[:limit]
    
    def record_resource_usage(self) -> ResourceUsage:
        """Record current system resource usage.
        
        Returns:
            ResourceUsage instance
        """
        if not HAS_PSUTIL:
            return None
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            usage = ResourceUsage(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory.used / 1024 / 1024,
                disk_percent=disk.percent,
                disk_mb_free=disk.free / 1024 / 1024
            )
            
            self.resource_history.append(usage)
            
            # Keep only last 1000 records
            if len(self.resource_history) > 1000:
                self.resource_history = self.resource_history[-1000:]
            
            return usage
        except Exception as e:
            self.logger.error(f"Failed to record resource usage: {e}")
            return None
    
    def get_resource_stats(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get resource usage statistics.
        
        Args:
            time_window_minutes: Time window for statistics
            
        Returns:
            Dictionary with resource statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_usage = [u for u in self.resource_history if u.timestamp > cutoff_time]
        
        if not recent_usage:
            return {
                "cpu_percent_avg": 0.0,
                "memory_percent_avg": 0.0,
                "disk_percent_avg": 0.0
            }
        
        cpu_percents = [u.cpu_percent for u in recent_usage]
        memory_percents = [u.memory_percent for u in recent_usage]
        disk_percents = [u.disk_percent for u in recent_usage]
        
        return {
            "cpu_percent_avg": mean(cpu_percents),
            "cpu_percent_max": max(cpu_percents),
            "memory_percent_avg": mean(memory_percents),
            "memory_percent_max": max(memory_percents),
            "disk_percent_avg": mean(disk_percents),
            "disk_percent_max": max(disk_percents),
            "memory_mb_avg": mean([u.memory_mb for u in recent_usage]),
            "disk_mb_free_min": min([u.disk_mb_free for u in recent_usage])
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report.
        
        Returns:
            Dictionary with performance report
        """
        all_stats = self.get_all_stats()
        resource_stats = self.get_resource_stats()
        
        total_requests = sum(s.total_requests for s in all_stats.values())
        total_errors = sum(int(s.total_requests * s.error_rate) for s in all_stats.values())
        
        return {
            "summary": {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "overall_error_rate": total_errors / total_requests if total_requests > 0 else 0.0,
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
            },
            "endpoints": {endpoint: stats.to_dict() for endpoint, stats in all_stats.items()},
            "slowest_endpoints": [s.to_dict() for s in self.get_slowest_endpoints(5)],
            "error_prone_endpoints": [s.to_dict() for s in self.get_error_prone_endpoints(5)],
            "resources": resource_stats
        }
    
    def reset(self) -> None:
        """Reset all performance metrics."""
        self.metrics = []
        self.resource_history = []
        self.start_time = datetime.utcnow()
        self.logger.info("Performance metrics reset")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor.
    
    Returns:
        PerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def setup_performance_monitoring() -> PerformanceMonitor:
    """Set up performance monitoring system.
    
    Returns:
        Configured PerformanceMonitor instance
    """
    monitor = get_performance_monitor()
    logger.info("Performance monitoring system initialized")
    return monitor
