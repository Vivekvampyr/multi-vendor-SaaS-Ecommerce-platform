import pytest
from app.core.security import create_access_token, hash_password
from app.models.coupon import Coupon, DiscountType
from app.models.order import OrderStatus, PaymentStatus
from app.models.product import Product, ProductStatus
from app.models.subscription import SubscriptionStatus, VendorSubscription
from app.models.user import User, UserRole
from app.models.vendor import VendorProfile, VendorStatus


def test_cart_operations_lifecycle(client, customer_headers, test_product):
    # 1. Add item to cart
    add_resp = client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 2},
        headers=customer_headers,
    )
    assert add_resp.status_code == 200
    cart_data = add_resp.json()["data"]
    assert cart_data["total_items"] == 2
    assert cart_data["subtotal"] == round(float(test_product.price) * 2, 2)
    assert len(cart_data["items"]) == 1
    item_id = cart_data["items"][0]["id"]

    # 2. Update item quantity
    upd_resp = client.put(
        f"/api/v1/cart/items/{item_id}",
        json={"quantity": 3},
        headers=customer_headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["data"]["total_items"] == 3

    # 3. View cart
    get_resp = client.get("/api/v1/cart", headers=customer_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["total_items"] == 3

    # 4. Remove item
    del_resp = client.delete(f"/api/v1/cart/items/{item_id}", headers=customer_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["total_items"] == 0


def test_guest_cart_with_session_token(client, test_product):
    session_headers = {"X-Session-Token": "guest-session-12345"}
    add_resp = client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 1},
        headers=session_headers,
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["data"]["total_items"] == 1


def test_guest_cart_with_cookie_session(client, test_product):
    client.cookies.set("guest_session_token", "cookie-session-999")
    add_resp = client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 2},
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["data"]["total_items"] == 2

    # View cart web page with cookie
    page_resp = client.get("/cart")
    assert page_resp.status_code == 200
    assert test_product.name in page_resp.text


def test_add_to_cart_exceeding_stock_fails(client, customer_headers, test_product):
    add_resp = client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": test_product.stock_quantity + 10},
        headers=customer_headers,
    )
    assert add_resp.status_code == 400
    assert "exceeds available stock" in add_resp.json()["error"]["message"]


def test_cumulative_add_to_cart_cannot_exceed_stock(client, db_session, test_product):
    # Set a product with limited stock of 3
    test_product.stock_quantity = 3
    db_session.commit()
    session_headers = {"X-Session-Token": "limited-stock-session"}

    # Add 2 items
    resp1 = client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 2},
        headers=session_headers,
    )
    assert resp1.status_code == 200

    # Add 1 item (now at max 3)
    resp2 = client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 1},
        headers=session_headers,
    )
    assert resp2.status_code == 200

    # Attempt to add 1 more (exceeds stock of 3)
    resp3 = client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 1},
        headers=session_headers,
    )
    assert resp3.status_code == 400
    assert "maximum available: 3" in resp3.json()["error"]["message"]


def test_checkout_multi_vendor_and_commission_splits(
    client,
    db_session,
    customer_headers,
    test_customer,
    test_vendor,
    test_vendor_profile,
    active_vendor_subscription,
    test_category,
    test_plan_gold,
):
    # Vendor 1 has Silver subscription (20% commission)
    prod1 = Product(
        vendor_id=test_vendor.id,
        category_id=test_category.id,
        name="Silver Vendor Product",
        slug="silver-vendor-product",
        sku="SILVER-PROD-001",
        price=100.00,
        stock_quantity=20,
        status=ProductStatus.PUBLISHED,
    )
    db_session.add(prod1)

    # Setup Vendor 2 with Gold plan (10% commission)
    vendor2 = User(
        email="vendor_gold@example.com",
        hashed_password=hash_password("GoldPass123!"),
        full_name="Gold Vendor",
        role=UserRole.VENDOR,
        is_active=True,
    )
    db_session.add(vendor2)
    db_session.commit()

    v2_profile = VendorProfile(
        user_id=vendor2.id,
        store_name="Gold Elite Store",
        slug="gold-elite-store",
        status=VendorStatus.APPROVED,
    )
    from datetime import datetime, timezone
    v2_sub = VendorSubscription(
        vendor_id=vendor2.id,
        plan_id=test_plan_gold.id,
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime.now(timezone.utc),
    )
    prod2 = Product(
        vendor_id=vendor2.id,
        category_id=test_category.id,
        name="Gold Vendor Product",
        slug="gold-vendor-product",
        sku="GOLD-PROD-001",
        price=200.00,
        stock_quantity=15,
        status=ProductStatus.PUBLISHED,
    )
    db_session.add_all([v2_profile, v2_sub, prod2])
    db_session.commit()

    # Customer adds both items to cart
    client.post("/api/v1/cart/items", json={"product_id": prod1.id, "quantity": 1}, headers=customer_headers)
    client.post("/api/v1/cart/items", json={"product_id": prod2.id, "quantity": 1}, headers=customer_headers)

    # Checkout
    checkout_payload = {
        "shipping_address": "742 Evergreen Terrace, Springfield, OR",
        "payment_method": "STRIPE",
    }
    response = client.post("/api/v1/orders/checkout", json=checkout_payload, headers=customer_headers)
    assert response.status_code == 201
    order_data = response.json()["data"]
    assert order_data["subtotal_amount"] == 300.00
    assert order_data["total_amount"] == 300.00
    assert order_data["status"] == "PENDING"
    assert len(order_data["items"]) == 2

    # Verify line item splits
    item1 = next(i for i in order_data["items"] if i["product_id"] == prod1.id)
    assert item1["commission_rate"] == 20.00
    assert item1["commission_amount"] == 20.00
    assert item1["vendor_earnings"] == 80.00

    item2 = next(i for i in order_data["items"] if i["product_id"] == prod2.id)
    assert item2["commission_rate"] == 10.00
    assert item2["commission_amount"] == 20.00
    assert item2["vendor_earnings"] == 180.00

    # Verify inventory was decremented
    db_session.refresh(prod1)
    db_session.refresh(prod2)
    assert prod1.stock_quantity == 19
    assert prod2.stock_quantity == 14

    # Verify cart is empty now
    cart_resp = client.get("/api/v1/cart", headers=customer_headers)
    assert cart_resp.json()["data"]["total_items"] == 0


def test_checkout_with_coupon_discount(
    client,
    customer_headers,
    test_product,
    test_platform_coupon,
):
    # test_product price = 199.99
    client.post("/api/v1/cart/items", json={"product_id": test_product.id, "quantity": 1}, headers=customer_headers)

    # Platform coupon: 15% off, max $30 cap
    # 199.99 * 15% = $30.00 cap -> total = 169.99
    checkout_payload = {
        "shipping_address": "100 Market St, San Francisco, CA",
        "coupon_code": test_platform_coupon.code,
    }
    response = client.post("/api/v1/orders/checkout", json=checkout_payload, headers=customer_headers)
    assert response.status_code == 201
    order = response.json()["data"]
    assert order["discount_amount"] == 30.00
    assert order["total_amount"] == 169.99


def test_payment_simulation_and_vendor_fulfillment(
    client,
    customer_headers,
    vendor_headers,
    test_product,
):
    # Customer adds product and checks out
    client.post("/api/v1/cart/items", json={"product_id": test_product.id, "quantity": 1}, headers=customer_headers)
    checkout_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "456 Main Street, Seattle, WA"},
        headers=customer_headers,
    )
    order_id = checkout_resp.json()["data"]["id"]

    # Process Payment
    pay_resp = client.post(
        f"/api/v1/orders/{order_id}/pay",
        json={"simulate_status": "SUCCESS", "payment_reference": "STRIPE-CHG-998877"},
        headers=customer_headers,
    )
    assert pay_resp.status_code == 200
    assert pay_resp.json()["data"]["status"] == "PAID"
    assert pay_resp.json()["data"]["payment_status"] == "SUCCESS"

    # Vendor checks their sold items
    vendor_orders_resp = client.get("/api/v1/orders/vendor/my-orders", headers=vendor_headers)
    assert vendor_orders_resp.status_code == 200
    items = vendor_orders_resp.json()["data"]
    assert len(items) >= 1
    item_id = items[0]["id"]

    # Vendor updates fulfillment status to SHIPPED
    status_resp = client.put(
        f"/api/v1/orders/items/{item_id}/status",
        json={"status": "SHIPPED"},
        headers=vendor_headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["status"] == "SHIPPED"


def test_vendor_cannot_fulfill_unpaid_online_order(
    client,
    customer_headers,
    vendor_headers,
    test_product,
):
    # Customer checks out with STRIPE online payment (unpaid)
    client.post("/api/v1/cart/items", json={"product_id": test_product.id, "quantity": 1}, headers=customer_headers)
    checkout_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "888 Online Way, Austin, TX", "payment_method": "STRIPE"},
        headers=customer_headers,
    )
    order_id = checkout_resp.json()["data"]["id"]

    # Vendor tries to ship without payment
    vendor_orders = client.get("/api/v1/orders/vendor/my-orders", headers=vendor_headers).json()["data"]
    item_id = next(i["id"] for i in vendor_orders if i["order_id"] == order_id)

    status_resp = client.put(
        f"/api/v1/orders/items/{item_id}/status",
        json={"status": "SHIPPED"},
        headers=vendor_headers,
    )
    assert status_resp.status_code == 400
    assert "Cannot ship or deliver an unpaid online order" in status_resp.json()["error"]["message"]


def test_vendor_can_fulfill_cod_order(
    client,
    customer_headers,
    vendor_headers,
    test_product,
):
    # Customer checks out with COD
    client.post("/api/v1/cart/items", json={"product_id": test_product.id, "quantity": 1}, headers=customer_headers)
    checkout_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "999 Cash Road, Miami, FL", "payment_method": "COD"},
        headers=customer_headers,
    )
    order_id = checkout_resp.json()["data"]["id"]

    vendor_orders = client.get("/api/v1/orders/vendor/my-orders", headers=vendor_headers).json()["data"]
    item_id = next(i["id"] for i in vendor_orders if i["order_id"] == order_id)

    # Vendor can ship COD order
    ship_resp = client.put(
        f"/api/v1/orders/items/{item_id}/status",
        json={"status": "SHIPPED"},
        headers=vendor_headers,
    )
    assert ship_resp.status_code == 200

    # Vendor delivers COD order -> confirms payment collection
    deliv_resp = client.put(
        f"/api/v1/orders/items/{item_id}/status",
        json={"status": "DELIVERED"},
        headers=vendor_headers,
    )
    assert deliv_resp.status_code == 200

    order_resp = client.get(f"/api/v1/orders/{order_id}", headers=customer_headers)
    assert order_resp.json()["data"]["payment_status"] == "SUCCESS"


def test_customer_cancel_order_restores_inventory(
    client,
    customer_headers,
    test_product,
    db_session,
):
    initial_stock = test_product.stock_quantity
    client.post("/api/v1/cart/items", json={"product_id": test_product.id, "quantity": 2}, headers=customer_headers)
    checkout_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "111 Cancel Ave, Denver, CO"},
        headers=customer_headers,
    )
    order_id = checkout_resp.json()["data"]["id"]

    db_session.refresh(test_product)
    assert test_product.stock_quantity == initial_stock - 2

    # Customer cancels order
    cancel_resp = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        json={"reason": "Ordered by mistake"},
        headers=customer_headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["data"]["status"] == "CANCELLED"

    # Inventory must be restored
    db_session.refresh(test_product)
    assert test_product.stock_quantity == initial_stock


def test_customer_cannot_cancel_delivered_order(
    client,
    customer_headers,
    vendor_headers,
    test_product,
):
    client.post("/api/v1/cart/items", json={"product_id": test_product.id, "quantity": 1}, headers=customer_headers)
    checkout_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "777 Delivered Blvd, Chicago, IL", "payment_method": "COD"},
        headers=customer_headers,
    )
    order_id = checkout_resp.json()["data"]["id"]

    # Vendor marks item as DELIVERED
    vendor_orders = client.get("/api/v1/orders/vendor/my-orders", headers=vendor_headers).json()["data"]
    item_id = next(i["id"] for i in vendor_orders if i["order_id"] == order_id)

    client.put(f"/api/v1/orders/items/{item_id}/status", json={"status": "DELIVERED"}, headers=vendor_headers)

    # Customer attempts to cancel delivered order -> must fail with 400
    cancel_resp = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        json={"reason": "Trying to cancel delivered item"},
        headers=customer_headers,
    )
    assert cancel_resp.status_code == 400
    assert "already DELIVERED" in cancel_resp.json()["error"]["message"] or "already" in cancel_resp.json()["error"]["message"]
