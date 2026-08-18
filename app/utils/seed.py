import logging
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.plan import Plan
from app.models.user import User, UserRole
from app.utils.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def seed_initial_data(db: Session) -> None:
    """
    Seed initial Admin account and default SaaS plans (Silver, Gold).
    """
    # 1. Seed Admin Account
    admin_email = "admin@platform.com"
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if not existing_admin:
        admin_user = User(
            email=admin_email,
            hashed_password=hash_password("AdminSecurePass123!"),
            full_name="Platform Super Admin",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin_user)
        logger.info("Seeded initial Admin user: %s", admin_email)
    else:
        logger.info("Admin user already exists: %s", admin_email)

    # 2. Seed Default Plans
    plans_data = [
        {
            "name": "Silver",
            "slug": "silver",
            "description": "Perfect for starter vendors with essential capabilities.",
            "price": 19.99,
            "currency": "USD",
            "billing_cycle": "MONTHLY",
            "max_products": 10,
            "commission_rate": 20.00,
            "is_active": True,
        },
        {
            "name": "Gold",
            "slug": "gold",
            "description": "Ideal for established sellers requiring high product limits and lower commissions.",
            "price": 49.99,
            "currency": "USD",
            "billing_cycle": "MONTHLY",
            "max_products": 20,
            "commission_rate": 10.00,
            "is_active": True,
        },
    ]

    for p in plans_data:
        existing_plan = db.query(Plan).filter(Plan.name == p["name"]).first()
        if not existing_plan:
            plan = Plan(**p)
            db.add(plan)
            logger.info("Seeded SaaS Plan: %s (Max: %d, Commission: %s%%)", p["name"], p["max_products"], p["commission_rate"])
        else:
            logger.info("SaaS Plan '%s' already exists", p["name"])

    # 3. Seed Default Product Categories
    from app.models.category import Category
    categories_data = [
        {"name": "Electronics", "slug": "electronics", "description": "Laptops, smartphones, audio, and gadgets."},
        {"name": "Fashion & Apparel", "slug": "fashion-apparel", "description": "Clothing, footwear, and accessories."},
        {"name": "Home & Living", "slug": "home-living", "description": "Furniture, decor, kitchen, and appliances."},
    ]
    for c in categories_data:
        existing_cat = db.query(Category).filter(Category.name == c["name"]).first()
        if not existing_cat:
            cat = Category(**c, is_active=True)
            db.add(cat)
            logger.info("Seeded Category: %s", c["name"])
        else:
            logger.info("Category '%s' already exists", c["name"])

    db.commit()
    logger.info("Initial data seeding completed successfully.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()
