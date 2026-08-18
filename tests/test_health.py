def test_health_endpoint_api_v1(client):
    """Test /api/v1/health returns 200 with standard schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["app_name"] == "Multi-Vendor SaaS E-Commerce"
    assert data["data"]["version"] == "0.1.0"
    assert "database" in data["data"]
    assert "connected" in data["data"]["database"]


def test_health_endpoint_root_alias(client):
    """Test /health root alias returns identical 200 health response."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] in ["healthy", "degraded"]


def test_root_html_view(client):
    """Test root view renders HTML template properly."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Multi-Vendor" in response.text
    assert "Phase 1 — Foundation Active" in response.text


def test_openapi_docs_available(client):
    """Test OpenAPI docs endpoint is accessible in debug mode."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()
