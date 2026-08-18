#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "==> Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "==> Running Alembic Database Migrations..."
alembic upgrade head

echo "==> Seeding initial SaaS plans & categories..."
python -c "
from app.core.database import SessionLocal, engine, Base
from app.models.plan import Plan
from app.models.product import Category

db = SessionLocal()
try:
    Base.metadata.create_all(bind=engine)

    if db.query(Plan).count() == 0:
        p1 = Plan(name='Starter', description='Perfect for new vendors starting their online business.', price=0.0, max_products=10, commission_rate=15.0, is_active=True)
        p2 = Plan(name='Pro', description='Designed for expanding stores with larger catalogs and priority support.', price=29.99, max_products=100, commission_rate=8.0, is_active=True)
        p3 = Plan(name='Enterprise', description='Unlimited product listings with our lowest platform commission rate.', price=99.99, max_products=1000, commission_rate=3.0, is_active=True)
        db.add_all([p1, p2, p3])
        db.commit()
        print('Seeded default SaaS Plans: Starter, Pro, Enterprise')

    if db.query(Category).count() == 0:
        c1 = Category(name='Electronics', slug='electronics', description='Gadgets, accessories, and electronics', is_active=True)
        c2 = Category(name='Fashion & Apparel', slug='fashion-apparel', description='Clothing, footwear, and accessories', is_active=True)
        c3 = Category(name='Home & Living', slug='home-living', description='Furniture, kitchenware, and home decor', is_active=True)
        c4 = Category(name='Beauty & Care', slug='beauty-care', description='Skincare, cosmetics, and self-care products', is_active=True)
        db.add_all([c1, c2, c3, c4])
        db.commit()
        print('Seeded default Categories: Electronics, Fashion, Home, Beauty')
except Exception as e:
    print('Seeding notice:', e)
finally:
    db.close()
"

echo "==> Build complete!"
