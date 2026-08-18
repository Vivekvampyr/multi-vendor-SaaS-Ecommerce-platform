# Multi-Vendor SaaS E-Commerce Platform

A production-oriented, scalable SaaS Multi-Vendor E-Commerce platform built with **Python**, **FastAPI**, **SQLAlchemy 2.x**, **PostgreSQL**, **Alembic**, and a server-rendered modern UI using **Jinja2** + **Tailwind CSS**.

---

## 📌 Project Status: Phase 8 Active (Customer Features & Wishlist Completed)

This project is built incrementally across clearly defined phases.
* **Phase 1 (Project Foundation)**: Completed
* **Phase 2 (Authentication & RBAC)**: Completed
* **Phase 3 (Admin & SaaS Plans)**: Completed
* **Phase 4 (Vendor Management)**: Completed
* **Phase 5 (Product Management)**: Completed
* **Phase 6 (Coupons, Discounts & Offers)**: Completed
* **Phase 7 (Cart, Orders & Payments)**: Completed
* **Phase 8 (Customer Features & Wishlist)**: Completed
* **Next Phase**: **Phase 9 (Real-time Live Chat Subsystem)**

---

## 🏗️ Architecture & Technology Stack

### Backend
- **Framework**: FastAPI (Async & Sync support, Pydantic v2 validation)
- **Database ORM**: SQLAlchemy 2.x (Connection pooling with `pool_pre_ping=True`)
- **Database Migrations**: Alembic
- **Database Engine**: PostgreSQL (`psycopg2-binary`)
- **Settings & Config**: `pydantic-settings` (Type-safe `.env` loading)
- **Security & Authentication**: `bcrypt==4.0.1`, `PyJWT` (JWT Access & Refresh token rotation)
- **Role-Based Access Control (RBAC)**: `ADMIN`, `VENDOR`, `CUSTOMER`
- **SaaS Subscription Engine**: Dynamic plan limits, commission percentage tiers, and vendor subscriptions
- **Vendor Store Subsystem**: Storefront profile customization, administrative verification status (`PENDING`, `APPROVED`, `REJECTED`, `SUSPENDED`), and unified vendor dashboard metrics
- **Product & Catalog Subsystem**: Hierarchical categories, multi-image product catalog with local/cloud upload storage, SKU and inventory tracking, and dynamic SaaS plan listing limit enforcement
- **Promotions & Discount Engine**: Platform-wide and vendor-scoped coupons, percentage & fixed amount calculation, maximum discount caps, minimum order value thresholds, date-range scheduling, and global/per-user usage limit tracking
- **Multi-Vendor Cart, Orders & Settlement Engine**: Guest & customer shopping carts, stock checks, multi-vendor order checkout, plan-based platform commission calculation per item, vendor earnings ledger, simulated payment gateway integration, and line-item fulfillment tracking
- **Customer Experience & Social Proof Engine**: Customer product wishlists, saved multi-address management with default designation, and product star ratings (1-5) with automated verified buyer purchase history verification

### Frontend (Server-Side Rendered)
- **Template Engine**: Jinja2
- **Styling**: Tailwind CSS (CDN) + Custom Vanilla CSS
- **Interactivity**: Vanilla JavaScript (Fetch API & WebSocket API)

---

## 📁 Directory Structure

```text
app/
├── __init__.py
├── main.py                   # Application initialization, middleware, routes, static/template/uploads mounting
├── core/
│   ├── __init__.py
│   ├── config.py             # Pydantic Settings v2 configuration
│   ├── database.py           # SQLAlchemy 2.0 Engine, sessionmaker, and get_db dependency
│   ├── dependencies.py       # Authentication, RBAC, ownership, and optional user dependencies
│   ├── exceptions.py         # Custom application exceptions and global error handlers
│   └── security.py           # bcrypt password hashing and JWT token handlers
├── models/
│   ├── __init__.py           # Model exports for Alembic auto-discovery
│   ├── address.py            # Address model & AddressType enum (HOME, WORK, OTHER)
│   ├── base.py               # Declarative Base, BaseModel, and TimestampMixin
│   ├── cart.py               # Cart & CartItem models
│   ├── category.py           # Category model (hierarchical parent-child support)
│   ├── coupon.py             # Coupon model (PERCENTAGE/FIXED, limits, vendor scope)
│   ├── coupon_usage.py       # CouponUsage model (tracking user redemptions)
│   ├── order.py              # Order & OrderItem models (OrderStatus, PaymentStatus)
│   ├── plan.py               # SaaS Plan model (product listing limits & commission %)
│   ├── product.py            # Product model (SKU, inventory, pricing, status)
│   ├── product_image.py      # ProductImage model (multi-image, primary selector)
│   ├── review.py             # Review model (ratings, verified buyer badges)
│   ├── subscription.py       # VendorSubscription model (status, lifecycle, duration)
│   ├── user.py               # User model & UserRole enum (ADMIN, VENDOR, CUSTOMER)
│   ├── vendor.py             # VendorProfile model & VendorStatus enum
│   └── wishlist.py           # WishlistItem model (user saved products)
├── schemas/
│   ├── __init__.py
│   ├── address.py            # AddressCreate, AddressOut, AddressUpdate schemas
│   ├── admin.py              # AdminDashboardStats schema
│   ├── auth.py               # UserLogin, TokenResponse, TokenRefresh schemas
│   ├── cart.py               # CartItemAdd, CartItemOut, CartOut
│   ├── category.py           # CategoryCreate, CategoryOut, CategoryUpdate
│   ├── common.py             # Standardized APIResponse, ErrorResponse, HealthResponse
│   ├── coupon.py             # CouponCreate, CouponOut, CouponValidateRequest, CouponValidationResult
│   ├── order.py              # OrderCheckoutRequest, OrderOut, OrderItemOut, OrderPayRequest
│   ├── plan.py               # PlanCreate, PlanOut, PlanUpdate schemas
│   ├── product.py            # ProductCreate, ProductOut, ProductImageOut
│   ├── review.py             # ReviewCreate, ReviewOut, ProductReviewSummary
│   ├── subscription.py       # VendorSubscriptionOut, VendorPlanLimitsOut schemas
│   ├── user.py               # UserCreate, UserOut, UserUpdate, UserPasswordUpdate
│   ├── vendor.py             # VendorProfileCreate, VendorProfileOut, VendorDashboardOverview
│   └── wishlist.py           # WishlistItemAdd, WishlistItemOut
├── routers/
│   ├── __init__.py
│   ├── addresses.py          # Saved Customer Addresses API (/addresses)
│   ├── admin.py              # Admin dashboard metrics and vendor store moderation
│   ├── api_v1.py             # Main API v1 router aggregator
│   ├── auth.py               # Auth endpoints (/register, /login, /refresh, /me)
│   ├── cart.py               # Shopping cart management (/cart)
│   ├── categories.py         # Category public catalog & admin CRUD (/categories)
│   ├── coupons.py            # Coupon creation, management & validation (/coupons)
│   ├── health.py             # Health check endpoints (/health, /api/v1/health)
│   ├── orders.py             # Multi-vendor checkout, orders & payment processing (/orders)
│   ├── plans.py              # SaaS Plan public catalog & admin CRUD (/plans)
│   ├── products.py           # Product catalog, multi-image upload & management (/products)
│   ├── reviews.py            # Product Reviews & Ratings API (/reviews & /products/{id}/reviews)
│   ├── subscriptions.py      # Vendor plan selection, limits, and cancellation
│   ├── user.py               # User management endpoints (/users/me, /users)
│   ├── vendors.py            # Vendor storefront, profile, and dashboard (/vendors)
│   └── wishlist.py           # Customer Wishlist API (/wishlist)
├── services/
│   ├── __init__.py
│   ├── address.py            # AddressService (address CRUD, default switching)
│   ├── admin.py              # Admin metrics aggregation service
│   ├── auth.py               # AuthService (registration, auth, token generation)
│   ├── cart.py               # CartService (cart items, stock checks)
│   ├── category.py           # CategoryService (category lifecycle & validation)
│   ├── coupon.py             # CouponService (promotions, limits & discount calculation)
│   ├── order.py              # OrderService (checkout, commission splits, payments)
│   ├── plan.py               # PlanService (plan creation, constraints, validation)
│   ├── product.py            # ProductService (listing limit enforcement, multi-image)
│   ├── review.py             # ReviewService (ratings, verified checks, statistical aggregation)
│   ├── subscription.py       # SubscriptionService (plan assignment, limits, lifecycle)
│   ├── user.py               # UserService (profile updates, password change)
│   ├── vendor.py             # VendorService (store setup, dashboard, admin review)
│   └── wishlist.py           # WishlistService (wishlist items, availability)
├── repositories/
│   ├── __init__.py
│   ├── address.py            # AddressRepository (CRUD for customer addresses)
│   ├── cart.py               # CartRepository (CRUD for carts and items)
│   ├── category.py           # CategoryRepository (CRUD for categories)
│   ├── coupon.py             # CouponRepository (CRUD for coupons & usage logs)
│   ├── order.py              # OrderRepository (CRUD for orders and line items)
│   ├── plan.py               # PlanRepository (CRUD for SaaS plans)
│   ├── product.py            # ProductRepository & ProductImageRepository
│   ├── review.py             # ReviewRepository (reviews, purchase checks, rating statistics)
│   ├── subscription.py       # SubscriptionRepository (CRUD for vendor subscriptions)
│   ├── user.py               # UserRepository (CRUD for User)
│   ├── vendor.py             # VendorRepository (CRUD for VendorProfile)
│   └── wishlist.py           # WishlistRepository (CRUD for wishlist items)
├── templates/
│   ├── base.html             # Main Jinja2 layout with Tailwind CSS
│   └── index.html            # Foundation status view
├── static/
│   ├── css/style.css         # Custom utility and glassmorphism styling
│   └── js/main.js            # Vanilla JavaScript entrypoint
└── utils/
    ├── __init__.py
    ├── logging.py            # Structured logging setup
    ├── seed.py               # Seed script for initial Admin, plans, and categories
    └── uploads.py            # Multi-image upload, validation & cleanup utility

uploads/                      # Product and media upload directory (served statically)
└── products/

alembic/                      # Alembic database migrations
├── env.py
├── script.py.mako
└── versions/
    ├── 2026_08_18_0001_create_users_table.py
    ├── 2026_08_18_0002_create_plans_and_subscriptions.py
    ├── 2026_08_18_0003_create_vendor_profiles_table.py
    ├── 2026_08_18_0004_create_categories_products_images_tables.py
    ├── 2026_08_18_0005_create_coupons_and_usage_tables.py
    ├── 2026_08_18_0006_create_cart_and_orders_tables.py
    └── 2026_08_18_0007_create_customer_features_tables.py

tests/                        # Automated test suite (90 tests passing)
├── __init__.py
├── conftest.py               # Fixtures, test database, and role-based test tokens
├── test_admin.py             # Admin metrics and manual assignment tests
├── test_auth.py              # Auth & token lifecycle tests
├── test_config_and_errors.py
├── test_coupons.py           # Coupon creation, isolation, limits, and calculation tests
├── test_customer_features.py # Wishlist, Address, and Verified Review tests
├── test_health.py
├── test_orders.py            # Cart, checkout, multi-vendor splits & payment tests
├── test_plans.py             # Plan CRUD, validation, and permissions tests
├── test_products.py          # Category, Product, Multi-Image, and Plan Limit tests
├── test_rbac.py              # Role permissions & ownership tests
├── test_subscriptions.py     # Vendor subscription and limit enforcement tests
├── test_users.py             # Profile and password change tests
└── test_vendors.py           # Vendor profile, dashboard, and moderation tests

.env.example
.gitignore
alembic.ini
requirements.txt
README.md
```

---

## 🚀 Getting Started

### 1. Create and Activate Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate on Linux/macOS
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Database Migrations (Alembic)

```bash
# Apply migrations
alembic upgrade head
```

### 4. Seed Initial Data (Admin, SaaS Plans, and Categories)

```bash
python -m app.utils.seed
```
* Seeds Admin user: `admin@platform.com` / `AdminSecurePass123!`
* Seeds `Silver` Plan: 10 max products, 20% commission ($19.99/mo)
* Seeds `Gold` Plan: 20 max products, 10% commission ($49.99/mo)
* Seeds Default Categories: `Electronics`, `Fashion & Apparel`, `Home & Living`

### 5. Run Development Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🔑 Phase 8 API Endpoints

### Customer Wishlist (`/api/v1/wishlist`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/wishlist` | List customer wishlist products | `CUSTOMER` only |
| `POST` | `/api/v1/wishlist` | Add product to wishlist | `CUSTOMER` only |
| `DELETE` | `/api/v1/wishlist/{product_id}` | Remove product from wishlist | `CUSTOMER` only |

### Saved Customer Addresses (`/api/v1/addresses`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/addresses` | List saved addresses | Authenticated User |
| `POST` | `/api/v1/addresses` | Add new saved address | Authenticated User |
| `PUT` | `/api/v1/addresses/{id}` | Update address details | Owner / Admin |
| `PUT` | `/api/v1/addresses/{id}/default` | Set address as primary default | Owner / Admin |
| `DELETE` | `/api/v1/addresses/{id}` | Delete saved address | Owner / Admin |

### Product Reviews & Ratings (`/api/v1/reviews` & `/api/v1/products/{id}/reviews`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/products/{id}/reviews` | Get reviews & 1-5 star statistical rating breakdown | Public |
| `POST` | `/api/v1/products/{id}/reviews` | Submit product review (with verified buyer check) | `CUSTOMER` only |
| `PUT` | `/api/v1/reviews/{id}` | Update existing review | Owner / Admin |
| `DELETE` | `/api/v1/reviews/{id}` | Delete review | Owner / Admin |

---

## 🧪 Running Automated Tests

```bash
pytest -v
```
*(All 90 unit and integration tests passing)*

---

## 🔜 Next Step

* **PHASE 9 — Real-time Live Chat Subsystem** (WebSocket connection manager, `ChatMessage` entity, bidirectional live messaging between customers and store vendors, unread message badges, and conversation history).
