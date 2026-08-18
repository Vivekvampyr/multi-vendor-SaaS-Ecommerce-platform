from app.core.config import Settings, settings
from app.models.base import BaseModel


def test_settings_loaded():
    """Verify settings properties and defaults."""
    assert settings.PROJECT_NAME == "Multi-Vendor SaaS E-Commerce"
    assert settings.API_V1_STR == "/api/v1"
    assert isinstance(settings.BACKEND_CORS_ORIGINS, list)
    assert settings.is_development is True


def test_404_error_response_format(client):
    """Verify 404 responses return standardized JSON schema."""
    response = client.get("/api/v1/non-existent-endpoint-xyz")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"


def test_base_model_instantiation():
    """Verify BaseModel class inherits correctly."""
    assert hasattr(BaseModel, "id")
    assert hasattr(BaseModel, "created_at")
    assert hasattr(BaseModel, "updated_at")
