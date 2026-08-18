import pytest


def test_vendor_select_plan_success(client, vendor_headers, test_plan_silver):
    payload = {"plan_id": test_plan_silver.id}
    response = client.post("/api/v1/subscriptions/select-plan", json=payload, headers=vendor_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["plan_id"] == test_plan_silver.id
    assert data["data"]["status"] == "ACTIVE"
    assert data["data"]["plan"]["name"] == "Silver"


def test_vendor_switch_plan(client, vendor_headers, test_plan_silver, test_plan_gold):
    # Select Silver first
    client.post("/api/v1/subscriptions/select-plan", json={"plan_id": test_plan_silver.id}, headers=vendor_headers)

    # Switch to Gold
    response = client.post("/api/v1/subscriptions/select-plan", json={"plan_id": test_plan_gold.id}, headers=vendor_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["plan_id"] == test_plan_gold.id
    assert data["data"]["plan"]["name"] == "Gold"
    assert data["data"]["plan"]["max_products"] == 20


def test_customer_blocked_from_vendor_subscriptions(client, customer_headers, test_plan_silver):
    response = client.post("/api/v1/subscriptions/select-plan", json={"plan_id": test_plan_silver.id}, headers=customer_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_get_my_plan_with_active_subscription(client, vendor_headers, active_vendor_subscription):
    response = client.get("/api/v1/subscriptions/my-plan", headers=vendor_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["plan_name"] == "Silver"
    assert data["data"]["max_products"] == 10
    assert data["data"]["commission_rate"] == 20.0
    assert data["data"]["is_active"] is True


def test_get_my_plan_without_subscription_fails(client, vendor_headers):
    # test_vendor starts without subscription in isolated test
    response = client.get("/api/v1/subscriptions/my-plan", headers=vendor_headers)
    assert response.status_code == 403
    assert "active SaaS subscription" in response.json()["error"]["message"]


def test_cancel_subscription_workflow(client, vendor_headers, active_vendor_subscription):
    response = client.post("/api/v1/subscriptions/cancel", headers=vendor_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "CANCELED"

    # Canceling again should return bad request
    repeat_cancel = client.post("/api/v1/subscriptions/cancel", headers=vendor_headers)
    assert repeat_cancel.status_code == 400
    assert repeat_cancel.json()["error"]["code"] == "BAD_REQUEST"
