from datetime import datetime, timedelta, timezone
import pytest
from app.core.security import create_access_token, hash_password
from app.models.coupon import Coupon, DiscountType
from app.models.user import User, UserRole


def test_admin_create_platform_coupon(client, admin_headers):
    payload = {
        "code": "MEGAFALL25",
        "description": "25% off platform wide",
        "discount_type": "PERCENTAGE",
        "discount_value": 25.00,
        "max_discount_amount": 50.00,
        "min_order_amount": 75.00,
    }
    response = client.post("/api/v1/coupons", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["code"] == "MEGAFALL25"
    assert data["data"]["vendor_id"] is None
    assert data["data"]["discount_type"] == "PERCENTAGE"


def test_vendor_create_vendor_scoped_coupon(client, vendor_headers, test_vendor):
    payload = {
        "code": "STORE10",
        "description": "10% off Bob Tech Store items",
        "discount_type": "PERCENTAGE",
        "discount_value": 10.00,
        "min_order_amount": 30.00,
    }
    response = client.post("/api/v1/coupons", json=payload, headers=vendor_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["code"] == "STORE10"
    assert data["data"]["vendor_id"] == test_vendor.id


def test_customer_cannot_create_coupon(client, customer_headers):
    payload = {
        "code": "HACK50",
        "discount_type": "PERCENTAGE",
        "discount_value": 50.00,
    }
    response = client.post("/api/v1/coupons", json=payload, headers=customer_headers)
    assert response.status_code == 403


def test_duplicate_coupon_code_fails(client, admin_headers, test_platform_coupon):
    payload = {
        "code": test_platform_coupon.code,
        "discount_type": "PERCENTAGE",
        "discount_value": 10.00,
    }
    response = client.post("/api/v1/coupons", json=payload, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_percentage_over_100_fails(client, admin_headers):
    payload = {
        "code": "FREEALL",
        "discount_type": "PERCENTAGE",
        "discount_value": 150.00,
    }
    response = client.post("/api/v1/coupons", json=payload, headers=admin_headers)
    assert response.status_code == 400


def test_vendor_isolation_coupons(client, db_session, test_vendor_coupon):
    # Vendor B
    vendor_b = User(
        email="vendor_b2@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Vendor B2",
        role=UserRole.VENDOR,
        is_active=True,
    )
    db_session.add(vendor_b)
    db_session.commit()
    token_b = create_access_token(subject=vendor_b.id, role=vendor_b.role.value)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Vendor B cannot update Vendor A's coupon
    response = client.put(
        f"/api/v1/coupons/{test_vendor_coupon.id}",
        json={"discount_value": 30.00},
        headers=headers_b,
    )
    assert response.status_code == 403

    # Vendor B cannot delete Vendor A's coupon
    del_resp = client.delete(f"/api/v1/coupons/{test_vendor_coupon.id}", headers=headers_b)
    assert del_resp.status_code == 403


def test_validate_percentage_coupon_with_cap(client, test_platform_coupon):
    # Platform coupon: 15% off, max $30 cap, min $50 order
    # Subtotal $300 -> 15% = $45 -> capped to $30.00 -> final $270.00
    payload = {
        "code": test_platform_coupon.code,
        "subtotal": 300.00,
    }
    response = client.post("/api/v1/coupons/validate", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is True
    assert data["discount_amount"] == 30.00
    assert data["final_total"] == 270.00


def test_validate_fixed_discount_coupon(client, test_vendor_coupon):
    # Vendor coupon: $20 fixed off, min $100 order
    # Subtotal $120.00 -> discount $20.00 -> final $100.00
    payload = {
        "code": test_vendor_coupon.code,
        "subtotal": 120.00,
        "vendor_id": test_vendor_coupon.vendor_id,
    }
    response = client.post("/api/v1/coupons/validate", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is True
    assert data["discount_amount"] == 20.00
    assert data["final_total"] == 100.00


def test_validate_coupon_min_order_unmet(client, test_platform_coupon):
    # Min order $50, provided $35
    payload = {
        "code": test_platform_coupon.code,
        "subtotal": 35.00,
    }
    response = client.post("/api/v1/coupons/validate", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is False
    assert "Minimum order subtotal" in data["message"]


def test_validate_expired_coupon(client, db_session):
    past_date = datetime.now(timezone.utc) - timedelta(days=2)
    coupon = Coupon(
        code="EXPIRED50",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=50.00,
        end_date=past_date,
        is_active=True,
    )
    db_session.add(coupon)
    db_session.commit()

    payload = {"code": "EXPIRED50", "subtotal": 100.00}
    response = client.post("/api/v1/coupons/validate", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is False
    assert "expired" in data["message"]


def test_validate_per_user_limit_enforced(client, db_session, test_customer, customer_headers):
    # Create coupon with user_limit = 1
    coupon = Coupon(
        code="ONCEONLY",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=20.00,
        user_limit=1,
        is_active=True,
    )
    db_session.add(coupon)
    db_session.commit()

    # Log 1 usage for test_customer
    from app.models.coupon_usage import CouponUsage
    usage = CouponUsage(
        coupon_id=coupon.id,
        user_id=test_customer.id,
        discount_amount=20.00,
    )
    db_session.add(usage)
    db_session.commit()

    # Now customer tries to validate again
    payload = {"code": "ONCEONLY", "subtotal": 100.00}
    response = client.post("/api/v1/coupons/validate", json=payload, headers=customer_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["valid"] is False
    assert "already redeemed" in data["message"]
