import pytest


def test_list_plans_public(client, test_plan_silver, test_plan_gold):
    response = client.get("/api/v1/plans")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 2
    assert data["data"][0]["name"] == "Silver"
    assert data["data"][0]["max_products"] == 10
    assert data["data"][0]["commission_rate"] == 20.0


def test_get_single_plan(client, test_plan_silver):
    response = client.get(f"/api/v1/plans/{test_plan_silver.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == test_plan_silver.id
    assert data["data"]["slug"] == "silver"


def test_create_plan_admin_success(client, admin_headers):
    payload = {
        "name": "Platinum Enterprise",
        "description": "Unlimited enterprise scale",
        "price": 99.99,
        "currency": "USD",
        "billing_cycle": "MONTHLY",
        "max_products": 100,
        "commission_rate": 5.0,
        "is_active": True,
    }
    response = client.post("/api/v1/plans", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Platinum Enterprise"
    assert data["data"]["slug"] == "platinum-enterprise"
    assert data["data"]["commission_rate"] == 5.0
    assert data["data"]["max_products"] == 100


def test_create_plan_forbidden_for_vendor_or_customer(client, vendor_headers, customer_headers):
    payload = {
        "name": "Unauthorized Plan",
        "price": 10.0,
        "max_products": 5,
        "commission_rate": 15.0,
    }
    resp_vendor = client.post("/api/v1/plans", json=payload, headers=vendor_headers)
    assert resp_vendor.status_code == 403

    resp_cust = client.post("/api/v1/plans", json=payload, headers=customer_headers)
    assert resp_cust.status_code == 403


def test_create_plan_duplicate_name_fails(client, admin_headers, test_plan_silver):
    payload = {
        "name": "Silver",
        "price": 25.0,
        "max_products": 15,
        "commission_rate": 18.0,
    }
    response = client.post("/api/v1/plans", json=payload, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_create_plan_invalid_commission_rate(client, admin_headers):
    payload = {
        "name": "Invalid Comm",
        "price": 20.0,
        "max_products": 10,
        "commission_rate": 120.0,  # Invalid: > 100%
    }
    response = client.post("/api/v1/plans", json=payload, headers=admin_headers)
    assert response.status_code == 422


def test_update_plan_admin(client, admin_headers, test_plan_silver):
    payload = {
        "max_products": 15,
        "commission_rate": 18.5,
    }
    response = client.put(f"/api/v1/plans/{test_plan_silver.id}", json=payload, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["max_products"] == 15
    assert data["data"]["commission_rate"] == 18.5


def test_delete_plan_without_subscribers(client, admin_headers, test_plan_gold):
    response = client.delete(f"/api/v1/plans/{test_plan_gold.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify deleted
    get_resp = client.get(f"/api/v1/plans/{test_plan_gold.id}")
    assert get_resp.status_code == 404


def test_delete_plan_with_active_subscribers_fails(client, admin_headers, active_vendor_subscription, test_plan_silver):
    # Silver has active test_vendor subscription
    response = client.delete(f"/api/v1/plans/{test_plan_silver.id}", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
