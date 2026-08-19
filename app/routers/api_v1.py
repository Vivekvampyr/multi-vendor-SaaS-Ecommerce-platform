from fastapi import APIRouter
from app.routers import (
    addresses,
    admin,
    ai,
    auth,
    cart,
    categories,
    chat,
    coupons,
    health,
    orders,
    payments,
    plans,
    products,
    reviews,
    subscriptions,
    user,
    vendors,
    wishlist,
)

api_v1_router = APIRouter()

# Mount API v1 sub-routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(user.router)
api_v1_router.include_router(plans.router)
api_v1_router.include_router(subscriptions.router)
api_v1_router.include_router(vendors.router)
api_v1_router.include_router(categories.router)
api_v1_router.include_router(products.router)
api_v1_router.include_router(coupons.router)
api_v1_router.include_router(cart.router)
api_v1_router.include_router(orders.router)
api_v1_router.include_router(payments.router)
api_v1_router.include_router(wishlist.router)
api_v1_router.include_router(addresses.router)
api_v1_router.include_router(reviews.router)
api_v1_router.include_router(chat.router)
api_v1_router.include_router(ai.router)
api_v1_router.include_router(admin.router)

