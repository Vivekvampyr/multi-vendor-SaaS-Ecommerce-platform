from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user_for_web
from app.models.user import User, UserRole
from app.repositories.category import CategoryRepository
from app.services.address import AddressService
from app.services.admin import AdminService
from app.services.cart import CartService
from app.services.coupon import CouponService
from app.services.order import OrderService
from app.services.plan import PlanService
from app.services.product import ProductService
from app.services.review import ReviewService
from app.services.vendor import VendorService
from app.services.wishlist import WishlistService

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

web_router = APIRouter(include_in_schema=False)


# ==============================================================================
# Public Marketplace & Storefront Pages
# ==============================================================================

@web_router.get("/", response_class=HTMLResponse)
async def home_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    plan_service = PlanService(db)
    cat_repo = CategoryRepository(db)
    prod_service = ProductService(db)

    plans, _ = plan_service.list_plans(only_active=True)
    categories = cat_repo.list(only_active=True, skip=0, limit=8)
    products, _ = prod_service.list_products(skip=0, limit=8)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "current_user": current_user,
            "plans": plans,
            "categories": categories,
            "products": products,
        },
    )


@web_router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if current_user:
        if current_user.role == UserRole.ADMIN:
            return RedirectResponse(url="/admin/dashboard")
        elif current_user.role == UserRole.VENDOR:
            return RedirectResponse(url="/vendor/dashboard")
        return RedirectResponse(url="/customer/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"request": request, "current_user": None},
    )


@web_router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if current_user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={"request": request, "current_user": None},
    )


@web_router.get("/products", response_class=HTMLResponse)
async def products_catalog_page(
    request: Request,
    category: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    cat_repo = CategoryRepository(db)
    prod_service = ProductService(db)

    categories = cat_repo.list(only_active=True)
    products, _ = prod_service.list_products(
        category_id=category,
        search=search,
        skip=0,
        limit=50,
    )

    return templates.TemplateResponse(
        request=request,
        name="products/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "categories": categories,
            "products": products,
            "selected_category": category,
            "search_query": search,
        },
    )


@web_router.get("/products/{slug}", response_class=HTMLResponse)
async def product_detail_page(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    prod_service = ProductService(db)
    product = prod_service.get_product_by_slug(slug)

    review_service = ReviewService(db)
    reviews_summary = review_service.get_product_reviews(product_id=product.id, skip=0, limit=20)

    return templates.TemplateResponse(
        request=request,
        name="products/detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "product": product,
            "reviews_summary": reviews_summary,
        },
    )


@web_router.get("/stores/{slug}", response_class=HTMLResponse)
async def store_detail_page(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    vendor_service = VendorService(db)
    store = vendor_service.get_public_store_profile(slug)

    prod_service = ProductService(db)
    products, _ = prod_service.list_products(vendor_id=store.user_id, skip=0, limit=50)

    return templates.TemplateResponse(
        request=request,
        name="stores/detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "store": store,
            "products": products,
        },
    )


# ==============================================================================
# Cart & Checkout Pages
# ==============================================================================

@web_router.get("/cart", response_class=HTMLResponse)
async def cart_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    cart_service = CartService(db)
    session_token = request.headers.get("X-Session-Token") or request.cookies.get("guest_session_token")
    cart = cart_service.get_cart(user=current_user, session_token=session_token)

    return templates.TemplateResponse(
        request=request,
        name="cart/index.html",
        context={
            "request": request,
            "current_user": current_user,
            "cart": cart,
        },
    )


@web_router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user:
        return RedirectResponse(url="/login?next=/checkout")

    cart_service = CartService(db)
    cart = cart_service.get_cart(user=current_user)

    addr_service = AddressService(db)
    addresses = addr_service.list_addresses(user=current_user)
    default_address = next((a for a in addresses if a.is_default), addresses[0] if addresses else None)

    return templates.TemplateResponse(
        request=request,
        name="cart/checkout.html",
        context={
            "request": request,
            "current_user": current_user,
            "cart": cart,
            "addresses": addresses,
            "default_address": default_address,
        },
    )


@web_router.get("/orders/{order_id}/success", response_class=HTMLResponse)
async def order_success_page(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user:
        return RedirectResponse(url="/login")

    order_service = OrderService(db)
    order = order_service.get_order_by_id(user=current_user, order_id=order_id)

    return templates.TemplateResponse(
        request=request,
        name="orders/success.html",
        context={
            "request": request,
            "current_user": current_user,
            "order": order,
        },
    )


# ==============================================================================
# Customer Portal Pages
# ==============================================================================

@web_router.get("/customer/dashboard", response_class=HTMLResponse)
async def customer_dashboard_page(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        request=request,
        name="customer/dashboard.html",
        context={"request": request, "current_user": current_user},
    )


@web_router.get("/customer/orders", response_class=HTMLResponse)
async def customer_orders_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user:
        return RedirectResponse(url="/login")

    order_service = OrderService(db)
    orders, _ = order_service.list_my_orders(customer_id=current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="customer/orders.html",
        context={"request": request, "current_user": current_user, "orders": orders},
    )


@web_router.get("/customer/wishlist", response_class=HTMLResponse)
async def customer_wishlist_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user:
        return RedirectResponse(url="/login")

    wishlist_service = WishlistService(db)
    wishlist = wishlist_service.list_wishlist(user=current_user)

    return templates.TemplateResponse(
        request=request,
        name="customer/wishlist.html",
        context={"request": request, "current_user": current_user, "wishlist": wishlist},
    )


@web_router.get("/customer/addresses", response_class=HTMLResponse)
async def customer_addresses_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user:
        return RedirectResponse(url="/login")

    addr_service = AddressService(db)
    addresses = addr_service.list_addresses(user=current_user)

    return templates.TemplateResponse(
        request=request,
        name="customer/addresses.html",
        context={"request": request, "current_user": current_user, "addresses": addresses},
    )


# ==============================================================================
# Vendor Merchant Portal Pages
# ==============================================================================

@web_router.get("/vendor/dashboard", response_class=HTMLResponse)
async def vendor_dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user or current_user.role != UserRole.VENDOR:
        return RedirectResponse(url="/login")

    vendor_service = VendorService(db)
    prod_service = ProductService(db)
    order_service = OrderService(db)

    vendor_dash = vendor_service.get_vendor_dashboard(vendor_user=current_user)
    _, total_products = prod_service.list_my_products(vendor_id=current_user.id)
    items, total_items = order_service.list_vendor_order_items(vendor_id=current_user.id)
    total_revenue = sum(float(i.vendor_earnings) for i in items)

    overview = {
        "store_name": vendor_dash.vendor_profile.store_name if vendor_dash.vendor_profile else current_user.full_name,
        "store_slug": vendor_dash.vendor_profile.slug if vendor_dash.vendor_profile else "",
        "active_plan_name": vendor_dash.plan_limits.plan_name if vendor_dash.plan_limits else "No Plan",
        "total_products": total_products,
        "max_products_allowed": vendor_dash.plan_limits.max_products if vendor_dash.plan_limits else 0,
        "total_orders": total_items,
        "total_revenue": total_revenue,
        "commission_rate": vendor_dash.plan_limits.commission_rate if vendor_dash.plan_limits else 0.0,
        "status": vendor_dash.status,
    }

    return templates.TemplateResponse(
        request=request,
        name="vendor/dashboard.html",
        context={"request": request, "current_user": current_user, "overview": overview},
    )


@web_router.get("/vendor/products", response_class=HTMLResponse)
async def vendor_products_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user or current_user.role != UserRole.VENDOR:
        return RedirectResponse(url="/login")

    prod_service = ProductService(db)
    cat_repo = CategoryRepository(db)

    products, _ = prod_service.list_my_products(vendor_id=current_user.id, skip=0, limit=100)
    categories = cat_repo.list(only_active=True)

    return templates.TemplateResponse(
        request=request,
        name="vendor/products.html",
        context={
            "request": request,
            "current_user": current_user,
            "products": products,
            "categories": categories,
        },
    )


@web_router.get("/vendor/orders", response_class=HTMLResponse)
async def vendor_orders_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user or current_user.role != UserRole.VENDOR:
        return RedirectResponse(url="/login")

    order_service = OrderService(db)
    items, _ = order_service.list_vendor_order_items(vendor_id=current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="vendor/orders.html",
        context={"request": request, "current_user": current_user, "items": items},
    )


@web_router.get("/vendor/coupons", response_class=HTMLResponse)
async def vendor_coupons_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user or current_user.role != UserRole.VENDOR:
        return RedirectResponse(url="/login")

    coupon_service = CouponService(db)
    coupons, _ = coupon_service.list_coupons(user=current_user)

    return templates.TemplateResponse(
        request=request,
        name="vendor/coupons.html",
        context={"request": request, "current_user": current_user, "coupons": coupons},
    )


# ==============================================================================
# Admin Portal Pages
# ==============================================================================

@web_router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user or current_user.role != UserRole.ADMIN:
        return RedirectResponse(url="/login")

    admin_service = AdminService(db)
    vendor_service = VendorService(db)

    stats = admin_service.get_dashboard_stats()
    vendors, _ = vendor_service.admin_list_vendors(skip=0, limit=100)

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "vendors": vendors,
        },
    )
