"""Tests for monitoring and alerting system."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from vista.monitoring import (
    AlertManager, AlertConfig, Alert, AlertThreshold, AlertSeverity,
    LoggingNotificationHandler, EmailNotificationHandler, SlackNotificationHandler,
    get_alert_manager, setup_monitoring
)


@pytest.fixture
def alert_manager():
    """Create an alert manager for testing."""
    return AlertManager()


@pytest.fixture
def mock_notification_handler():
    """Create a mock notification handler."""
    return Mock()


class TestAlertManager:
    """Tests for AlertManager class."""
    
    def test_alert_manager_initialization(self, alert_manager):
        """Test alert manager initializes with default alerts."""
        assert len(alert_manager.alert_configs) == 4
        assert AlertThreshold.RESPONSE_TIME in alert_manager.alert_configs
        assert AlertThreshold.ERROR_RATE in alert_manager.alert_configs
        assert AlertThreshold.COMPONENT_HEALTH in alert_manager.alert_configs
        assert AlertThreshold.UPTIME in alert_manager.alert_configs
    
    def test_add_alert_config(self, alert_manager):
        """Test adding custom alert configuration."""
        config = AlertConfig(
            threshold_type=AlertThreshold.RESPONSE_TIME,
            threshold_value=500.0,
            severity=AlertSeverity.CRITICAL,
            description="Custom response time alert"
        )
        
        alert_manager.add_alert_config(config)
        
        assert alert_manager.alert_configs[AlertThreshold.RESPONSE_TIME].threshold_value == 500.0
        assert alert_manager.alert_configs[AlertThreshold.RESPONSE_TIME].severity == AlertSeverity.CRITICAL
    
    def test_register_notification_handler(self, alert_manager, mock_notification_handler):
        """Test registering notification handler."""
        alert_manager.register_notification_handler(mock_notification_handler)
        
        assert mock_notification_handler in alert_manager.notification_handlers
    
    def test_check_response_time_below_threshold(self, alert_manager):
        """Test response time check when below threshold."""
        alert = alert_manager.check_response_time(500.0)
        
        assert alert is None
    
    def test_check_response_time_above_threshold(self, alert_manager, mock_notification_handler):
        """Test response time check when above threshold."""
        alert_manager.register_notification_handler(mock_notification_handler)
        
        alert = alert_manager.check_response_time(1500.0)
        
        assert alert is not None
        assert alert.alert_type == AlertThreshold.RESPONSE_TIME
        assert alert.severity == AlertSeverity.WARNING
        assert alert.value == 1500.0
        mock_notification_handler.assert_called_once()
    
    def test_check_error_rate_below_threshold(self, alert_manager):
        """Test error rate check when below threshold."""
        alert = alert_manager.check_error_rate(0.02)
        
        assert alert is None
    
    def test_check_error_rate_above_threshold(self, alert_manager, mock_notification_handler):
        """Test error rate check when above threshold."""
        alert_manager.register_notification_handler(mock_notification_handler)
        
        alert = alert_manager.check_error_rate(0.10)
        
        assert alert is not None
        assert alert.alert_type == AlertThreshold.ERROR_RATE
        assert alert.severity == AlertSeverity.WARNING
        assert alert.value == 0.10
        mock_notification_handler.assert_called_once()
    
    def test_check_component_health_healthy(self, alert_manager):
        """Test component health check when healthy."""
        alert = alert_manager.check_component_health("database", "healthy")
        
        assert alert is None
    
    def test_check_component_health_degraded(self, alert_manager, mock_notification_handler):
        """Test component health check when degraded."""
        alert_manager.register_notification_handler(mock_notification_handler)
        
        alert = alert_manager.check_component_health("database", "degraded")
        
        assert alert is not None
        assert alert.alert_type == AlertThreshold.COMPONENT_HEALTH
        assert alert.severity == AlertSeverity.WARNING
        mock_notification_handler.assert_called_once()
    
    def test_check_component_health_unhealthy(self, alert_manager, mock_notification_handler):
        """Test component health check when unhealthy."""
        alert_manager.register_notification_handler(mock_notification_handler)
        
        alert = alert_manager.check_component_health("database", "unhealthy")
        
        assert alert is not None
        assert alert.alert_type == AlertThreshold.COMPONENT_HEALTH
        assert alert.severity == AlertSeverity.CRITICAL
        mock_notification_handler.assert_called_once()
    
    def test_check_uptime_above_threshold(self, alert_manager):
        """Test uptime check when above threshold."""
        alert = alert_manager.check_uptime(0.995)
        
        assert alert is None
    
    def test_check_uptime_below_threshold(self, alert_manager, mock_notification_handler):
        """Test uptime check when below threshold."""
        alert_manager.register_notification_handler(mock_notification_handler)
        
        alert = alert_manager.check_uptime(0.98)
        
        assert alert is not None
        assert alert.alert_type == AlertThreshold.UPTIME
        assert alert.severity == AlertSeverity.WARNING
        mock_notification_handler.assert_called_once()
    
    def test_alert_cooldown(self, alert_manager, mock_notification_handler):
        """Test alert cooldown prevents duplicate alerts."""
        alert_manager.register_notification_handler(mock_notification_handler)
        alert_manager.alert_cooldown_seconds = 1
        
        # First alert should be sent
        alert1 = alert_manager.check_response_time(1500.0)
        assert alert1 is not None
        assert mock_notification_handler.call_count == 1
        
        # Second alert within cooldown should not be sent
        alert2 = alert_manager.check_response_time(1500.0)
        assert alert2 is None
        assert mock_notification_handler.call_count == 1
    
    def test_get_alert_history(self, alert_manager, mock_notification_handler):
        """Test retrieving alert history."""
        alert_manager.register_notification_handler(mock_notification_handler)
        
        # Generate multiple alerts
        alert_manager.check_response_time(1500.0)
        alert_manager.alert_cooldown_seconds = 0  # Disable cooldown for testing
        alert_manager.check_error_rate(0.10)
        
        history = alert_manager.get_alert_history()
        
        assert len(history) >= 2
    
    def test_get_active_alerts(self, alert_manager, mock_notification_handler):
        """Test retrieving active alerts."""
        alert_manager.register_notification_handler(mock_notification_handler)
        
        # Generate alert
        alert_manager.check_response_time(1500.0)
        
        active = alert_manager.get_active_alerts()
        
        assert len(active) >= 1
        assert active[0].alert_type == AlertThreshold.RESPONSE_TIME
    
    def test_alert_history_limit(self, alert_manager, mock_notification_handler):
        """Test that alert history is limited to prevent memory bloat."""
        alert_manager.register_notification_handler(mock_notification_handler)
        alert_manager.alert_cooldown_seconds = 0
        
        # Generate more than 1000 alerts
        for i in range(1100):
            alert_manager.check_response_time(1500.0 + i)
        
        # Should only keep last 1000
        assert len(alert_manager.alert_history) == 1000
    
    def test_disabled_alert_config(self, alert_manager):
        """Test that disabled alerts are not triggered."""
        config = alert_manager.alert_configs[AlertThreshold.RESPONSE_TIME]
        config.enabled = False
        
        alert = alert_manager.check_response_time(1500.0)
        
        assert alert is None


class TestAlertConfig:
    """Tests for AlertConfig dataclass."""
    
    def test_alert_config_creation(self):
        """Test creating alert configuration."""
        config = AlertConfig(
            threshold_type=AlertThreshold.RESPONSE_TIME,
            threshold_value=1000.0,
            severity=AlertSeverity.WARNING,
            description="Test alert"
        )
        
        assert config.threshold_type == AlertThreshold.RESPONSE_TIME
        assert config.threshold_value == 1000.0
        assert config.severity == AlertSeverity.WARNING
        assert config.enabled is True


class TestAlert:
    """Tests for Alert dataclass."""
    
    def test_alert_creation(self):
        """Test creating alert instance."""
        alert = Alert(
            alert_type=AlertThreshold.RESPONSE_TIME,
            severity=AlertSeverity.WARNING,
            message="Response time exceeded",
            timestamp=datetime.utcnow(),
            value=1500.0,
            threshold=1000.0
        )
        
        assert alert.alert_type == AlertThreshold.RESPONSE_TIME
        assert alert.severity == AlertSeverity.WARNING
        assert alert.value == 1500.0
        assert alert.threshold == 1000.0


class TestLoggingNotificationHandler:
    """Tests for LoggingNotificationHandler."""
    
    def test_logging_handler_creation(self):
        """Test creating logging handler."""
        handler = LoggingNotificationHandler()
        
        assert handler is not None
    
    @patch('vista.monitoring.logging.getLogger')
    def test_logging_handler_logs_alert(self, mock_get_logger):
        """Test logging handler logs alerts."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        handler = LoggingNotificationHandler()
        alert = Alert(
            alert_type=AlertThreshold.RESPONSE_TIME,
            severity=AlertSeverity.WARNING,
            message="Test alert",
            timestamp=datetime.utcnow(),
            value=1500.0,
            threshold=1000.0
        )
        
        handler.handle(alert)
        
        # Verify logger was called
        assert mock_logger.log.called or mock_logger.warning.called


class TestEmailNotificationHandler:
    """Tests for EmailNotificationHandler."""
    
    def test_email_handler_disabled_without_config(self):
        """Test email handler is disabled without config."""
        handler = EmailNotificationHandler()
        
        assert handler.enabled is False
    
    def test_email_handler_enabled_with_config(self):
        """Test email handler is enabled with config."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pass",
            "from_email": "noreply@example.com",
            "to_emails": ["admin@example.com"]
        }
        handler = EmailNotificationHandler(config)
        
        assert handler.enabled is True
    
    def test_email_handler_handle_disabled(self):
        """Test email handler does nothing when disabled."""
        handler = EmailNotificationHandler()
        alert = Alert(
            alert_type=AlertThreshold.RESPONSE_TIME,
            severity=AlertSeverity.WARNING,
            message="Test alert",
            timestamp=datetime.utcnow(),
            value=1500.0,
            threshold=1000.0
        )
        
        # Should not raise exception
        handler.handle(alert)


class TestSlackNotificationHandler:
    """Tests for SlackNotificationHandler."""
    
    def test_slack_handler_disabled_without_url(self):
        """Test Slack handler is disabled without URL."""
        handler = SlackNotificationHandler()
        
        assert handler.enabled is False
    
    def test_slack_handler_enabled_with_url(self):
        """Test Slack handler is enabled with URL."""
        handler = SlackNotificationHandler("https://hooks.slack.com/services/xxx")
        
        assert handler.enabled is True
    
    def test_slack_handler_handle_disabled(self):
        """Test Slack handler does nothing when disabled."""
        handler = SlackNotificationHandler()
        alert = Alert(
            alert_type=AlertThreshold.RESPONSE_TIME,
            severity=AlertSeverity.WARNING,
            message="Test alert",
            timestamp=datetime.utcnow(),
            value=1500.0,
            threshold=1000.0
        )
        
        # Should not raise exception
        handler.handle(alert)


class TestMonitoringSetup:
    """Tests for monitoring setup function."""
    
    def test_setup_monitoring_with_logging(self):
        """Test setting up monitoring with logging."""
        manager = setup_monitoring(enable_logging=True)
        
        assert len(manager.notification_handlers) > 0
    
    def test_setup_monitoring_with_email(self):
        """Test setting up monitoring with email."""
        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pass",
            "from_email": "noreply@example.com",
            "to_emails": ["admin@example.com"]
        }
        manager = setup_monitoring(enable_email=True, email_config=email_config)
        
        assert len(manager.notification_handlers) > 0
    
    def test_setup_monitoring_with_slack(self):
        """Test setting up monitoring with Slack."""
        manager = setup_monitoring(
            enable_slack=True,
            slack_webhook_url="https://hooks.slack.com/services/xxx"
        )
        
        assert len(manager.notification_handlers) > 0
    
    def test_get_alert_manager_singleton(self):
        """Test that get_alert_manager returns singleton."""
        manager1 = get_alert_manager()
        manager2 = get_alert_manager()
        
        assert manager1 is manager2


class TestAlertThresholds:
    """Tests for alert threshold enums."""
    
    def test_alert_threshold_values(self):
        """Test alert threshold enum values."""
        assert AlertThreshold.RESPONSE_TIME == "response_time"
        assert AlertThreshold.ERROR_RATE == "error_rate"
        assert AlertThreshold.COMPONENT_HEALTH == "component_health"
        assert AlertThreshold.UPTIME == "uptime"
    
    def test_alert_severity_values(self):
        """Test alert severity enum values."""
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.CRITICAL == "critical"


class TestAlertManagerEdgeCases:
    """Tests for edge cases in alert manager."""
    
    def test_multiple_notification_handlers(self, alert_manager):
        """Test multiple notification handlers are called."""
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()
        
        alert_manager.register_notification_handler(handler1)
        alert_manager.register_notification_handler(handler2)
        alert_manager.register_notification_handler(handler3)
        
        alert_manager.check_response_time(1500.0)
        
        handler1.assert_called_once()
        handler2.assert_called_once()
        handler3.assert_called_once()
    
    def test_notification_handler_exception_handling(self, alert_manager):
        """Test that exception in handler doesn't break other handlers."""
        handler1 = Mock(side_effect=Exception("Handler error"))
        handler2 = Mock()
        
        alert_manager.register_notification_handler(handler1)
        alert_manager.register_notification_handler(handler2)
        
        # Should not raise exception
        alert_manager.check_response_time(1500.0)
        
        # Second handler should still be called
        handler2.assert_called_once()
    
    def test_zero_threshold_values(self, alert_manager):
        """Test handling of zero threshold values."""
        config = AlertConfig(
            threshold_type=AlertThreshold.ERROR_RATE,
            threshold_value=0.0,
            severity=AlertSeverity.CRITICAL
        )
        alert_manager.add_alert_config(config)
        
        # Any error rate > 0 should trigger alert
        alert = alert_manager.check_error_rate(0.001)
        
        assert alert is not None
    
    def test_very_high_threshold_values(self, alert_manager):
        """Test handling of very high threshold values."""
        config = AlertConfig(
            threshold_type=AlertThreshold.RESPONSE_TIME,
            threshold_value=999999.0,
            severity=AlertSeverity.WARNING
        )
        alert_manager.add_alert_config(config)
        
        # Normal response time should not trigger alert
        alert = alert_manager.check_response_time(1000.0)
        
        assert alert is None
