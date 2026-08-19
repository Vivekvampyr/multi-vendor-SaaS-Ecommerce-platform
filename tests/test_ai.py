import json
from unittest.mock import AsyncMock, patch
import pytest

from app.schemas.ai import AIDescriptionGenerateRequest
from app.services.ai import AIService


def test_vendor_generate_ai_description_success(client, vendor_headers):
    payload = {
        "title": "Sony WH-1000XM5 Wireless Headphones",
        "category_name": "Audio & Electronics",
        "tone": "exciting",
        "keywords": "ANC, 30hr battery, LDAC, Multipoint Bluetooth",
    }
    response = client.post(
        "/api/v1/ai/generate-description", json=payload, headers=vendor_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "short_description" in data["data"]
    assert len(data["data"]["short_description"]) > 10
    assert "description" in data["data"]
    assert "seo_tags" in data["data"]
    assert len(data["data"]["seo_tags"]) >= 1
    assert "model_used" in data["data"]


def test_admin_generate_ai_description_success(client, admin_headers):
    payload = {
        "title": "Ergonomic Mechanical Keyboard",
        "category_name": "Computer Accessories",
        "tone": "technical",
        "keywords": "Hot-swappable switches, RGB backlight, PBT keycaps",
    }
    response = client.post(
        "/api/v1/ai/generate-description", json=payload, headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Ergonomic Mechanical Keyboard" in data["data"]["description"]


def test_customer_cannot_generate_ai_description(client, customer_headers):
    payload = {
        "title": "Gaming Mouse",
        "category_name": "Peripherals",
    }
    response = client.post(
        "/api/v1/ai/generate-description", json=payload, headers=customer_headers
    )
    assert response.status_code == 403


def test_unauthenticated_cannot_generate_ai_description(client):
    payload = {
        "title": "Smart Fitness Watch",
        "category_name": "Wearables",
    }
    response = client.post("/api/v1/ai/generate-description", json=payload)
    assert response.status_code == 401


def test_empty_title_validation_error(client, vendor_headers):
    payload = {
        "title": " ",
        "category_name": "Gadgets",
    }
    # min_length=2 on trimmed string
    response = client.post(
        "/api/v1/ai/generate-description",
        json={"title": "A", "category_name": "Gadgets"},
        headers=vendor_headers,
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_live_gemini_api_call_parsing():
    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "short_description": "Next-gen graphics powerhouse with cutting-edge Ray Tracing.",
                                    "description": "### Overview\nUnleash ultra-high FPS 4K gaming performance with dedicated AI tensor cores.",
                                    "seo_tags": ["rtx-5070", "gaming-gpu", "nvidia", "4k-gaming"],
                                }
                            )
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: mock_gemini_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        ai_service = AIService(api_key="AIzaFakeTestKeyForGemini12345", model="gemini-2.5-flash-lite")
        req = AIDescriptionGenerateRequest(
            title="Inno3D RTX 5070 Ti 16GB",
            category_name="Graphics Cards",
            tone="exciting",
            keywords="16GB GDDR7, Triple Fan, DLSS 4",
        )
        res = await ai_service._call_gemini_api(req)

        assert res.short_description == "Next-gen graphics powerhouse with cutting-edge Ray Tracing."
        assert "Unleash ultra-high FPS" in res.description
        assert "rtx-5070" in res.seo_tags
        assert res.model_used == "gemini-2.5-flash-lite"
