"""Health check system for production monitoring."""

import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    response_time_ms: float
    error_message: Optional[str] = None
    last_check: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class HealthCheckResponse:
    """Overall health check response."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    components: Dict[str, Dict[str, Any]]
    message: Optional[str] = None
    uptime_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class HealthChecker:
    """Manages health checks for system components."""
    
    def __init__(self, query_engine=None, vector_store=None, llm_client=None):
        """Initialize health checker with system components.
        
        Args:
            query_engine: QueryEngine instance
            vector_store: VectorStoreManager instance
            llm_client: LLM client instance
        """
        self.query_engine = query_engine
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.start_time = time.time()
        self.logger = logging.getLogger(__name__)
    
    def check_health(self) -> HealthCheckResponse:
        """Check overall system health.
        
        Returns:
            HealthCheckResponse with overall status and component details
        """
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        # Check each component
        api_health = self._check_api_health()
        components["api"] = api_health.to_dict()
        
        db_health = self._check_database_health()
        components["database"] = db_health.to_dict()
        
        llm_health = self._check_llm_health()
        components["llm"] = llm_health.to_dict()
        
        # Determine overall status
        for component in components.values():
            if component["status"] == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            elif component["status"] == HealthStatus.DEGRADED:
                if overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        uptime = time.time() - self.start_time
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            components=components,
            message=self._get_status_message(overall_status),
            uptime_seconds=uptime
        )
    
    def _check_api_health(self) -> ComponentHealth:
        """Check API component health.
        
        Returns:
            ComponentHealth for API
        """
        start = time.time()
        
        try:
            # API is healthy if we can reach this point
            response_time = (time.time() - start) * 1000
            
            return ComponentHealth(
                name="api",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow().isoformat()
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            self.logger.error(f"API health check failed: {e}")
            
            return ComponentHealth(
                name="api",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=str(e),
                last_check=datetime.utcnow().isoformat()
            )
    
    def _check_database_health(self) -> ComponentHealth:
        """Check database component health.
        
        Returns:
            ComponentHealth for database
        """
        start = time.time()
        
        try:
            if not self.vector_store:
                response_time = (time.time() - start) * 1000
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    error_message="Vector store not initialized",
                    last_check=datetime.utcnow().isoformat()
                )
            
            # Try to get collection count
            count = self.vector_store.get_collection_count()
            response_time = (time.time() - start) * 1000
            
            # Database is healthy if we can query it
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow().isoformat()
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            self.logger.error(f"Database health check failed: {e}")
            
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=str(e),
                last_check=datetime.utcnow().isoformat()
            )
    
    def _check_llm_health(self) -> ComponentHealth:
        """Check LLM component health.
        
        Returns:
            ComponentHealth for LLM
        """
        start = time.time()
        
        try:
            if not self.llm_client:
                response_time = (time.time() - start) * 1000
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    error_message="LLM client not initialized",
                    last_check=datetime.utcnow().isoformat()
                )
            
            # LLM is healthy if client is initialized
            response_time = (time.time() - start) * 1000
            
            return ComponentHealth(
                name="llm",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.utcnow().isoformat()
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            self.logger.error(f"LLM health check failed: {e}")
            
            return ComponentHealth(
                name="llm",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=str(e),
                last_check=datetime.utcnow().isoformat()
            )
    
    @staticmethod
    def _get_status_message(status: HealthStatus) -> str:
        """Get human-readable status message.
        
        Args:
            status: Health status
            
        Returns:
            Status message
        """
        messages = {
            HealthStatus.HEALTHY: "All systems operational",
            HealthStatus.DEGRADED: "Some systems degraded",
            HealthStatus.UNHEALTHY: "System unhealthy"
        }
        return messages.get(status, "Unknown status")
