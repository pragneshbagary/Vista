"""Monitoring and alerting configuration for production."""

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Callable, List
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertThreshold(str, Enum):
    """Alert threshold types."""
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    COMPONENT_HEALTH = "component_health"
    UPTIME = "uptime"


@dataclass
class AlertConfig:
    """Configuration for an alert threshold."""
    threshold_type: AlertThreshold
    threshold_value: float
    severity: AlertSeverity
    enabled: bool = True
    description: str = ""


@dataclass
class Alert:
    """Alert instance."""
    alert_type: AlertThreshold
    severity: AlertSeverity
    message: str
    timestamp: datetime
    value: float
    threshold: float


class AlertManager:
    """Manages alert thresholds and notifications."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.logger = logging.getLogger(__name__)
        self.alert_configs: Dict[AlertThreshold, AlertConfig] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: List[Callable[[Alert], None]] = []
        self.last_alert_time: Dict[AlertThreshold, datetime] = {}
        self.alert_cooldown_seconds = 300  # 5 minutes between same alerts
        
        # Initialize default alert configurations
        self._initialize_default_alerts()
    
    def _initialize_default_alerts(self) -> None:
        """Initialize default alert thresholds."""
        # Response time alert: warn if p95 > 1000ms
        self.add_alert_config(AlertConfig(
            threshold_type=AlertThreshold.RESPONSE_TIME,
            threshold_value=1000.0,
            severity=AlertSeverity.WARNING,
            description="Alert if p95 response time exceeds 1000ms"
        ))
        
        # Error rate alert: warn if > 5%
        self.add_alert_config(AlertConfig(
            threshold_type=AlertThreshold.ERROR_RATE,
            threshold_value=0.05,
            severity=AlertSeverity.WARNING,
            description="Alert if error rate exceeds 5%"
        ))
        
        # Component health alert: critical if unhealthy
        self.add_alert_config(AlertConfig(
            threshold_type=AlertThreshold.COMPONENT_HEALTH,
            threshold_value=0.0,  # Not used for component health
            severity=AlertSeverity.CRITICAL,
            description="Alert if any component is unhealthy"
        ))
        
        # Uptime alert: warn if < 99%
        self.add_alert_config(AlertConfig(
            threshold_type=AlertThreshold.UPTIME,
            threshold_value=0.99,
            severity=AlertSeverity.WARNING,
            description="Alert if uptime drops below 99%"
        ))
    
    def add_alert_config(self, config: AlertConfig) -> None:
        """Add or update alert configuration.
        
        Args:
            config: Alert configuration
        """
        self.alert_configs[config.threshold_type] = config
        self.logger.info(f"Alert configured: {config.threshold_type} = {config.threshold_value}")
    
    def register_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        """Register a notification handler.
        
        Args:
            handler: Callable that receives Alert instances
        """
        self.notification_handlers.append(handler)
        handler_name = getattr(handler, '__name__', str(handler))
        self.logger.info(f"Notification handler registered: {handler_name}")
    
    def check_response_time(self, p95_response_time_ms: float) -> Optional[Alert]:
        """Check response time threshold.
        
        Args:
            p95_response_time_ms: 95th percentile response time in milliseconds
            
        Returns:
            Alert if threshold exceeded, None otherwise
        """
        config = self.alert_configs.get(AlertThreshold.RESPONSE_TIME)
        if not config or not config.enabled:
            return None
        
        if p95_response_time_ms > config.threshold_value:
            return self._create_and_send_alert(
                alert_type=AlertThreshold.RESPONSE_TIME,
                severity=config.severity,
                message=f"Response time p95 ({p95_response_time_ms:.1f}ms) exceeds threshold ({config.threshold_value:.1f}ms)",
                value=p95_response_time_ms,
                threshold=config.threshold_value
            )
        
        return None
    
    def check_error_rate(self, error_rate: float) -> Optional[Alert]:
        """Check error rate threshold.
        
        Args:
            error_rate: Error rate as decimal (0.0 - 1.0)
            
        Returns:
            Alert if threshold exceeded, None otherwise
        """
        config = self.alert_configs.get(AlertThreshold.ERROR_RATE)
        if not config or not config.enabled:
            return None
        
        if error_rate > config.threshold_value:
            return self._create_and_send_alert(
                alert_type=AlertThreshold.ERROR_RATE,
                severity=config.severity,
                message=f"Error rate ({error_rate*100:.2f}%) exceeds threshold ({config.threshold_value*100:.2f}%)",
                value=error_rate,
                threshold=config.threshold_value
            )
        
        return None
    
    def check_component_health(self, component_name: str, health_status: str) -> Optional[Alert]:
        """Check component health status.
        
        Args:
            component_name: Name of component
            health_status: Health status ("healthy", "degraded", "unhealthy")
            
        Returns:
            Alert if component is unhealthy, None otherwise
        """
        config = self.alert_configs.get(AlertThreshold.COMPONENT_HEALTH)
        if not config or not config.enabled:
            return None
        
        if health_status == "unhealthy":
            return self._create_and_send_alert(
                alert_type=AlertThreshold.COMPONENT_HEALTH,
                severity=config.severity,
                message=f"Component '{component_name}' is unhealthy",
                value=0.0,
                threshold=0.0
            )
        elif health_status == "degraded":
            return self._create_and_send_alert(
                alert_type=AlertThreshold.COMPONENT_HEALTH,
                severity=AlertSeverity.WARNING,
                message=f"Component '{component_name}' is degraded",
                value=0.0,
                threshold=0.0
            )
        
        return None
    
    def check_uptime(self, uptime_percentage: float) -> Optional[Alert]:
        """Check uptime threshold.
        
        Args:
            uptime_percentage: Uptime as decimal (0.0 - 1.0)
            
        Returns:
            Alert if uptime drops below threshold, None otherwise
        """
        config = self.alert_configs.get(AlertThreshold.UPTIME)
        if not config or not config.enabled:
            return None
        
        if uptime_percentage < config.threshold_value:
            return self._create_and_send_alert(
                alert_type=AlertThreshold.UPTIME,
                severity=config.severity,
                message=f"Uptime ({uptime_percentage*100:.2f}%) drops below threshold ({config.threshold_value*100:.2f}%)",
                value=uptime_percentage,
                threshold=config.threshold_value
            )
        
        return None
    
    def _create_and_send_alert(self, alert_type: AlertThreshold, severity: AlertSeverity,
                               message: str, value: float, threshold: float) -> Alert:
        """Create alert and send to notification handlers.
        
        Args:
            alert_type: Type of alert
            severity: Alert severity
            message: Alert message
            value: Current value
            threshold: Threshold value
            
        Returns:
            Alert instance
        """
        # Check cooldown to avoid alert spam
        last_alert = self.last_alert_time.get(alert_type)
        if last_alert and (datetime.utcnow() - last_alert).total_seconds() < self.alert_cooldown_seconds:
            self.logger.debug(f"Alert cooldown active for {alert_type}")
            return None
        
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            value=value,
            threshold=threshold
        )
        
        # Record alert
        self.alert_history.append(alert)
        self.last_alert_time[alert_type] = datetime.utcnow()
        
        # Keep only last 1000 alerts
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        # Send to notification handlers
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Error in notification handler: {e}")
        
        self.logger.warning(f"Alert: {message}")
        
        return alert
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get recent alert history.
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of recent alerts
        """
        return self.alert_history[-limit:]
    
    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts (within last hour).
        
        Args:
            Returns:
            List of active alerts
        """
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        return [a for a in self.alert_history if a.timestamp > one_hour_ago]


class NotificationHandler:
    """Base class for notification handlers."""
    
    def handle(self, alert: Alert) -> None:
        """Handle alert notification.
        
        Args:
            alert: Alert to handle
        """
        raise NotImplementedError


class LoggingNotificationHandler(NotificationHandler):
    """Notification handler that logs alerts."""
    
    def __init__(self):
        """Initialize logging handler."""
        self.logger = logging.getLogger(__name__)
    
    def handle(self, alert: Alert) -> None:
        """Log alert.
        
        Args:
            alert: Alert to log
        """
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }.get(alert.severity, logging.WARNING)
        
        self.logger.log(
            log_level,
            f"[{alert.severity.upper()}] {alert.alert_type}: {alert.message}"
        )


class EmailNotificationHandler(NotificationHandler):
    """Notification handler that sends email alerts."""
    
    def __init__(self, smtp_config: Optional[Dict] = None):
        """Initialize email handler.
        
        Args:
            smtp_config: SMTP configuration dict with keys: host, port, username, password, from_email, to_emails
        """
        self.logger = logging.getLogger(__name__)
        self.smtp_config = smtp_config or {}
        self.enabled = bool(self.smtp_config.get("host"))
    
    def handle(self, alert: Alert) -> None:
        """Send email alert.
        
        Args:
            alert: Alert to send
        """
        if not self.enabled:
            self.logger.debug("Email notifications disabled")
            return
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create email
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config.get("from_email", "noreply@vista.local")
            msg["To"] = ", ".join(self.smtp_config.get("to_emails", []))
            msg["Subject"] = f"[{alert.severity.upper()}] VISTA Alert: {alert.alert_type}"
            
            # Create body
            body = f"""
VISTA Alert Notification

Type: {alert.alert_type}
Severity: {alert.severity}
Time: {alert.timestamp.isoformat()}

Message:
{alert.message}

Current Value: {alert.value}
Threshold: {alert.threshold}

---
This is an automated alert from VISTA monitoring system.
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(self.smtp_config["host"], self.smtp_config.get("port", 587)) as server:
                if self.smtp_config.get("use_tls", True):
                    server.starttls()
                
                if self.smtp_config.get("username"):
                    server.login(self.smtp_config["username"], self.smtp_config["password"])
                
                server.send_message(msg)
            
            self.logger.info(f"Email alert sent for {alert.alert_type}")
        
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")


class SlackNotificationHandler(NotificationHandler):
    """Notification handler that sends Slack alerts."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """Initialize Slack handler.
        
        Args:
            webhook_url: Slack webhook URL
        """
        self.logger = logging.getLogger(__name__)
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
    
    def handle(self, alert: Alert) -> None:
        """Send Slack alert.
        
        Args:
            alert: Alert to send
        """
        if not self.enabled:
            self.logger.debug("Slack notifications disabled")
            return
        
        try:
            import requests
            import json
            
            # Determine color based on severity
            color_map = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ff9900",
                AlertSeverity.CRITICAL: "#ff0000",
            }
            color = color_map.get(alert.severity, "#999999")
            
            # Create Slack message
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"{alert.severity.upper()}: {alert.alert_type}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Current Value",
                                "value": str(alert.value),
                                "short": True
                            },
                            {
                                "title": "Threshold",
                                "value": str(alert.threshold),
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert.timestamp.isoformat(),
                                "short": False
                            }
                        ]
                    }
                ]
            }
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Slack alert sent for {alert.alert_type}")
            else:
                self.logger.error(f"Slack alert failed: {response.status_code}")
        
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create global alert manager.
    
    Returns:
        AlertManager instance
    """
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def setup_monitoring(
    enable_logging: bool = True,
    enable_email: bool = False,
    email_config: Optional[Dict] = None,
    enable_slack: bool = False,
    slack_webhook_url: Optional[str] = None
) -> AlertManager:
    """Set up monitoring with notification handlers.
    
    Args:
        enable_logging: Enable logging notifications
        enable_email: Enable email notifications
        email_config: Email configuration
        enable_slack: Enable Slack notifications
        slack_webhook_url: Slack webhook URL
        
    Returns:
        Configured AlertManager instance
    """
    manager = get_alert_manager()
    
    if enable_logging:
        handler = LoggingNotificationHandler()
        manager.register_notification_handler(handler.handle)
    
    if enable_email and email_config:
        handler = EmailNotificationHandler(email_config)
        manager.register_notification_handler(handler.handle)
    
    if enable_slack and slack_webhook_url:
        handler = SlackNotificationHandler(slack_webhook_url)
        manager.register_notification_handler(handler.handle)
    
    return manager
