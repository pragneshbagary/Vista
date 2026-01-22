"""Production ASGI server configuration for VISTA."""

import os
import logging
from typing import Optional
from dataclasses import dataclass


@dataclass
class ASGIConfig:
    """Configuration for production ASGI server (Gunicorn + Uvicorn)."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    worker_class: str = "uvicorn.workers.UvicornWorker"
    
    # Timeout settings (in seconds)
    timeout: int = 120
    graceful_timeout: int = 30
    keepalive: int = 5
    
    # Worker settings
    worker_connections: int = 1000
    max_requests: int = 1000
    max_requests_jitter: int = 50
    
    # Logging
    access_log: str = "-"  # stdout
    error_log: str = "-"   # stderr
    log_level: str = "info"
    
    # Performance
    backlog: int = 2048
    
    @classmethod
    def from_env(cls) -> "ASGIConfig":
        """Load ASGI configuration from environment variables.
        
        Returns:
            ASGIConfig instance with values from environment
            
        Raises:
            ValueError: If configuration is invalid
        """
        try:
            workers = int(os.getenv("WORKERS", "4"))
            port = int(os.getenv("PORT", "8000"))
            timeout = int(os.getenv("TIMEOUT", "120"))
            graceful_timeout = int(os.getenv("GRACEFUL_TIMEOUT", "30"))
            keepalive = int(os.getenv("KEEPALIVE", "5"))
            worker_connections = int(os.getenv("WORKER_CONNECTIONS", "1000"))
            max_requests = int(os.getenv("MAX_REQUESTS", "1000"))
            max_requests_jitter = int(os.getenv("MAX_REQUESTS_JITTER", "50"))
            backlog = int(os.getenv("BACKLOG", "2048"))
        except ValueError as e:
            raise ValueError(f"Invalid ASGI configuration: {e}")
        
        config = cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=port,
            workers=workers,
            timeout=timeout,
            graceful_timeout=graceful_timeout,
            keepalive=keepalive,
            worker_connections=worker_connections,
            max_requests=max_requests,
            max_requests_jitter=max_requests_jitter,
            log_level=os.getenv("LOG_LEVEL", "info"),
            backlog=backlog
        )
        
        config.validate()
        return config
    
    def validate(self) -> None:
        """Validate ASGI configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        errors = []
        
        if self.workers < 1:
            errors.append(f"WORKERS must be at least 1, got {self.workers}")
        
        if self.timeout < 1:
            errors.append(f"TIMEOUT must be at least 1 second, got {self.timeout}")
        
        if self.graceful_timeout < 1:
            errors.append(f"GRACEFUL_TIMEOUT must be at least 1 second, got {self.graceful_timeout}")
        
        if self.graceful_timeout > self.timeout:
            errors.append(f"GRACEFUL_TIMEOUT ({self.graceful_timeout}) must be less than TIMEOUT ({self.timeout})")
        
        if self.keepalive < 0:
            errors.append(f"KEEPALIVE must be non-negative, got {self.keepalive}")
        
        if self.worker_connections < 1:
            errors.append(f"WORKER_CONNECTIONS must be at least 1, got {self.worker_connections}")
        
        if self.max_requests < 0:
            errors.append(f"MAX_REQUESTS must be non-negative, got {self.max_requests}")
        
        if self.backlog < 1:
            errors.append(f"BACKLOG must be at least 1, got {self.backlog}")
        
        if not (1 <= self.port <= 65535):
            errors.append(f"PORT must be between 1 and 65535, got {self.port}")
        
        if errors:
            error_message = "ASGI configuration validation failed:\n"
            for error in errors:
                error_message += f"  - {error}\n"
            raise ValueError(error_message)
    
    def to_gunicorn_config(self) -> dict:
        """Convert to Gunicorn configuration dictionary.
        
        Returns:
            Dictionary with Gunicorn configuration
        """
        return {
            "bind": f"{self.host}:{self.port}",
            "workers": self.workers,
            "worker_class": self.worker_class,
            "timeout": self.timeout,
            "graceful_timeout": self.graceful_timeout,
            "keepalive": self.keepalive,
            "max_requests": self.max_requests,
            "max_requests_jitter": self.max_requests_jitter,
            "backlog": self.backlog,
            "accesslog": self.access_log,
            "errorlog": self.error_log,
            "loglevel": self.log_level,
        }
    
    def to_uvicorn_config(self) -> dict:
        """Convert to Uvicorn configuration dictionary.
        
        Returns:
            Dictionary with Uvicorn configuration
        """
        return {
            "host": self.host,
            "port": self.port,
            "log_level": self.log_level,
            "timeout_keep_alive": self.keepalive,
        }
    
    def get_recommended_workers(self) -> int:
        """Get recommended number of workers based on CPU count.
        
        Returns:
            Recommended number of workers
        """
        try:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            # Recommended: (2 * cpu_count) + 1
            return (2 * cpu_count) + 1
        except Exception:
            # Fallback to 4 if unable to determine CPU count
            return 4
