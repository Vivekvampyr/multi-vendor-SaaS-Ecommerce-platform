# Multi-Vendor SaaS E-Commerce Platform

A production-oriented, scalable SaaS Multi-Vendor E-Commerce platform built with **Python**, **FastAPI**, **SQLAlchemy 2.x**, **PostgreSQL**, **Alembic**, and a server-rendered modern UI using **Jinja2** + **Tailwind CSS**.

---

## 📌 Project Status: Phase 3 Active (Admin & SaaS Plans Completed)

This project is built incrementally across clearly defined phases.
* **Phase 1 (Project Foundation)**: Completed
* **Phase 2 (Authentication & RBAC)**: Completed
* **Phase 3 (Admin & SaaS Plans)**: Completed
* **Next Phase**: **Phase 4 (Vendor Management)**

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
- **SaaS Subscription Subsystem**: Dynamic SaaS plan creation, product listing limits, and platform commission tiers

### Frontend (Server-Side Rendered)
- **Template Engine**: Jinja2
- **Styling**: Tailwind CSS (CDN) + Custom Vanilla CSS
- **Interactivity**: Vanilla JavaScript (Fetch API & WebSocket API)

---

## 📁 Directory Structure

```text
app/
├── __init__.py
├── main.py                   # Application initialization, middleware, routes, static/template mounting
├── core/
│   ├── __init__.py
│   ├── config.py             # Pydantic Settings v2 configuration
│   ├── database.py           # SQLAlchemy 2.0 Engine, sessionmaker, and get_db dependency
│   ├── dependencies.py       # Authentication, RBAC, and ownership dependencies
│   ├── exceptions.py         # Custom application exceptions and global error handlers
│   └── security.py           # bcrypt password hashing and JWT token handlers
├── models/
│   ├── __init__.py           # Model exports for Alembic auto-discovery
│   ├── base.py               # Declarative Base, BaseModel, and TimestampMixin
│   ├── plan.py               # SaaS Plan model (product listing limits & commission %)
│   ├── subscription.py       # VendorSubscription model (status, lifecycle, duration)
│   └── user.py               # User model & UserRole enum (ADMIN, VENDOR, CUSTOMER)
├── schemas/
│   ├── __init__.py
│   ├── admin.py              # AdminDashboardStats schema
│   ├── auth.py               # UserLogin, TokenResponse, TokenRefresh schemas
│   ├── common.py             # Standardized APIResponse, ErrorResponse, HealthResponse
│   ├── plan.py               # PlanCreate, PlanOut, PlanUpdate schemas
│   ├── subscription.py       # VendorSubscriptionOut, VendorPlanLimitsOut schemas
│   └── user.py               # UserCreate, UserOut, UserUpdate, UserPasswordUpdate
├── routers/
│   ├── __init__.py
│   ├── admin.py              # Admin dashboard metrics and subscription overrides
│   ├── api_v1.py             # Main API v1 router aggregator
│   ├── auth.py               # Auth endpoints (/register, /login, /refresh, /me)
│   ├── health.py             # Health check endpoints (/health, /api/v1/health)
│   ├── plans.py              # SaaS Plan public catalog & admin CRUD (/plans)
│   ├── subscriptions.py      # Vendor plan selection, limits, and cancellation
│   └── user.py               # User management endpoints (/users/me, /users)
├── services/
│   ├── __init__.py
│   ├── admin.py              # Admin metrics aggregation service
│   ├── auth.py               # AuthService (registration, auth, token generation)
│   ├── plan.py               # PlanService (plan creation, constraints, validation)
│   ├── subscription.py       # SubscriptionService (plan assignment, limits, lifecycle)
│   └── user.py               # UserService (profile updates, password change)
├── repositories/
│   ├── __init__.py
│   ├── plan.py               # PlanRepository (CRUD for SaaS plans)
│   ├── subscription.py       # SubscriptionRepository (CRUD for vendor subscriptions)
│   └── user.py               # UserRepository (CRUD for User)
├── templates/
│   ├── base.html             # Main Jinja2 layout with Tailwind CSS
│   └── index.html            # Foundation status view
├── static/
│   ├── css/style.css         # Custom utility and glassmorphism styling
│   └── js/main.js            # Vanilla JavaScript entrypoint
└── utils/
    ├── __init__.py
    ├── logging.py            # Structured logging setup
    └── seed.py               # Seed script for initial Admin and default plans

alembic/                      # Alembic database migrations
├── env.py
├── script.py.mako
└── versions/
    ├── 2026_08_18_0001_create_users_table.py
    └── 2026_08_18_0002_create_plans_and_subscriptions.py

tests/                        # Automated test suite (50 tests passing)
├── __init__.py
├── conftest.py               # Fixtures, test database, and role-based test tokens
├── test_admin.py             # Admin metrics and manual assignment tests
├── test_auth.py              # Auth & token lifecycle tests
├── test_config_and_errors.py
├── test_health.py
├── test_plans.py             # Plan CRUD, validation, and permissions tests
├── test_rbac.py              # Role permissions & ownership tests
├── test_subscriptions.py     # Vendor subscription and limit enforcement tests
└── test_users.py             # Profile and password change tests

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
# Apply migrations to create users, plans, and subscriptions tables
alembic upgrade head
```

### 4. Seed Initial Data (Admin & Default SaaS Plans)

```bash
python -m app.utils.seed
```
* Seeds Admin user: `admin@platform.com` / `AdminSecurePass123!`
* Seeds `Silver` Plan: 10 max products, 20% commission ($19.99/mo)
* Seeds `Gold` Plan: 20 max products, 10% commission ($49.99/mo)

### 5. Run Development Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🔑 Phase 3 API Endpoints

### SaaS Plans (`/api/v1/plans`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/plans` | List available active SaaS plans | Public |
| `GET` | `/api/v1/plans/{plan_id}` | Retrieve specific plan details | Public |
| `POST` | `/api/v1/plans` | Create a new SaaS plan | `ADMIN` only |
| `PUT` | `/api/v1/plans/{plan_id}` | Update SaaS plan pricing or limits | `ADMIN` only |
| `DELETE` | `/api/v1/plans/{plan_id}` | Delete SaaS plan (blocked if active subscribers) | `ADMIN` only |

### Vendor Subscriptions (`/api/v1/subscriptions`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/subscriptions/my-plan` | View active plan limits and commission % | `VENDOR` only |
| `POST` | `/api/v1/subscriptions/select-plan` | Select or switch SaaS plan | `VENDOR` only |
| `POST` | `/api/v1/subscriptions/cancel` | Cancel active SaaS plan subscription | `VENDOR` only |

### Admin Operations (`/api/v1/admin`)
| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/admin/dashboard` | Aggregated platform metrics and analytics | `ADMIN` only |
| `GET` | `/api/v1/admin/subscriptions` | List all vendor subscriptions | `ADMIN` only |
| `POST` | `/api/v1/admin/vendors/{id}/assign-plan` | Manually assign or override vendor plan | `ADMIN` only |

---

## 🧪 Running Automated Tests

```bash
pytest -v
```
*(All 50 unit and integration tests passing)*

---

## 🔜 Next Step

* **PHASE 4 — Vendor Management** (Vendor profile, Vendor dashboard API, Vendor verification status, Vendor subscription display, Vendor settings).
