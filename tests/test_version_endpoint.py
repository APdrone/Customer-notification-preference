"""Tests for the application version endpoint."""

from fastapi.testclient import TestClient

from app import config as app_config
from app.main import app


class TestVersionEndpoint:
    """Test the public version endpoint."""

    def test_version_endpoint_returns_configured_version(self, monkeypatch):
        """The endpoint should return the configured app version."""
        monkeypatch.setattr(app_config, 'APP_VERSION', '1.2.3', raising=False)
        client = TestClient(app)

        response = client.get('/version')

        assert response.status_code == 200
        assert response.json() == {'version': '1.2.3'}

    def test_version_endpoint_returns_503_when_config_missing(self, monkeypatch):
        """The endpoint should fail safely when no version is configured."""
        monkeypatch.setattr(app_config, 'APP_VERSION', '', raising=False)
        client = TestClient(app)

        response = client.get('/version')

        assert response.status_code == 503
        assert response.json()['detail'] == 'Version configuration unavailable'