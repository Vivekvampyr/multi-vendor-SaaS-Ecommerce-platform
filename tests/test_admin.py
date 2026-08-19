import pytest


def test_admin_dashboard_metrics(client, admin_headers, test_customer, test_vendor, test_plan_silver, active_vendor_subscription):
    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    stats = data["data"]
    assert stats["total_users"] >= 3  # admin, customer, vendor
    assert stats["total_vendors"] >= 1
    assert stats["total_customers"] >= 1
    assert stats["total_plans"] >= 1
    assert stats["total_active_subscriptions"] >= 1
    assert stats["subscription_revenue"] >= float(test_plan_silver.price)
    assert "commission_revenue" in stats
    assert "total_revenue" in stats
    assert "total_gmv" in stats
    assert "total_vendor_payouts" in stats


def test_admin_dashboard_forbidden_for_non_admin(client, vendor_headers, customer_headers):
    assert client.get("/api/v1/admin/dashboard", headers=vendor_headers).status_code == 403
    assert client.get("/api/v1/admin/dashboard", headers=customer_headers).status_code == 403


def test_admin_list_subscriptions(client, admin_headers, active_vendor_subscription):
    response = client.get("/api/v1/admin/subscriptions", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1


def test_admin_manual_assign_vendor_plan(client, admin_headers, test_vendor, test_plan_gold):
    payload = {
        "plan_id": test_plan_gold.id,
        "status": "ACTIVE",
        "duration_days": 60,
    }
    response = client.post(
        f"/api/v1/admin/vendors/{test_vendor.id}/assign-plan",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["plan_id"] == test_plan_gold.id
    assert data["data"]["vendor_id"] == test_vendor.id


def test_admin_assign_plan_to_non_vendor_fails(client, admin_headers, test_customer, test_plan_silver):
    payload = {"plan_id": test_plan_silver.id}
    response = client.post(
        f"/api/v1/admin/vendors/{test_customer.id}/assign-plan",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "only available for VENDOR accounts" in response.json()["error"]["message"]
