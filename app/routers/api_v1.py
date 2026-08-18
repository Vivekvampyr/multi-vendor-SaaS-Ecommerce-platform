from fastapi import APIRouter
from app.routers import admin, auth, health, plans, subscriptions, user

api_v1_router = APIRouter()

# Mount API v1 sub-routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(user.router)
api_v1_router.include_router(plans.router)
api_v1_router.include_router(subscriptions.router)
api_v1_router.include_router(admin.router)
