"""
Application HTTP and API routers.
"""

from app.routers.admin import router as admin_router
from app.routers.api_v1 import api_v1_router
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.plans import router as plans_router
from app.routers.subscriptions import router as subscriptions_router
from app.routers.user import router as user_router
from app.routers.vendors import router as vendors_router

__all__ = [
    "api_v1_router",
    "auth_router",
    "health_router",
    "user_router",
    "plans_router",
    "subscriptions_router",
    "vendors_router",
    "admin_router",
]
