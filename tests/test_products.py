import io
import pytest
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.vendor import VendorProfile, VendorStatus


def test_admin_create_category_success(client, admin_headers):
    payload = {
        "name": "Smartphones",
        "description": "Latest mobile smartphones and devices",
    }
    response = client.post("/api/v1/categories", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Smartphones"
    assert data["data"]["slug"] == "smartphones"


def test_public_list_categories(client, test_category):
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1
    assert data["data"][0]["slug"] == test_category.slug


def test_vendor_create_product_success(
    client, vendor_headers, test_vendor_profile, active_vendor_subscription, test_category
):
    payload = {
        "category_id": test_category.id,
        "name": "Ultra Slim 4K Smart Monitor",
        "sku": "MON-4K-001",
        "description": "27-inch 4K IPS display with HDR400.",
        "short_description": "Crystal clear 4K monitor.",
        "price": 349.99,
        "compare_at_price": 399.99,
        "stock_quantity": 25,
        "status": "PUBLISHED",
    }
    response = client.post("/api/v1/products", json=payload, headers=vendor_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["sku"] == "MON-4K-001"
    assert data["data"]["slug"] == "ultra-slim-4k-smart-monitor"
    assert data["data"]["price"] == 349.99
    assert data["data"]["compare_at_price"] == 399.99
    assert data["data"]["short_description"] == "Crystal clear 4K monitor."
    assert data["data"]["stock_quantity"] == 25


def test_create_product_duplicate_sku_fails(
    client, vendor_headers, test_vendor_profile, active_vendor_subscription, test_product
):
    payload = {
        "category_id": test_product.category_id,
        "name": "Duplicate SKU Product",
        "sku": test_product.sku,  # same SKU
        "price": 99.99,
    }
    response = client.post("/api/v1/products", json=payload, headers=vendor_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_vendor_without_active_subscription_cannot_create_product(
    client, vendor_headers, test_vendor_profile, test_category
):
    # test_vendor starts without active subscription in this isolated test
    payload = {
        "category_id": test_category.id,
        "name": "Unauthorized Product Listing",
        "sku": "UNAUTH-001",
        "price": 49.99,
    }
    response = client.post("/api/v1/products", json=payload, headers=vendor_headers)
    assert response.status_code == 403
    assert "active SaaS subscription is required" in response.json()["error"]["message"]


def test_plan_product_listing_limit_enforcement(
    client, vendor_headers, test_vendor_profile, active_vendor_subscription, test_category, db_session
):
    # Silver plan has max_products = 10.
    # Seed 10 existing products directly for test_vendor
    from app.models.product import Product, ProductStatus
    for i in range(10):
        prod = Product(
            vendor_id=test_vendor_profile.user_id,
            category_id=test_category.id,
            name=f"Bulk Product {i}",
            slug=f"bulk-product-{i}",
            sku=f"BULK-SKU-{i:03d}",
            price=19.99,
            stock_quantity=10,
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(prod)
    db_session.commit()

    # Attempt to create the 11th product
    payload = {
        "category_id": test_category.id,
        "name": "Exceeding Limit Product",
        "sku": "LIMIT-EXCEED-001",
        "price": 29.99,
    }
    response = client.post("/api/v1/products", json=payload, headers=vendor_headers)
    assert response.status_code == 403
    assert "Product listing limit reached" in response.json()["error"]["message"]


def test_product_ownership_vendor_isolation(client, db_session, test_product, test_category):
    # Create Vendor B
    vendor_b = User(
        email="vendor_b@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Vendor B",
        role=UserRole.VENDOR,
        is_active=True,
    )
    db_session.add(vendor_b)
    db_session.commit()
    token_b = create_access_token(subject=vendor_b.id, role=vendor_b.role.value)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Vendor B attempts to update Vendor A's product
    update_payload = {"name": "Hacked Product Title"}
    response = client.put(f"/api/v1/products/{test_product.id}", json=update_payload, headers=headers_b)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

    # Vendor B attempts to delete Vendor A's product
    delete_response = client.delete(f"/api/v1/products/{test_product.id}", headers=headers_b)
    assert delete_response.status_code == 403


def test_admin_can_update_any_product(client, admin_headers, test_product):
    update_payload = {"price": 179.99}
    response = client.put(f"/api/v1/products/{test_product.id}", json=update_payload, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["data"]["price"] == 179.99


def test_multi_image_upload_and_primary_switch(client, vendor_headers, test_product):
    # Upload 2 fake image files
    file1_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."  # mock png
    file2_content = b"\xff\xd8\xff\xe0\x00\x10JFIF..."         # mock jpg

    files = [
        ("files", ("image1.png", io.BytesIO(file1_content), "image/png")),
        ("files", ("image2.jpg", io.BytesIO(file2_content), "image/jpeg")),
    ]

    response = client.post(
        f"/api/v1/products/{test_product.id}/images",
        files=files,
        headers=vendor_headers,
    )
    assert response.status_code == 201
    images = response.json()["data"]
    assert len(images) == 2
    assert images[0]["is_primary"] is True
    assert images[1]["is_primary"] is False

    image1_id = images[0]["id"]
    image2_id = images[1]["id"]

    # Set image 2 as primary
    primary_resp = client.put(
        f"/api/v1/products/{test_product.id}/images/{image2_id}/primary",
        headers=vendor_headers,
    )
    assert primary_resp.status_code == 200
    assert primary_resp.json()["data"]["is_primary"] is True

    # Delete image 1
    del_resp = client.delete(
        f"/api/v1/products/{test_product.id}/images/{image1_id}",
        headers=vendor_headers,
    )
    assert del_resp.status_code == 200


def test_upload_invalid_file_extension_fails(client, vendor_headers, test_product):
    files = [
        ("files", ("malicious.exe", io.BytesIO(b"binary executable"), "application/octet-stream")),
    ]
    response = client.post(
        f"/api/v1/products/{test_product.id}/images",
        files=files,
        headers=vendor_headers,
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["error"]["message"]


def test_public_product_search_and_filters(client, test_product):
    # Filter by search
    resp_search = client.get("/api/v1/products?search=Headphones")
    assert resp_search.status_code == 200
    assert len(resp_search.json()["data"]) >= 1

    # Filter by price range
    resp_price = client.get("/api/v1/products?min_price=100&max_price=300")
    assert resp_price.status_code == 200
    assert len(resp_price.json()["data"]) >= 1

    # Filter by price range (out of bounds)
    resp_empty = client.get("/api/v1/products?min_price=500&max_price=600")
    assert resp_empty.status_code == 200
    assert len(resp_empty.json()["data"]) == 0


def test_add_product_image_by_url_success(client, vendor_headers, test_product):
    payload = {
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e",
        "is_primary": True,
        "alt_text": "High-Res Studio Shot"
    }
    response = client.post(
        f"/api/v1/products/{test_product.id}/images/url",
        json=payload,
        headers=vendor_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["image_url"] == payload["image_url"]
    assert data["is_primary"] is True


def test_create_product_with_initial_image_url(client, vendor_headers, test_vendor_profile, active_vendor_subscription, test_category):
    payload = {
        "category_id": test_category.id,
        "name": "Mechanical Keyboard RGB",
        "sku": "KB-RGB-001",
        "price": 129.99,
        "stock_quantity": 30,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3",
    }
    response = client.post(
        "/api/v1/products",
        json=payload,
        headers=vendor_headers,
    )
    assert response.status_code == 201
    prod = response.json()["data"]
    assert len(prod["images"]) == 1
    assert prod["images"][0]["image_url"] == payload["image_url"]
    assert prod["images"][0]["is_primary"] is True


def test_product_suggestions_feature(
    client, vendor_headers, test_vendor_profile, active_vendor_subscription, test_category, test_product, db_session
):
    from app.models.product import Product, ProductStatus

    # Seed 2 complementary products in the same category
    p2 = Product(
        vendor_id=test_vendor_profile.user_id,
        category_id=test_category.id,
        name="Related Wireless Mouse",
        slug="related-wireless-mouse",
        sku="MOUSE-REL-01",
        price=49.99,
        stock_quantity=20,
        status=ProductStatus.PUBLISHED,
        is_approved=True,
    )
    p3 = Product(
        vendor_id=test_vendor_profile.user_id,
        category_id=test_category.id,
        name="Related Mouse Pad XXL",
        slug="related-mouse-pad-xxl",
        sku="PAD-REL-02",
        price=19.99,
        stock_quantity=15,
        status=ProductStatus.PUBLISHED,
        is_approved=True,
    )
    # Seed a product in a DIFFERENT category
    from app.models.category import Category
    diff_cat = Category(name="Different Category", slug="different-cat", is_active=True)
    db_session.add(diff_cat)
    db_session.commit()
    p_diff = Product(
        vendor_id=test_vendor_profile.user_id,
        category_id=diff_cat.id,
        name="Unrelated Appliance",
        slug="unrelated-appliance",
        sku="UNREL-01",
        price=199.99,
        stock_quantity=10,
        status=ProductStatus.PUBLISHED,
        is_approved=True,
    )
    db_session.add_all([p2, p3, p_diff])
    db_session.commit()

    # Test suggestions API endpoint
    resp = client.get(f"/api/v1/products/{test_product.id}/suggestions?limit=4")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 2
    # Ensure current product is not in suggestions
    suggested_ids = [p["id"] for p in data]
    assert test_product.id not in suggested_ids
    assert p2.id in suggested_ids
    assert p3.id in suggested_ids
    assert p_diff.id not in suggested_ids  # Strictly category based!

    # Test web view renders suggested products section
    web_resp = client.get(f"/products/{test_product.slug}")
    assert web_resp.status_code == 200
    assert "Related Category" in web_resp.text
    assert "Related Wireless Mouse" in web_resp.text
    assert "Unrelated Appliance" not in web_resp.text
