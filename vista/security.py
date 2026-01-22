"""Security utilities for production deployment."""

import logging
import re
from typing import List, Optional


class SecurityManager:
    """Manages security policies including CORS validation and error sanitization."""
    
    def __init__(self, allowed_origins: List[str]):
        """Initialize security manager with CORS whitelist.
        
        Args:
            allowed_origins: List of allowed origins for CORS
        """
        self.allowed_origins = allowed_origins
        self.logger = logging.getLogger(__name__)
    
    def validate_origin(self, origin: Optional[str]) -> bool:
        """Validate if an origin is in the CORS whitelist.
        
        Args:
            origin: The origin header value from the request
            
        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin:
            return False
        
        # Check if origin is in whitelist
        is_allowed = origin in self.allowed_origins
        
        if not is_allowed:
            self.log_security_event(
                "cors_rejection",
                {"origin": origin, "allowed_origins": self.allowed_origins}
            )
        
        return is_allowed
    
    def sanitize_error_message(self, error: Exception) -> str:
        """Remove sensitive data from error messages.
        
        Removes API keys, tokens, and other sensitive information from error messages.
        
        Args:
            error: The exception to sanitize
            
        Returns:
            Sanitized error message safe for client exposure
        """
        error_str = str(error)
        
        # Remove API keys (OpenAI format: sk-...)
        error_str = re.sub(r'sk-[A-Za-z0-9_-]{20,}', '[REDACTED_OPENAI_KEY]', error_str)
        
        # Remove Gemini API keys (AIza...)
        error_str = re.sub(r'AIza[A-Za-z0-9_-]{30,}', '[REDACTED_GEMINI_KEY]', error_str)
        
        # Remove generic tokens/secrets (common patterns)
        error_str = re.sub(r'(token|secret|password|api_key|apikey)[\s]*[:=][\s]*[^\s,}]+', 
                          r'\1=[REDACTED]', error_str, flags=re.IGNORECASE)
        
        # Remove bearer tokens
        error_str = re.sub(r'Bearer\s+[A-Za-z0-9._-]+', 'Bearer [REDACTED]', error_str)
        
        # Remove authorization headers
        error_str = re.sub(r'Authorization[\s]*[:=][\s]*[^\s,}]+', 
                          'Authorization: [REDACTED]', error_str, flags=re.IGNORECASE)
        
        # Remove URLs with credentials (user:pass@host)
        error_str = re.sub(r'([a-z]+://)[^:]+:[^@]+@', r'\1[REDACTED]@', error_str, flags=re.IGNORECASE)
        
        return error_str
    
    def sanitize_log_message(self, message: str) -> str:
        """Remove sensitive data from log messages.
        
        Args:
            message: The log message to sanitize
            
        Returns:
            Sanitized log message
        """
        return self.sanitize_error_message(Exception(message))
    
    def log_security_event(self, event_type: str, details: dict) -> None:
        """Log security-relevant events.
        
        Args:
            event_type: Type of security event (e.g., 'cors_rejection', 'auth_failure')
            details: Additional details about the event
        """
        self.logger.warning(
            f"SECURITY_EVENT: {event_type}",
            extra={"event_type": event_type, "details": details}
        )
