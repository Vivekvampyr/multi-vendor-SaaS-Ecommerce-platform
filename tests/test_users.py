import pytest


def test_update_my_profile(client, customer_headers, test_customer):
    payload = {
        "full_name": "Alice Updated Name",
        "phone_number": "+1234567890",
    }
    response = client.put("/api/v1/users/me", json=payload, headers=customer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["full_name"] == "Alice Updated Name"
    assert data["data"]["phone_number"] == "+1234567890"


def test_change_my_password_success(client, customer_headers, test_customer):
    payload = {
        "current_password": "CustomerPass123!",
        "new_password": "NewStrongPass456!",
    }
    response = client.put("/api/v1/users/me/password", json=payload, headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify user can login with new password
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_customer.email, "password": "NewStrongPass456!"},
    )
    assert login_resp.status_code == 200


def test_change_my_password_wrong_current(client, customer_headers):
    payload = {
        "current_password": "IncorrectPassword999!",
        "new_password": "NewStrongPass456!",
    }
    response = client.put("/api/v1/users/me/password", json=payload, headers=customer_headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"
