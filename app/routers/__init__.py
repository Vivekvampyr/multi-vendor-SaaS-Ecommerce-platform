"""
Application HTTP and API routers.
"""

from app.routers.addresses import router as addresses_router
from app.routers.admin import router as admin_router
from app.routers.ai import router as ai_router
from app.routers.api_v1 import api_v1_router
from app.routers.auth import router as auth_router
from app.routers.cart import router as cart_router
from app.routers.categories import router as categories_router
from app.routers.chat import router as chat_router
from app.routers.coupons import router as coupons_router
from app.routers.health import router as health_router
from app.routers.orders import router as orders_router
from app.routers.plans import router as plans_router
from app.routers.products import router as products_router
from app.routers.reviews import router as reviews_router
from app.routers.subscriptions import router as subscriptions_router
from app.routers.user import router as user_router
from app.routers.vendors import router as vendors_router
from app.routers.wishlist import router as wishlist_router

__all__ = [
    "api_v1_router",
    "auth_router",
    "health_router",
    "user_router",
    "plans_router",
    "subscriptions_router",
    "vendors_router",
    "categories_router",
    "products_router",
    "coupons_router",
    "cart_router",
    "orders_router",
    "wishlist_router",
    "addresses_router",
    "reviews_router",
    "chat_router",
    "ai_router",
    "admin_router",
]

