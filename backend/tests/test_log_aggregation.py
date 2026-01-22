"""Tests for log aggregation system."""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from vista.log_aggregation import (
    LogAggregator, LogSearchEngine, LogEntry, LogStats,
    get_log_aggregator, get_log_search_engine, setup_log_aggregation
)


@pytest.fixture
def log_aggregator():
    """Create a log aggregator for testing."""
    return LogAggregator()


@pytest.fixture
def log_search_engine(log_aggregator):
    """Create a log search engine for testing."""
    return LogSearchEngine(log_aggregator)


class TestLogAggregator:
    """Tests for LogAggregator class."""
    
    def test_aggregator_initialization(self, log_aggregator):
        """Test aggregator initializes correctly."""
        assert len(log_aggregator.logs) == 0
        assert log_aggregator.max_logs == 50000
        assert log_aggregator.retention_days == 7
    
    def test_add_log(self, log_aggregator):
        """Test adding a log entry."""
        entry = log_aggregator.add_log("INFO", "test_logger", "Test message")
        
        assert entry.level == "INFO"
        assert entry.logger_name == "test_logger"
        assert entry.message == "Test message"
        assert len(log_aggregator.logs) == 1
    
    def test_add_multiple_logs(self, log_aggregator):
        """Test adding multiple logs."""
        log_aggregator.add_log("INFO", "logger1", "Message 1")
        log_aggregator.add_log("WARNING", "logger2", "Message 2")
        log_aggregator.add_log("ERROR", "logger3", "Message 3")
        
        assert len(log_aggregator.logs) == 3
    
    def test_add_log_with_context(self, log_aggregator):
        """Test adding log with context."""
        context = {"user_id": "123", "action": "login"}
        entry = log_aggregator.add_log("INFO", "logger", "Message", context=context)
        
        assert entry.context == context
    
    def test_add_log_with_request_id(self, log_aggregator):
        """Test adding log with request ID."""
        entry = log_aggregator.add_log("INFO", "logger", "Message", request_id="req-123")
        
        assert entry.request_id == "req-123"
    
    def test_get_stats(self, log_aggregator):
        """Test getting log statistics."""
        log_aggregator.add_log("INFO", "logger1", "Message 1")
        log_aggregator.add_log("INFO", "logger1", "Message 2")
        log_aggregator.add_log("WARNING", "logger2", "Message 3")
        log_aggregator.add_log("ERROR", "logger3", "Message 4")
        
        stats = log_aggregator.get_stats()
        
        assert stats.total_logs == 4
        assert stats.logs_by_level["INFO"] == 2
        assert stats.logs_by_level["WARNING"] == 1
        assert stats.logs_by_level["ERROR"] == 1
        assert stats.error_count == 1
        assert stats.warning_count == 1
        assert stats.info_count == 2
    
    def test_search_logs(self, log_aggregator):
        """Test searching logs by message."""
        log_aggregator.add_log("INFO", "logger", "User login successful")
        log_aggregator.add_log("INFO", "logger", "User logout successful")
        log_aggregator.add_log("ERROR", "logger", "Database connection failed")
        
        results = log_aggregator.search_logs("User")
        
        assert len(results) == 2
        assert all("User" in r.message for r in results)
    
    def test_search_by_level(self, log_aggregator):
        """Test searching logs by level."""
        log_aggregator.add_log("INFO", "logger", "Message 1")
        log_aggregator.add_log("INFO", "logger", "Message 2")
        log_aggregator.add_log("ERROR", "logger", "Message 3")
        
        errors = log_aggregator.search_by_level("ERROR")
        
        assert len(errors) == 1
        assert errors[0].level == "ERROR"
    
    def test_search_by_logger(self, log_aggregator):
        """Test searching logs by logger name."""
        log_aggregator.add_log("INFO", "logger1", "Message 1")
        log_aggregator.add_log("INFO", "logger1", "Message 2")
        log_aggregator.add_log("INFO", "logger2", "Message 3")
        
        logger1_logs = log_aggregator.search_by_logger("logger1")
        
        assert len(logger1_logs) == 2
        assert all(l.logger_name == "logger1" for l in logger1_logs)
    
    def test_search_by_request_id(self, log_aggregator):
        """Test searching logs by request ID."""
        log_aggregator.add_log("INFO", "logger", "Message 1", request_id="req-123")
        log_aggregator.add_log("INFO", "logger", "Message 2", request_id="req-123")
        log_aggregator.add_log("INFO", "logger", "Message 3", request_id="req-456")
        
        req_logs = log_aggregator.search_by_request_id("req-123")
        
        assert len(req_logs) == 2
        assert all(l.request_id == "req-123" for l in req_logs)
    
    def test_get_recent_logs(self, log_aggregator):
        """Test getting recent logs."""
        for i in range(150):
            log_aggregator.add_log("INFO", "logger", f"Message {i}")
        
        recent = log_aggregator.get_recent_logs(limit=50)
        
        assert len(recent) == 50
    
    def test_get_errors(self, log_aggregator):
        """Test getting error logs."""
        log_aggregator.add_log("INFO", "logger", "Message 1")
        log_aggregator.add_log("ERROR", "logger", "Error 1")
        log_aggregator.add_log("CRITICAL", "logger", "Critical 1")
        log_aggregator.add_log("WARNING", "logger", "Warning 1")
        
        errors = log_aggregator.get_errors()
        
        assert len(errors) == 2
        assert all(l.level in ("ERROR", "CRITICAL") for l in errors)
    
    def test_get_warnings(self, log_aggregator):
        """Test getting warning logs."""
        log_aggregator.add_log("INFO", "logger", "Message 1")
        log_aggregator.add_log("WARNING", "logger", "Warning 1")
        log_aggregator.add_log("WARNING", "logger", "Warning 2")
        log_aggregator.add_log("ERROR", "logger", "Error 1")
        
        warnings = log_aggregator.get_warnings()
        
        assert len(warnings) == 2
        assert all(l.level == "WARNING" for l in warnings)
    
    def test_clear_old_logs(self, log_aggregator):
        """Test clearing old logs."""
        # Add old log
        old_entry = LogEntry(
            timestamp=datetime.utcnow() - timedelta(days=10),
            level="INFO",
            logger_name="logger",
            message="Old message"
        )
        log_aggregator.logs.append(old_entry)
        
        # Add recent log
        log_aggregator.add_log("INFO", "logger", "Recent message")
        
        assert len(log_aggregator.logs) == 2
        
        # Clear logs older than 7 days
        removed = log_aggregator.clear_old_logs(days=7)
        
        assert removed == 1
        assert len(log_aggregator.logs) == 1
    
    def test_export_logs_json(self, log_aggregator):
        """Test exporting logs to JSON."""
        log_aggregator.add_log("INFO", "logger", "Message 1")
        log_aggregator.add_log("ERROR", "logger", "Message 2")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "logs.json")
            count = log_aggregator.export_logs(filepath, format="json")
            
            assert count == 2
            assert os.path.exists(filepath)
            
            # Verify file content
            with open(filepath, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 2
    
    def test_export_logs_csv(self, log_aggregator):
        """Test exporting logs to CSV."""
        log_aggregator.add_log("INFO", "logger", "Message 1")
        log_aggregator.add_log("ERROR", "logger", "Message 2")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "logs.csv")
            count = log_aggregator.export_logs(filepath, format="csv")
            
            assert count == 2
            assert os.path.exists(filepath)
    
    def test_reset(self, log_aggregator):
        """Test resetting log aggregator."""
        log_aggregator.add_log("INFO", "logger", "Message 1")
        log_aggregator.add_log("INFO", "logger", "Message 2")
        
        assert len(log_aggregator.logs) == 2
        
        log_aggregator.reset()
        
        assert len(log_aggregator.logs) == 0
    
    def test_log_limit(self, log_aggregator):
        """Test that logs are limited to prevent memory bloat."""
        aggregator = LogAggregator(max_logs=100)
        
        # Add more than limit
        for i in range(150):
            aggregator.add_log("INFO", "logger", f"Message {i}")
        
        # Should only keep last 100
        assert len(aggregator.logs) == 100


class TestLogEntry:
    """Tests for LogEntry dataclass."""
    
    def test_log_entry_creation(self):
        """Test creating log entry."""
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level="INFO",
            logger_name="test_logger",
            message="Test message"
        )
        
        assert entry.level == "INFO"
        assert entry.logger_name == "test_logger"
        assert entry.message == "Test message"
    
    def test_log_entry_to_dict(self):
        """Test converting log entry to dictionary."""
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level="INFO",
            logger_name="test_logger",
            message="Test message",
            request_id="req-123"
        )
        
        data = entry.to_dict()
        
        assert data["level"] == "INFO"
        assert data["logger_name"] == "test_logger"
        assert data["message"] == "Test message"
        assert data["request_id"] == "req-123"
    
    def test_log_entry_to_json(self):
        """Test converting log entry to JSON."""
        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level="INFO",
            logger_name="test_logger",
            message="Test message"
        )
        
        json_str = entry.to_json()
        
        assert isinstance(json_str, str)
        assert "INFO" in json_str
        assert "test_logger" in json_str


class TestLogSearchEngine:
    """Tests for LogSearchEngine class."""
    
    def test_search_engine_initialization(self, log_search_engine):
        """Test search engine initializes correctly."""
        assert log_search_engine.aggregator is not None
    
    def test_search_with_query(self, log_aggregator, log_search_engine):
        """Test searching with query."""
        log_aggregator.add_log("INFO", "logger", "User login successful")
        log_aggregator.add_log("INFO", "logger", "User logout successful")
        log_aggregator.add_log("ERROR", "logger", "Database error")
        
        results = log_search_engine.search("User")
        
        assert len(results) == 2
    
    def test_search_with_level_filter(self, log_aggregator, log_search_engine):
        """Test searching with level filter."""
        log_aggregator.add_log("INFO", "logger", "Message 1")
        log_aggregator.add_log("ERROR", "logger", "Message 2")
        log_aggregator.add_log("ERROR", "logger", "Message 3")
        
        results = log_search_engine.search("Message", level="ERROR")
        
        assert len(results) == 2
        assert all(r.level == "ERROR" for r in results)
    
    def test_search_with_logger_filter(self, log_aggregator, log_search_engine):
        """Test searching with logger filter."""
        log_aggregator.add_log("INFO", "logger1", "Message 1")
        log_aggregator.add_log("INFO", "logger2", "Message 2")
        log_aggregator.add_log("INFO", "logger1", "Message 3")
        
        results = log_search_engine.search("Message", logger_name="logger1")
        
        assert len(results) == 2
        assert all(r.logger_name == "logger1" for r in results)
    
    def test_get_error_summary(self, log_aggregator, log_search_engine):
        """Test getting error summary."""
        log_aggregator.add_log("ERROR", "logger1", "Connection error")
        log_aggregator.add_log("ERROR", "logger2", "Connection error")
        log_aggregator.add_log("ERROR", "logger1", "Timeout error")
        
        summary = log_search_engine.get_error_summary()
        
        assert summary["total_errors"] == 3
        assert "error_types" in summary
        assert "error_loggers" in summary
    
    def test_get_request_logs(self, log_aggregator, log_search_engine):
        """Test getting logs for a request."""
        log_aggregator.add_log("INFO", "logger", "Message 1", request_id="req-123")
        log_aggregator.add_log("INFO", "logger", "Message 2", request_id="req-123")
        log_aggregator.add_log("ERROR", "logger", "Message 3", request_id="req-123")
        
        result = log_search_engine.get_request_logs("req-123")
        
        assert result["request_id"] == "req-123"
        assert result["total_logs"] == 3
        assert result["has_errors"] is True


class TestGlobalInstances:
    """Tests for global log aggregation instances."""
    
    def test_get_log_aggregator_singleton(self):
        """Test that get_log_aggregator returns singleton."""
        agg1 = get_log_aggregator()
        agg2 = get_log_aggregator()
        
        assert agg1 is agg2
    
    def test_get_log_search_engine_singleton(self):
        """Test that get_log_search_engine returns singleton."""
        engine1 = get_log_search_engine()
        engine2 = get_log_search_engine()
        
        assert engine1 is engine2
    
    def test_setup_log_aggregation(self):
        """Test setting up log aggregation."""
        aggregator = setup_log_aggregation(retention_days=14)
        
        assert aggregator is not None
        assert aggregator.retention_days == 14


class TestLogAggregationEdgeCases:
    """Tests for edge cases in log aggregation."""
    
    def test_search_with_no_matches(self, log_aggregator):
        """Test searching with no matches."""
        log_aggregator.add_log("INFO", "logger", "Message 1")
        
        results = log_aggregator.search_logs("nonexistent")
        
        assert len(results) == 0
    
    def test_empty_log_stats(self, log_aggregator):
        """Test stats with no logs."""
        stats = log_aggregator.get_stats()
        
        assert stats.total_logs == 0
        assert stats.error_count == 0
        assert stats.warning_count == 0
    
    def test_search_case_insensitive(self, log_aggregator):
        """Test that search is case insensitive."""
        log_aggregator.add_log("INFO", "logger", "User Login Successful")
        
        results = log_aggregator.search_logs("user login")
        
        assert len(results) == 1
    
    def test_log_with_special_characters(self, log_aggregator):
        """Test logging with special characters."""
        message = "Error: Connection failed! [timeout=30s]"
        entry = log_aggregator.add_log("ERROR", "logger", message)
        
        assert entry.message == message
        
        results = log_aggregator.search_logs("timeout")
        assert len(results) == 1
    
    def test_log_with_empty_context(self, log_aggregator):
        """Test logging with empty context."""
        entry = log_aggregator.add_log("INFO", "logger", "Message", context={})
        
        assert entry.context == {}
