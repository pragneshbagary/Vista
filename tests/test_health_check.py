"""Tests for health check system."""

import pytest
from unittest.mock import Mock, MagicMock
from vista.health_check import HealthChecker, HealthStatus, ComponentHealth, HealthCheckResponse


@pytest.fixture
def mock_query_engine():
    """Create a mock query engine."""
    return Mock()


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock()
    store.get_collection_count.return_value = 100
    return store


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return Mock()


@pytest.fixture
def health_checker(mock_query_engine, mock_vector_store, mock_llm_client):
    """Create a health checker with mocked components."""
    return HealthChecker(
        query_engine=mock_query_engine,
        vector_store=mock_vector_store,
        llm_client=mock_llm_client
    )


class TestHealthChecker:
    """Tests for HealthChecker class."""
    
    def test_check_health_all_healthy(self, health_checker):
        """Test health check when all components are healthy."""
        response = health_checker.check_health()
        
        assert response.status == HealthStatus.HEALTHY
        assert response.timestamp is not None
        assert "api" in response.components
        assert "database" in response.components
        assert "llm" in response.components
        assert response.message == "All systems operational"
    
    def test_check_health_degraded_database(self, health_checker):
        """Test health check when database is degraded."""
        health_checker.vector_store = None
        
        response = health_checker.check_health()
        
        assert response.status == HealthStatus.DEGRADED
        assert response.components["database"]["status"] == HealthStatus.DEGRADED
        assert response.message == "Some systems degraded"
    
    def test_check_health_unhealthy_database(self, health_checker):
        """Test health check when database is unhealthy."""
        health_checker.vector_store.get_collection_count.side_effect = Exception("DB Error")
        
        response = health_checker.check_health()
        
        assert response.status == HealthStatus.UNHEALTHY
        assert response.components["database"]["status"] == HealthStatus.UNHEALTHY
        assert response.components["database"]["error_message"] is not None
    
    def test_check_health_degraded_llm(self, health_checker):
        """Test health check when LLM is degraded."""
        health_checker.llm_client = None
        
        response = health_checker.check_health()
        
        assert response.status == HealthStatus.DEGRADED
        assert response.components["llm"]["status"] == HealthStatus.DEGRADED
    
    def test_check_health_response_times(self, health_checker):
        """Test that response times are recorded."""
        response = health_checker.check_health()
        
        for component in response.components.values():
            assert component["response_time_ms"] >= 0
            assert component["last_check"] is not None
    
    def test_check_health_uptime(self, health_checker):
        """Test that uptime is recorded."""
        response = health_checker.check_health()
        
        assert response.uptime_seconds >= 0
    
    def test_component_health_to_dict(self):
        """Test ComponentHealth to_dict conversion."""
        component = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            response_time_ms=10.5,
            error_message=None,
            last_check="2024-01-01T00:00:00"
        )
        
        data = component.to_dict()
        
        assert data["name"] == "test"
        assert data["status"] == HealthStatus.HEALTHY
        assert data["response_time_ms"] == 10.5
    
    def test_health_check_response_to_dict(self, health_checker):
        """Test HealthCheckResponse to_dict conversion."""
        response = health_checker.check_health()
        data = response.to_dict()
        
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert "uptime_seconds" in data


class TestHealthCheckerComponentChecks:
    """Tests for individual component health checks."""
    
    def test_api_health_check(self, health_checker):
        """Test API health check."""
        component = health_checker._check_api_health()
        
        assert component.name == "api"
        assert component.status == HealthStatus.HEALTHY
        assert component.response_time_ms >= 0
    
    def test_database_health_check_healthy(self, health_checker):
        """Test database health check when healthy."""
        component = health_checker._check_database_health()
        
        assert component.name == "database"
        assert component.status == HealthStatus.HEALTHY
        assert component.response_time_ms >= 0
    
    def test_database_health_check_degraded(self, health_checker):
        """Test database health check when degraded."""
        health_checker.vector_store = None
        
        component = health_checker._check_database_health()
        
        assert component.status == HealthStatus.DEGRADED
        assert "not initialized" in component.error_message
    
    def test_database_health_check_unhealthy(self, health_checker):
        """Test database health check when unhealthy."""
        health_checker.vector_store.get_collection_count.side_effect = Exception("Connection failed")
        
        component = health_checker._check_database_health()
        
        assert component.status == HealthStatus.UNHEALTHY
        assert component.error_message is not None
    
    def test_llm_health_check_healthy(self, health_checker):
        """Test LLM health check when healthy."""
        component = health_checker._check_llm_health()
        
        assert component.name == "llm"
        assert component.status == HealthStatus.HEALTHY
    
    def test_llm_health_check_degraded(self, health_checker):
        """Test LLM health check when degraded."""
        health_checker.llm_client = None
        
        component = health_checker._check_llm_health()
        
        assert component.status == HealthStatus.DEGRADED
        assert "not initialized" in component.error_message


class TestHealthCheckerEdgeCases:
    """Tests for edge cases in health checking."""
    
    def test_health_check_no_components(self):
        """Test health check with no components initialized."""
        checker = HealthChecker()
        
        response = checker.check_health()
        
        assert response.status == HealthStatus.DEGRADED
        assert response.components["database"]["status"] == HealthStatus.DEGRADED
        assert response.components["llm"]["status"] == HealthStatus.DEGRADED
    
    def test_health_check_multiple_calls(self, health_checker):
        """Test that multiple health checks work correctly."""
        response1 = health_checker.check_health()
        response2 = health_checker.check_health()
        
        assert response1.status == response2.status
        assert response1.components["api"]["status"] == response2.components["api"]["status"]
    
    def test_status_message_mapping(self):
        """Test status message mapping."""
        assert HealthChecker._get_status_message(HealthStatus.HEALTHY) == "All systems operational"
        assert HealthChecker._get_status_message(HealthStatus.DEGRADED) == "Some systems degraded"
        assert HealthChecker._get_status_message(HealthStatus.UNHEALTHY) == "System unhealthy"
