import pytest
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


def test_register_customer_success(client):
    payload = {
        "email": "newcustomer@example.com",
        "password": "StrongPassword123!",
        "full_name": "Jane Customer",
        "role": "CUSTOMER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "newcustomer@example.com"
    assert data["data"]["role"] == "CUSTOMER"
    assert "password" not in data["data"]


def test_register_vendor_success(client):
    payload = {
        "email": "newvendor@example.com",
        "password": "StrongPassword123!",
        "full_name": "Acme Vendor Store",
        "role": "VENDOR",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["role"] == "VENDOR"


def test_register_duplicate_email_fails(client, test_customer):
    payload = {
        "email": test_customer.email,
        "password": "AnotherPassword123!",
        "full_name": "Duplicate User",
        "role": "CUSTOMER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "CONFLICT"


def test_register_admin_role_forbidden(client):
    payload = {
        "email": "hacker@example.com",
        "password": "StrongPassword123!",
        "full_name": "Fake Admin",
        "role": "ADMIN",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FORBIDDEN"


def test_register_invalid_password_length(client):
    payload = {
        "email": "short@example.com",
        "password": "123",
        "full_name": "Short Pass",
        "role": "CUSTOMER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_login_success(client, test_customer):
    payload = {
        "email": "customer@example.com",
        "password": "CustomerPass123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"
    assert data["data"]["user"]["email"] == test_customer.email


def test_login_invalid_password(client, test_customer):
    payload = {
        "email": test_customer.email,
        "password": "WrongPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_login_non_existent_user(client):
    payload = {
        "email": "nobody@example.com",
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


def test_login_deactivated_user(client, db_session):
    deactivated_user = User(
        email="banned@example.com",
        hashed_password=hash_password("BannedPass123!"),
        full_name="Banned User",
        role=UserRole.CUSTOMER,
        is_active=False,
    )
    db_session.add(deactivated_user)
    db_session.commit()

    payload = {
        "email": "banned@example.com",
        "password": "BannedPass123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 403


def test_login_oauth2_form(client, test_vendor):
    response = client.post(
        "/api/v1/auth/login/oauth2",
        data={"username": "vendor@example.com", "password": "VendorPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_token_lifecycle(client, test_customer):
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPass123!"},
    )
    refresh_token = login_resp.json()["data"]["refresh_token"]

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert data["success"] is True
    assert "access_token" in data["data"]


def test_refresh_with_access_token_fails(client, customer_token):
    # Trying to use an access token on the refresh endpoint should be rejected
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": customer_token},
    )
    assert response.status_code == 401


def test_get_me_authenticated(client, customer_headers, test_customer):
    response = client.get("/api/v1/auth/me", headers=customer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == test_customer.email


def test_get_me_unauthorized_missing_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
