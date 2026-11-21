import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app import __version__


@pytest.mark.anyio
async def test_health_endpoint():
    """Verify the /api/v1/health endpoint returns 200 OK and expected structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == settings.APP_NAME
        assert data["version"] == __version__
        assert data["gemini_model_configured"] == "gemini-3.8-flash"
        assert "timestamp_utc" in data


@pytest.mark.anyio
async def test_root_endpoint():
    """Verify the root / endpoint responds with API metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["health_check"] == "/api/v1/health"
