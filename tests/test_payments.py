import json
import pytest
from app.models.order import OrderStatus, PaymentStatus
from app.models.subscription import SubscriptionStatus, VendorSubscription


def test_get_stripe_config(client):
    response = client.get("/api/v1/payments/config")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "publishable_key" in data["data"]
    assert "currency" in data["data"]
    assert "is_configured" in data["data"]


def test_create_order_checkout_session_customer(client, customer_headers, test_customer, test_product, test_vendor, active_vendor_subscription):
    # 1. Add product to cart
    client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 1},
        headers=customer_headers,
    )
    # 2. Checkout
    co_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "123 Main St, New York, NY 10001", "payment_method": "STRIPE"},
        headers=customer_headers,
    )
    assert co_resp.status_code == 201
    order_id = co_resp.json()["data"]["id"]

    # 3. Create Stripe Checkout Session
    session_resp = client.post(
        "/api/v1/payments/checkout-session/order",
        json={"order_id": order_id},
        headers=customer_headers,
    )
    assert session_resp.status_code == 200
    session_data = session_resp.json()
    assert session_data["success"] is True
    assert session_data["data"]["session_id"] is not None
    assert session_data["data"]["mode"] == "payment"


def test_create_order_checkout_session_forbidden_for_other_user(client, vendor_headers, customer_headers, test_product, active_vendor_subscription):
    client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 1},
        headers=customer_headers,
    )
    co_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "456 Oak St, Los Angeles, CA 90001", "payment_method": "STRIPE"},
        headers=customer_headers,
    )
    order_id = co_resp.json()["data"]["id"]

    # Vendor role is rejected by require_customer dependency
    response = client.post(
        "/api/v1/payments/checkout-session/order",
        json={"order_id": order_id},
        headers=vendor_headers,
    )
    assert response.status_code == 403


def test_create_subscription_checkout_session_vendor(client, vendor_headers, test_vendor, test_plan_gold):
    response = client.post(
        "/api/v1/payments/checkout-session/subscription",
        json={"plan_id": test_plan_gold.id},
        headers=vendor_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["session_id"] is not None
    assert data["data"]["mode"] == "subscription"


def test_create_subscription_checkout_session_customer_fails(client, customer_headers, test_plan_gold):
    response = client.post(
        "/api/v1/payments/checkout-session/subscription",
        json={"plan_id": test_plan_gold.id},
        headers=customer_headers,
    )
    assert response.status_code == 403


def test_create_order_payment_intent(client, customer_headers, test_customer, test_product, active_vendor_subscription):
    client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 1},
        headers=customer_headers,
    )
    co_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "789 Pine St, Chicago, IL 60601", "payment_method": "STRIPE"},
        headers=customer_headers,
    )
    order_id = co_resp.json()["data"]["id"]

    response = client.post(
        f"/api/v1/payments/payment-intent/order/{order_id}",
        headers=customer_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "client_secret" in data["data"]
    assert "payment_intent_id" in data["data"]


def test_stripe_webhook_order_completed(client, customer_headers, test_customer, test_product, active_vendor_subscription, db_session):
    client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 1},
        headers=customer_headers,
    )
    co_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "100 Broadway, NY, NY 10005", "payment_method": "STRIPE"},
        headers=customer_headers,
    )
    order_id = co_resp.json()["data"]["id"]

    webhook_event = {
        "id": "evt_test_order_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_order_sess_999",
                "mode": "payment",
                "payment_intent": "pi_test_order_intent_888",
                "metadata": {
                    "order_id": str(order_id),
                    "type": "order_payment",
                }
            }
        }
    }

    response = client.post(
        "/api/v1/payments/webhook",
        content=json.dumps(webhook_event),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["received"] is True

    # Verify Order is marked PAID in database
    get_resp = client.get(f"/api/v1/orders/{order_id}", headers=customer_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["status"] == OrderStatus.PAID.value
    assert get_resp.json()["data"]["payment_status"] == PaymentStatus.SUCCESS.value
    assert get_resp.json()["data"]["payment_reference"] == "pi_test_order_intent_888"


def test_stripe_webhook_subscription_completed(client, vendor_headers, test_vendor, test_plan_gold, db_session):
    webhook_event = {
        "id": "evt_test_sub_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_sub_sess_777",
                "mode": "subscription",
                "subscription": "sub_stripe_test_gold_123",
                "customer": "cus_stripe_test_vendor_456",
                "metadata": {
                    "vendor_id": str(test_vendor.id),
                    "plan_id": str(test_plan_gold.id),
                    "type": "saas_subscription",
                }
            }
        }
    }

    response = client.post(
        "/api/v1/payments/webhook",
        content=json.dumps(webhook_event),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["received"] is True

    # Verify Vendor active plan is now Gold
    plan_resp = client.get("/api/v1/subscriptions/my-plan", headers=vendor_headers)
    assert plan_resp.status_code == 200
    assert plan_resp.json()["data"]["plan_name"] == test_plan_gold.name
    assert plan_resp.json()["data"]["max_products"] == test_plan_gold.max_products


def test_stripe_webhook_payment_intent_succeeded(client, customer_headers, test_customer, test_product, active_vendor_subscription):
    client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 1},
        headers=customer_headers,
    )
    co_resp = client.post(
        "/api/v1/orders/checkout",
        json={"shipping_address": "555 Market St, San Francisco, CA 94105", "payment_method": "STRIPE"},
        headers=customer_headers,
    )
    order_id = co_resp.json()["data"]["id"]

    webhook_event = {
        "id": "evt_test_pi_123",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_succeeded_direct_111",
                "metadata": {
                    "order_id": str(order_id),
                }
            }
        }
    }

    response = client.post(
        "/api/v1/payments/webhook",
        content=json.dumps(webhook_event),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200

    get_resp = client.get(f"/api/v1/orders/{order_id}", headers=customer_headers)
    assert get_resp.json()["data"]["payment_status"] == PaymentStatus.SUCCESS.value


def test_stripe_webhook_subscription_deleted(client, db_session, test_vendor, test_plan_silver, active_vendor_subscription):
    active_vendor_subscription.stripe_subscription_id = "sub_to_be_canceled_999"
    db_session.commit()

    webhook_event = {
        "id": "evt_test_sub_del_123",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_to_be_canceled_999",
            }
        }
    }

    response = client.post(
        "/api/v1/payments/webhook",
        content=json.dumps(webhook_event),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200

    db_session.refresh(active_vendor_subscription)
    assert active_vendor_subscription.status == SubscriptionStatus.CANCELED
