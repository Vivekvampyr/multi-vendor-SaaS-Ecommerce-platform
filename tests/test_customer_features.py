import pytest
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus


def test_wishlist_lifecycle(client, customer_headers, test_product):
    # 1. Add product to wishlist
    resp = client.post(
        "/api/v1/wishlist",
        json={"product_id": test_product.id},
        headers=customer_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["product_id"] == test_product.id
    assert data["product_name"] == test_product.name
    assert data["in_stock"] is True

    # 2. Add same product again (idempotent)
    resp2 = client.post(
        "/api/v1/wishlist",
        json={"product_id": test_product.id},
        headers=customer_headers,
    )
    assert resp2.status_code == 201

    # 3. List wishlist items
    list_resp = client.get("/api/v1/wishlist", headers=customer_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    assert len(items) == 1
    assert items[0]["product_id"] == test_product.id

    # 4. Remove product from wishlist
    del_resp = client.delete(f"/api/v1/wishlist/{test_product.id}", headers=customer_headers)
    assert del_resp.status_code == 200

    # 5. Verify wishlist is now empty
    list_resp_after = client.get("/api/v1/wishlist", headers=customer_headers)
    assert len(list_resp_after.json()["data"]) == 0


def test_customer_saved_addresses_management(client, customer_headers):
    # 1. Create first address (should auto-become default)
    addr1_payload = {
        "full_name": "John Doe",
        "phone_number": "+1 555-0199",
        "address_line1": "123 Main Street",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
        "country": "USA",
        "address_type": "HOME",
    }
    resp1 = client.post("/api/v1/addresses", json=addr1_payload, headers=customer_headers)
    assert resp1.status_code == 201
    addr1 = resp1.json()["data"]
    assert addr1["is_default"] is True
    addr1_id = addr1["id"]

    # 2. Create second address with is_default=True
    addr2_payload = {
        "full_name": "John Work",
        "phone_number": "+1 555-0200",
        "address_line1": "456 Corporate Blvd",
        "city": "Dallas",
        "state": "TX",
        "postal_code": "75001",
        "country": "USA",
        "is_default": True,
        "address_type": "WORK",
    }
    resp2 = client.post("/api/v1/addresses", json=addr2_payload, headers=customer_headers)
    assert resp2.status_code == 201
    addr2 = resp2.json()["data"]
    assert addr2["is_default"] is True
    addr2_id = addr2["id"]

    # 3. List addresses (addr2 should be default, addr1 non-default)
    list_resp = client.get("/api/v1/addresses", headers=customer_headers)
    assert list_resp.status_code == 200
    addresses = list_resp.json()["data"]
    assert len(addresses) == 2
    assert addresses[0]["id"] == addr2_id
    assert addresses[0]["is_default"] is True
    assert addresses[1]["id"] == addr1_id
    assert addresses[1]["is_default"] is False

    # 4. Switch default back to addr1
    switch_resp = client.put(f"/api/v1/addresses/{addr1_id}/default", headers=customer_headers)
    assert switch_resp.status_code == 200
    assert switch_resp.json()["data"]["is_default"] is True

    # 5. Update address details
    upd_resp = client.put(
        f"/api/v1/addresses/{addr1_id}",
        json={"city": "Round Rock"},
        headers=customer_headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["data"]["city"] == "Round Rock"

    # 6. Delete address
    del_resp = client.delete(f"/api/v1/addresses/{addr2_id}", headers=customer_headers)
    assert del_resp.status_code == 200

    list_resp_final = client.get("/api/v1/addresses", headers=customer_headers)
    assert len(list_resp_final.json()["data"]) == 1


def test_product_reviews_and_ratings(
    client,
    db_session,
    customer_headers,
    test_customer,
    test_product,
):
    # 1. Public view before reviews
    pub_resp = client.get(f"/api/v1/products/{test_product.id}/reviews")
    assert pub_resp.status_code == 200
    summary = pub_resp.json()["data"]
    assert summary["average_rating"] == 0.0
    assert summary["total_reviews"] == 0

    # 2. Customer submits review without having purchased -> is_verified_purchase = False
    rev_payload = {
        "rating": 5,
        "title": "Excellent Quality!",
        "comment": "Exceeded all expectations, premium craftsmanship.",
    }
    rev_resp = client.post(
        f"/api/v1/products/{test_product.id}/reviews",
        json=rev_payload,
        headers=customer_headers,
    )
    assert rev_resp.status_code == 201
    rev_data = rev_resp.json()["data"]
    assert rev_data["rating"] == 5
    assert rev_data["is_verified_purchase"] is False
    rev_id = rev_data["id"]

    # 3. Duplicate review attempt by same customer fails with 409 Conflict
    dup_resp = client.post(
        f"/api/v1/products/{test_product.id}/reviews",
        json=rev_payload,
        headers=customer_headers,
    )
    assert dup_resp.status_code == 409

    # 4. Update review
    upd_resp = client.put(
        f"/api/v1/reviews/{rev_id}",
        json={"rating": 4, "title": "Great (Revised)"},
        headers=customer_headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["data"]["rating"] == 4
    assert upd_resp.json()["data"]["title"] == "Great (Revised)"

    # 5. Public review summary aggregation
    summary_resp = client.get(f"/api/v1/products/{test_product.id}/reviews")
    assert summary_resp.status_code == 200
    sum_data = summary_resp.json()["data"]
    assert sum_data["average_rating"] == 4.0
    assert sum_data["total_reviews"] == 1
    assert sum_data["rating_breakdown"]["4"] == 1

    # 6. Delete review
    del_resp = client.delete(f"/api/v1/reviews/{rev_id}", headers=customer_headers)
    assert del_resp.status_code == 200


def test_verified_buyer_review_badge(
    client,
    db_session,
    customer_headers,
    test_customer,
    test_product,
):
    # Setup completed paid order for customer containing test_product
    order = Order(
        order_number="ORD-TEST-VERIFIED-01",
        customer_id=test_customer.id,
        status=OrderStatus.DELIVERED,
        payment_status=PaymentStatus.SUCCESS,
        subtotal_amount=test_product.price,
        total_amount=test_product.price,
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=test_product.id,
        vendor_id=test_product.vendor_id,
        product_name=test_product.name,
        product_sku=test_product.sku,
        unit_price=test_product.price,
        quantity=1,
        subtotal=test_product.price,
        status=OrderStatus.DELIVERED,
    )
    db_session.add(item)
    db_session.commit()

    # Customer submits review -> is_verified_purchase should be True
    rev_resp = client.post(
        f"/api/v1/products/{test_product.id}/reviews",
        json={"rating": 5, "title": "Verified Purchase Review", "comment": "Confirmed buyer review"},
        headers=customer_headers,
    )
    assert rev_resp.status_code == 201
    assert rev_resp.json()["data"]["is_verified_purchase"] is True
