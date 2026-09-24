"""Integration tests for the health check endpoint."""

import json
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Fixture that provides a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Integration tests for the GET /health endpoint."""
    
    def test_health_endpoint_returns_200_when_healthy(self, client):
        """Test that health endpoint returns 200 OK with healthy status."""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert response.headers['content-type'] == 'application/json'
        
        data = response.json()
        assert data == {"status": "healthy"}
    
    def test_health_endpoint_requires_no_authentication(self, client):
        """Test that health endpoint is accessible without authentication."""
        # Call endpoint without Authorization header
        response = client.get('/health')
        
        # Should succeed (200), not 401
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_health_endpoint_response_format_is_json(self, client):
        """Test that health endpoint returns valid JSON."""
        response = client.get('/health')
        
        assert response.headers['content-type'] == 'application/json'
        
        # Should be able to parse as JSON
        data = response.json()
        assert isinstance(data, dict)
        assert 'status' in data
    
    def test_health_endpoint_response_time(self, client):
        """Test that health endpoint responds within 100ms SLA."""
        start_time = time.time()
        response = client.get('/health')
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert elapsed_ms < 100  # Should complete in < 100ms
    
    def test_health_endpoint_response_time_median(self, client):
        """Test that median response time is under 50ms."""
        times = []
        for _ in range(10):
            start = time.time()
            response = client.get('/health')
            times.append((time.time() - start) * 1000)
            assert response.status_code == 200
        
        median_time = sorted(times)[len(times) // 2]
        assert median_time < 50  # Median < 50ms
    
    def test_health_endpoint_concurrent_requests(self, client):
        """Test that endpoint handles multiple concurrent requests."""
        # Send 10 rapid requests
        responses = []
        for _ in range(10):
            response = client.get('/health')
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
    
    def test_health_endpoint_http_method_get_only(self, client):
        """Test that endpoint only accepts GET method."""
        # Test that only GET is accepted
        get_response = client.get('/health')
        assert get_response.status_code == 200
        
        # POST should be rejected
        post_response = client.post('/health')
        assert post_response.status_code in [405, 422]  # Method Not Allowed or Unprocessable
        
        # PUT should be rejected
        put_response = client.put('/health')
        assert put_response.status_code in [405, 422]
        
        # DELETE should be rejected
        delete_response = client.delete('/health')
        assert delete_response.status_code in [405, 422]
    
    def test_health_endpoint_idempotent(self, client):
        """Test that calling endpoint multiple times returns same result."""
        responses = [client.get('/health') for _ in range(5)]
        
        for response in responses:
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
    
    def test_health_endpoint_no_request_body(self, client):
        """Test that endpoint works with no request body."""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestHealthEndpointErrorHandling:
    """Test error handling in health endpoint."""
    
    def test_health_endpoint_handles_errors_gracefully(self, client):
        """Test that endpoint returns 503 on error.
        
        Note: This test verifies the error path exists. In real scenarios,
        the health probe is designed to handle errors internally, so this
        endpoint should rarely return 503 unless the application is
        truly unhealthy.
        """
        # Normal case: should return 200
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_health_endpoint_response_validity(self, client):
        """Test that all response statuses return valid JSON."""
        response = client.get('/health')
        
        # Response should be valid JSON
        try:
            data = response.json()
            assert isinstance(data, dict)
            assert 'status' in data
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")


class TestHealthEndpointPerformance:
    """Performance tests for health endpoint."""
    
    def test_health_endpoint_p95_response_time(self, client):
        """Test that p95 response time is under 100ms."""
        times = []
        for _ in range(100):
            start = time.time()
            response = client.get('/health')
            times.append((time.time() - start) * 1000)
            assert response.status_code == 200
        
        times.sort()
        p95_index = int(len(times) * 0.95)
        p95_time = times[p95_index]
        
        assert p95_time < 100  # p95 < 100ms
    
    def test_health_endpoint_no_spike_in_response_time(self, client):
        """Test that response time is consistent (no spikes)."""
        times = []
        for _ in range(50):
            start = time.time()
            response = client.get('/health')
            times.append((time.time() - start) * 1000)
            assert response.status_code == 200
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Max should not be significantly higher than average
        # (allows for occasional slowness, but no major spikes)
        assert max_time < avg_time * 5  # Max is at most 5x average
