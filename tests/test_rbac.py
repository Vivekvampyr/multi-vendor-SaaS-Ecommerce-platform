import pytest


def test_admin_route_accessible_by_admin(client, admin_headers):
    response = client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_admin_route_blocked_for_vendor(client, vendor_headers):
    response = client.get("/api/v1/users", headers=vendor_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FORBIDDEN"


def test_admin_route_blocked_for_customer(client, customer_headers):
    response = client.get("/api/v1/users", headers=customer_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FORBIDDEN"


def test_ownership_customer_access_self(client, customer_headers, test_customer):
    response = client.get(f"/api/v1/users/{test_customer.id}", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == test_customer.id


def test_ownership_customer_blocked_access_other(client, customer_headers, test_vendor):
    response = client.get(f"/api/v1/users/{test_vendor.id}", headers=customer_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_ownership_admin_access_any_user(client, admin_headers, test_customer):
    response = client.get(f"/api/v1/users/{test_customer.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == test_customer.id
