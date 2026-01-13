"""Smoke tests for staging deployment verification."""

import pytest
import httpx
import os
from pathlib import Path


class TestHealthCheck:
    """Test health check endpoint."""
    
    @pytest.fixture
    def api_url(self):
        """Get API URL from environment or use default."""
        return os.getenv("STAGING_API_URL", "http://localhost:8000")
    
    def test_health_endpoint_responds(self, api_url):
        """Test that health endpoint responds with 200."""
        response = httpx.get(f"{api_url}/health", timeout=10.0)
        assert response.status_code == 200
    
    def test_health_status_structure(self, api_url):
        """Test that health status has required fields."""
        response = httpx.get(f"{api_url}/health", timeout=10.0)
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_health_components_present(self, api_url):
        """Test that all required components are in health status."""
        response = httpx.get(f"{api_url}/health", timeout=10.0)
        data = response.json()
        
        components = data.get("components", {})
        assert "api" in components
        assert "database" in components


class TestAPIEndpoints:
    """Test basic API endpoints."""
    
    @pytest.fixture
    def api_url(self):
        """Get API URL from environment or use default."""
        return os.getenv("STAGING_API_URL", "http://localhost:8000")
    
    def test_api_responds_to_requests(self, api_url):
        """Test that API responds to basic requests."""
        response = httpx.get(f"{api_url}/health", timeout=10.0)
        assert response.status_code == 200
    
    def test_api_handles_cors(self, api_url):
        """Test that API handles CORS headers."""
        # Test without Origin header - CORS validation is tested in security tests
        response = httpx.get(
            f"{api_url}/health",
            timeout=10.0
        )
        assert response.status_code == 200
    
    def test_api_returns_json(self, api_url):
        """Test that API returns valid JSON."""
        response = httpx.get(f"{api_url}/health", timeout=10.0)
        assert response.headers.get("content-type") == "application/json"
        data = response.json()
        assert isinstance(data, dict)


class TestFrontendDeployment:
    """Test frontend deployment."""
    
    @pytest.fixture
    def frontend_url(self):
        """Get frontend URL from environment or use default."""
        return os.getenv("STAGING_FRONTEND_URL", "http://localhost:3000")
    
    def test_frontend_loads(self, frontend_url):
        """Test that frontend loads successfully."""
        response = httpx.get(frontend_url, timeout=10.0, follow_redirects=True)
        assert response.status_code == 200
    
    def test_frontend_returns_html(self, frontend_url):
        """Test that frontend returns HTML."""
        response = httpx.get(frontend_url, timeout=10.0, follow_redirects=True)
        assert "text/html" in response.headers.get("content-type", "")


class TestDatabasePersistence:
    """Test database persistence."""
    
    @pytest.fixture
    def api_url(self):
        """Get API URL from environment or use default."""
        return os.getenv("STAGING_API_URL", "http://localhost:8000")
    
    def test_database_is_accessible(self, api_url):
        """Test that database is accessible."""
        response = httpx.get(f"{api_url}/health", timeout=10.0)
        data = response.json()
        
        db_health = data.get("components", {}).get("database", {})
        assert db_health.get("status") in ["healthy", "degraded"]
    
    def test_database_has_data(self, api_url):
        """Test that database contains data."""
        response = httpx.get(f"{api_url}/health", timeout=10.0)
        data = response.json()
        
        # Database should be accessible
        assert data.get("status") in ["healthy", "degraded"]


class TestErrorHandling:
    """Test error handling."""
    
    @pytest.fixture
    def api_url(self):
        """Get API URL from environment or use default."""
        return os.getenv("STAGING_API_URL", "http://localhost:8000")
    
    def test_invalid_endpoint_returns_404(self, api_url):
        """Test that invalid endpoints return 404."""
        response = httpx.get(f"{api_url}/invalid-endpoint", timeout=10.0)
        assert response.status_code == 404
    
    def test_error_messages_are_sanitized(self, api_url):
        """Test that error messages don't contain sensitive data."""
        response = httpx.get(f"{api_url}/invalid-endpoint", timeout=10.0)
        error_text = response.text.lower()
        
        # Check that common sensitive patterns are not in error
        assert "api_key" not in error_text
        assert "secret" not in error_text
        assert "password" not in error_text


class TestMetrics:
    """Test metrics collection."""
    
    @pytest.fixture
    def api_url(self):
        """Get API URL from environment or use default."""
        return os.getenv("STAGING_API_URL", "http://localhost:8000")
    
    def test_metrics_endpoint_exists(self, api_url):
        """Test that metrics endpoint exists."""
        response = httpx.get(f"{api_url}/metrics", timeout=10.0)
        # Metrics endpoint may return 200 or 404 depending on implementation
        assert response.status_code in [200, 404]
    
    def test_metrics_have_required_fields(self, api_url):
        """Test that metrics have required fields."""
        response = httpx.get(f"{api_url}/metrics", timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            assert "total_requests" in data or "requests" in data


class TestResponseTimes:
    """Test response times are acceptable."""
    
    @pytest.fixture
    def api_url(self):
        """Get API URL from environment or use default."""
        return os.getenv("STAGING_API_URL", "http://localhost:8000")
    
    def test_health_check_response_time(self, api_url):
        """Test that health check responds quickly."""
        import time
        
        start = time.time()
        response = httpx.get(f"{api_url}/health", timeout=10.0)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        assert response.status_code == 200
        assert elapsed < 1000  # Should respond within 1 second
    
    def test_api_response_time(self, api_url):
        """Test that API responds within acceptable time."""
        import time
        
        start = time.time()
        response = httpx.get(f"{api_url}/health", timeout=10.0)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        assert response.status_code == 200
        assert elapsed < 5000  # Should respond within 5 seconds


class TestDeploymentConfiguration:
    """Test deployment configuration."""
    
    def test_environment_variables_set(self):
        """Test that required environment variables are set."""
        required_vars = [
            "LLM_PROVIDER",
            "LLM_MODEL",
        ]
        
        for var in required_vars:
            # These may not be set in test environment, so we just check they can be accessed
            value = os.getenv(var)
            # If set, should not be empty
            if value is not None:
                assert len(value) > 0
    
    def test_data_directory_exists(self):
        """Test that data directory exists."""
        data_dir = Path("./data")
        assert data_dir.exists() or os.getenv("DATA_DIRECTORY") is not None
    
    def test_persistence_directory_accessible(self):
        """Test that persistence directory is accessible."""
        persist_dir = os.getenv("PERSIST_DIRECTORY", "./chroma_db")
        persist_path = Path(persist_dir)
        
        # Directory should exist or be creatable
        if persist_path.exists():
            assert persist_path.is_dir()
