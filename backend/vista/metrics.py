"""Metrics collection for production monitoring."""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict
from statistics import median, quantiles

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    endpoint: str
    duration_ms: float
    status_code: int
    error: Optional[str] = None


@dataclass
class SystemMetrics:
    """Aggregated system metrics."""
    total_requests: int = 0
    total_errors: int = 0
    average_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    error_rate: float = 0.0
    uptime_seconds: float = 0.0
    requests_by_endpoint: Dict[str, int] = field(default_factory=dict)
    errors_by_type: Dict[str, int] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates system metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()
        self.request_metrics: List[RequestMetrics] = []
        self.lock = None  # Can be replaced with threading.Lock if needed
    
    def record_request(self, endpoint: str, duration_ms: float, status_code: int, 
                      error: Optional[str] = None) -> None:
        """Record a request metric.
        
        Args:
            endpoint: API endpoint
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
            error: Error message if request failed
        """
        metric = RequestMetrics(
            endpoint=endpoint,
            duration_ms=duration_ms,
            status_code=status_code,
            error=error
        )
        self.request_metrics.append(metric)
        
        # Keep only last 10000 metrics to avoid memory bloat
        if len(self.request_metrics) > 10000:
            self.request_metrics = self.request_metrics[-10000:]
    
    def get_metrics(self) -> SystemMetrics:
        """Get aggregated system metrics.
        
        Returns:
            SystemMetrics with current aggregated metrics
        """
        if not self.request_metrics:
            return SystemMetrics(uptime_seconds=time.time() - self.start_time)
        
        # Calculate basic metrics
        total_requests = len(self.request_metrics)
        total_errors = sum(1 for m in self.request_metrics if m.error)
        error_rate = total_errors / total_requests if total_requests > 0 else 0.0
        
        # Calculate response time percentiles
        durations = [m.duration_ms for m in self.request_metrics]
        average_response_time = sum(durations) / len(durations) if durations else 0.0
        
        # Calculate percentiles
        p50, p95, p99 = self._calculate_percentiles(durations)
        
        # Count requests by endpoint
        requests_by_endpoint = defaultdict(int)
        for metric in self.request_metrics:
            requests_by_endpoint[metric.endpoint] += 1
        
        # Count errors by type
        errors_by_type = defaultdict(int)
        for metric in self.request_metrics:
            if metric.error:
                errors_by_type[metric.error] += 1
        
        uptime = time.time() - self.start_time
        
        return SystemMetrics(
            total_requests=total_requests,
            total_errors=total_errors,
            average_response_time_ms=average_response_time,
            p50_response_time_ms=p50,
            p95_response_time_ms=p95,
            p99_response_time_ms=p99,
            error_rate=error_rate,
            uptime_seconds=uptime,
            requests_by_endpoint=dict(requests_by_endpoint),
            errors_by_type=dict(errors_by_type)
        )
    
    @staticmethod
    def _calculate_percentiles(values: List[float]) -> tuple:
        """Calculate p50, p95, p99 percentiles.
        
        Args:
            values: List of values to calculate percentiles for
            
        Returns:
            Tuple of (p50, p95, p99)
        """
        if not values:
            return 0.0, 0.0, 0.0
        
        sorted_values = sorted(values)
        
        # Calculate p50 (median)
        p50 = median(sorted_values)
        
        # Calculate p95 and p99 using quantiles
        try:
            # quantiles requires at least 2 values
            if len(sorted_values) >= 2:
                quants = quantiles(sorted_values, n=100)
                p95 = quants[94]  # 95th percentile (index 94 for 100 quantiles)
                p99 = quants[98]  # 99th percentile (index 98 for 100 quantiles)
            else:
                p95 = sorted_values[0]
                p99 = sorted_values[0]
        except Exception:
            # Fallback if quantiles fails
            p95 = sorted_values[-1] if sorted_values else 0.0
            p99 = sorted_values[-1] if sorted_values else 0.0
        
        return p50, p95, p99
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.request_metrics = []
        self.start_time = time.time()
