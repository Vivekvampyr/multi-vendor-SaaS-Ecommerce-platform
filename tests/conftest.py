from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.plan import Plan
from app.models.subscription import SubscriptionStatus, VendorSubscription
from app.models.user import User, UserRole

# In-memory SQLite database for deterministic, fast isolated test runs
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all schema tables before test session and drop afterwards."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_database():
    """Wipe data from tables between individual test functions."""
    with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def db_session():
    """Provide a standalone transactional database session for direct model manipulation."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_customer(db_session) -> User:
    """Create and return a sample customer user."""
    user = User(
        email="customer@example.com",
        hashed_password=hash_password("CustomerPass123!"),
        full_name="Alice Customer",
        role=UserRole.CUSTOMER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def customer_token(test_customer) -> str:
    return create_access_token(subject=test_customer.id, role=test_customer.role.value)


@pytest.fixture
def customer_headers(customer_token) -> dict:
    return {"Authorization": f"Bearer {customer_token}"}


@pytest.fixture
def test_vendor(db_session) -> User:
    """Create and return a sample vendor user."""
    user = User(
        email="vendor@example.com",
        hashed_password=hash_password("VendorPass123!"),
        full_name="Bob Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def vendor_token(test_vendor) -> str:
    return create_access_token(subject=test_vendor.id, role=test_vendor.role.value)


@pytest.fixture
def vendor_headers(vendor_token) -> dict:
    return {"Authorization": f"Bearer {vendor_token}"}


@pytest.fixture
def test_admin(db_session) -> User:
    """Create and return a sample administrator user."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Super Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(test_admin) -> str:
    return create_access_token(subject=test_admin.id, role=test_admin.role.value)


@pytest.fixture
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def test_plan_silver(db_session) -> Plan:
    """Create and return standard Silver plan (10 products, 20% commission)."""
    plan = Plan(
        name="Silver",
        slug="silver",
        description="Ideal for starter sellers.",
        price=19.99,
        currency="USD",
        billing_cycle="MONTHLY",
        max_products=10,
        commission_rate=20.00,
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def test_plan_gold(db_session) -> Plan:
    """Create and return Gold plan (20 products, 10% commission)."""
    plan = Plan(
        name="Gold",
        slug="gold",
        description="Best for growing vendors with lower commission.",
        price=49.99,
        currency="USD",
        billing_cycle="MONTHLY",
        max_products=20,
        commission_rate=10.00,
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


@pytest.fixture
def active_vendor_subscription(db_session, test_vendor, test_plan_silver) -> VendorSubscription:
    """Create and return an active subscription for test vendor under Silver plan."""
    sub = VendorSubscription(
        vendor_id=test_vendor.id,
        plan_id=test_plan_silver.id,
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime.now(timezone.utc),
        auto_renew=True,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub
