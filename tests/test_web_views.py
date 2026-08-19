from app.core.security import create_access_token
from app.models.category import Category
from app.models.product import Product, ProductStatus


def test_public_pages_render_html(client, db_session, test_vendor):
    # Setup sample category & product
    cat = Category(name="Electronics", slug="electronics")
    db_session.add(cat)
    db_session.commit()

    from app.models.vendor import VendorProfile, VendorStatus
    v_profile = db_session.query(VendorProfile).filter_by(user_id=test_vendor.id).first()
    if not v_profile:
        v_profile = VendorProfile(
            user_id=test_vendor.id,
            store_name="Tech Gadgets Store",
            slug="tech-gadgets-store",
            status=VendorStatus.APPROVED,
            is_store_active=True,
        )
        db_session.add(v_profile)
        db_session.commit()
    else:
        v_profile.status = VendorStatus.APPROVED
        v_profile.is_store_active = True
        db_session.commit()

    prod = Product(
        name="Ultra Smart Watch",
        slug="ultra-smart-watch",
        sku="WATCH-001",
        price=199.99,
        stock_quantity=50,
        vendor_id=test_vendor.id,
        category_id=cat.id,
        status=ProductStatus.PUBLISHED,
        is_approved=True,
    )
    db_session.add(prod)
    db_session.commit()

    # 1. Homepage
    resp_home = client.get("/")
    assert resp_home.status_code == 200
    assert "NexusSaaS" in resp_home.text
    assert "Ultra Smart Watch" in resp_home.text

    # 2. Login & Register
    resp_login = client.get("/login")
    assert resp_login.status_code == 200
    assert "Sign in to your NexusSaaS" in resp_login.text

    resp_reg = client.get("/register")
    assert resp_reg.status_code == 200
    assert "Create Account" in resp_reg.text

    # 3. Product Catalog
    resp_catalog = client.get("/products")
    assert resp_catalog.status_code == 200
    assert "Ultra Smart Watch" in resp_catalog.text

    prod.description = "### Product Overview\nElevate your setup with **Ultra Smart Watch**.\n\n### Key Features\n- **Battery**: 7 days\n- **Waterproof**: 5ATM"
    db_session.commit()

    # 4. Product Details
    resp_detail = client.get("/products/ultra-smart-watch")
    assert resp_detail.status_code == 200
    assert "Ultra Smart Watch" in resp_detail.text
    assert "WATCH-001" in resp_detail.text
    # Verify markdown rendered into styled HTML
    assert "<h4" in resp_detail.text
    assert "Product Overview" in resp_detail.text
    assert "<strong" in resp_detail.text
    assert "<ul" in resp_detail.text
    assert "<li" in resp_detail.text
    assert "###" not in resp_detail.text

    # 5. Public Storefront
    resp_store = client.get(f"/stores/tech-gadgets-store")
    assert resp_store.status_code == 200
    assert "Tech Gadgets Store" in resp_store.text

    # 6. Cart Page
    resp_cart = client.get("/cart")
    assert resp_cart.status_code == 200
    assert "Shopping Cart" in resp_cart.text


def test_authenticated_customer_portal_views(client, test_customer):
    token = create_access_token(subject=test_customer.id, role=test_customer.role.value)
    client.cookies.set("access_token", token)

    # 1. Checkout
    resp_checkout = client.get("/checkout")
    assert resp_checkout.status_code == 200
    assert "Secure Checkout" in resp_checkout.text

    # 2. Customer Dashboard
    resp_dash = client.get("/customer/dashboard")
    assert resp_dash.status_code == 200
    assert test_customer.full_name in resp_dash.text

    # 3. Orders
    resp_orders = client.get("/customer/orders")
    assert resp_orders.status_code == 200
    assert "Order History" in resp_orders.text

    # 4. Wishlist
    resp_wish = client.get("/customer/wishlist")
    assert resp_wish.status_code == 200
    assert "Saved Wishlist" in resp_wish.text

    # 5. Addresses
    resp_addr = client.get("/customer/addresses")
    assert resp_addr.status_code == 200
    assert "Delivery Addresses" in resp_addr.text


def test_authenticated_vendor_portal_views(client, test_vendor):
    token = create_access_token(subject=test_vendor.id, role=test_vendor.role.value)
    client.cookies.set("access_token", token)

    # 1. Vendor Dashboard
    resp_dash = client.get("/vendor/dashboard")
    assert resp_dash.status_code == 200
    assert "Merchant Dashboard" in resp_dash.text

    # 2. Vendor Products
    resp_prods = client.get("/vendor/products")
    assert resp_prods.status_code == 200
    assert "Store Catalog & Products" in resp_prods.text

    # 3. Vendor Orders
    resp_orders = client.get("/vendor/orders")
    assert resp_orders.status_code == 200
    assert "Sold Items & Fulfillment" in resp_orders.text

    # 4. Vendor Coupons
    resp_coupons = client.get("/vendor/coupons")
    assert resp_coupons.status_code == 200
    assert "Store Promotional Coupons" in resp_coupons.text


def test_authenticated_admin_portal_views(client, test_admin):
    token = create_access_token(subject=test_admin.id, role=test_admin.role.value)
    client.cookies.set("access_token", token)

    resp_admin = client.get("/admin/dashboard")
    assert resp_admin.status_code == 200
    assert "Platform Administration" in resp_admin.text
