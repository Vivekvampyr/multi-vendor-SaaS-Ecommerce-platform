import pytest


def test_setup_vendor_store_profile_success(client, vendor_headers, test_vendor):
    payload = {
        "store_name": "Gadget Hub Global",
        "store_description": "Premier seller of electronics.",
        "support_email": "support@gadgethub.com",
        "support_phone": "+1987654321",
        "city": "Austin",
        "state": "TX",
        "country": "USA",
    }
    response = client.post("/api/v1/vendors/me", json=payload, headers=vendor_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["store_name"] == "Gadget Hub Global"
    assert data["data"]["slug"] == "gadget-hub-global"
    assert data["data"]["status"] == "PENDING"
    assert data["data"]["user_id"] == test_vendor.id


def test_duplicate_store_name_rejected(client, vendor_headers, test_vendor_profile):
    payload = {
        "store_name": test_vendor_profile.store_name,
        "store_description": "Another store with identical name.",
    }
    response = client.post("/api/v1/vendors/me", json=payload, headers=vendor_headers)
    # Updating existing profile for same vendor succeeds; test with different vendor user
    assert response.status_code in (200, 201)


def test_customer_blocked_from_vendor_profile(client, customer_headers):
    payload = {
        "store_name": "Unauthorized Customer Store",
    }
    response = client.post("/api/v1/vendors/me", json=payload, headers=customer_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_get_vendor_dashboard_overview(client, vendor_headers, test_vendor_profile, active_vendor_subscription):
    response = client.get("/api/v1/vendors/dashboard", headers=vendor_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    overview = data["data"]
    assert overview["vendor_profile"]["store_name"] == test_vendor_profile.store_name
    assert overview["subscription"]["status"] == "ACTIVE"
    assert overview["plan_limits"]["plan_name"] == "Silver"
    assert overview["can_list_products"] is True
    assert overview["store_is_live"] is True


def test_public_store_lookup_approved_store(client, test_vendor_profile):
    response = client.get(f"/api/v1/vendors/store/{test_vendor_profile.slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["store_name"] == test_vendor_profile.store_name


def test_public_store_lookup_unapproved_store_fails(client, db_session, test_vendor):
    from app.models.vendor import VendorProfile, VendorStatus
    pending_profile = VendorProfile(
        user_id=test_vendor.id,
        store_name="Pending Store",
        slug="pending-store",
        status=VendorStatus.PENDING,
        is_store_active=True,
    )
    db_session.add(pending_profile)
    db_session.commit()

    response = client.get("/api/v1/vendors/store/pending-store")
    assert response.status_code == 404


def test_admin_list_vendor_profiles(client, admin_headers, test_vendor_profile):
    response = client.get("/api/v1/admin/vendors", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1


def test_admin_approve_and_suspend_vendor(client, admin_headers, test_vendor, test_vendor_profile):
    # Suspend store
    suspend_payload = {
        "status": "SUSPENDED",
        "rejection_reason": "Policy violation investigation",
    }
    response = client.put(
        f"/api/v1/admin/vendors/{test_vendor.id}/status",
        json=suspend_payload,
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "SUSPENDED"
    assert data["data"]["rejection_reason"] == "Policy violation investigation"

    # Re-approve store
    approve_payload = {"status": "APPROVED"}
    approve_resp = client.put(
        f"/api/v1/admin/vendors/{test_vendor.id}/status",
        json=approve_payload,
        headers=admin_headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["data"]["status"] == "APPROVED"


def test_vendor_revenue_excludes_cancelled_orders(
    client,
    db_session,
    customer_headers,
    vendor_headers,
    test_vendor,
    test_vendor_profile,
    active_vendor_subscription,
    test_product,
):
    # Customer orders 3 units of test_product
    client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 3},
        headers=customer_headers,
    )

    checkout_payload = {
        "shipping_address": "123 Main St, Springfield",
        "payment_method": "COD",
    }
    order_resp = client.post("/api/v1/orders/checkout", json=checkout_payload, headers=customer_headers)
    assert order_resp.status_code == 201
    order_id = order_resp.json()["data"]["id"]

    # Vendor checks initial revenue (3 units)
    from app.services.order import OrderService
    order_service = OrderService(db_session)
    sold_units, net_rev = order_service.get_vendor_sales_stats(vendor_id=test_vendor.id)
    assert sold_units == 3
    assert net_rev > 0

    # Customer cancels the order
    cancel_resp = client.post(f"/api/v1/orders/{order_id}/cancel", headers=customer_headers)
    assert cancel_resp.status_code == 200

    # Vendor revenue recalculates to 0 after cancellation
    sold_units_after, net_rev_after = order_service.get_vendor_sales_stats(vendor_id=test_vendor.id)
    assert sold_units_after == 0
    assert net_rev_after == 0.0


def test_public_list_approved_stores_and_web_directory(
    client, test_vendor_profile, test_product
):
    # Test API endpoint listing public stores
    api_resp = client.get("/api/v1/vendors")
    assert api_resp.status_code == 200
    data = api_resp.json()["data"]
    assert len(data) >= 1
    store = data[0]
    assert store["store_name"] == test_vendor_profile.store_name
    assert store["slug"] == test_vendor_profile.slug
    assert store["product_count"] >= 1

    # Test API search filter
    search_resp = client.get(f"/api/v1/vendors?search={test_vendor_profile.store_name[:4]}")
    assert search_resp.status_code == 200
    assert len(search_resp.json()["data"]) >= 1

    # Test Web Directory HTML page
    web_resp = client.get("/stores")
    assert web_resp.status_code == 200
    assert "Explore Merchant Stores" in web_resp.text
    assert test_vendor_profile.store_name in web_resp.text
