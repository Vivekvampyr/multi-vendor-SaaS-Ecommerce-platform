from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user_for_web
from app.models.subscription import SubscriptionStatus
from app.models.user import User, UserRole
from app.repositories.category import CategoryRepository
from app.repositories.order import OrderRepository
from app.repositories.subscription import SubscriptionRepository
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

import html
import re
from markupsafe import Markup

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
TEMPLATES_DIR = BASE_DIR / "templates"
ASSETS_CATEGORY_DIR = PROJECT_ROOT / "assets" / "category"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render_markdown_filter(text: Optional[str]) -> Markup:
    """
    Renders structured Markdown text into safe, beautifully styled HTML with headings,
    bullet lists, bold highlights, and clean paragraph breaks.
    """
    if not text or not str(text).strip():
        return Markup('<p class="text-xs sm:text-sm text-slate-500 dark:text-zinc-400">No description provided.</p>')

    # 1. Normalize line endings and separate inline headings / bullets that lack newlines
    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = re.sub(r"([^\n])\s*(#{1,4}\s+[A-Za-z0-9])", r"\1\n\n\2", normalized)
    normalized = re.sub(r"([^\n])\s+([-\*]\s+\*\*)", r"\1\n\2", normalized)
    normalized = re.sub(r"([^\n])\s+([-\*]\s+[A-Za-z0-9])", r"\1\n\2", normalized)
    normalized = re.sub(
        r"^(#{1,4}\s+[^\n]+?)\s+([A-Z][a-z0-9]+(?:\s+[a-z0-9]+){3,})",
        r"\1\n\n\2",
        normalized,
        flags=re.MULTILINE,
    )

    # 2. Escape raw HTML for security
    escaped = html.escape(normalized)

    # 3. Format Bold **text** -> <strong>
    escaped = re.sub(
        r"\*\*(.+?)\*\*",
        r'<strong class="font-bold text-slate-900 dark:text-white">\1</strong>',
        escaped,
    )
    # Format Italic *text* -> <em>
    escaped = re.sub(
        r"\*(.+?)\*",
        r'<em class="italic text-slate-700 dark:text-zinc-300">\1</em>',
        escaped,
    )

    lines = escaped.splitlines()
    html_blocks = []
    in_list = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line in ("#", "##", "###", "####"):
            if in_list:
                html_blocks.append("</ul>")
                in_list = False
            continue

        if line.startswith("### "):
            if in_list:
                html_blocks.append("</ul>")
                in_list = False
            title = line[4:].strip()
            html_blocks.append(
                f'<h4 class="text-xs sm:text-sm font-bold text-slate-900 dark:text-white mt-4 mb-1.5 tracking-tight"><span class="inline-block w-1.5 h-1.5 rounded-full bg-slate-700 dark:bg-zinc-300 mr-1.5 align-middle"></span>{title}</h4>'
            )
        elif line.startswith("## "):
            if in_list:
                html_blocks.append("</ul>")
                in_list = False
            title = line[3:].strip()
            html_blocks.append(
                f'<h3 class="text-sm sm:text-base font-bold text-slate-900 dark:text-white mt-4 mb-2"><span class="inline-block w-2 h-2 rounded-full bg-slate-700 dark:bg-zinc-300 mr-2 align-middle"></span>{title}</h3>'
            )
        elif line.startswith("# "):
            if in_list:
                html_blocks.append("</ul>")
                in_list = False
            title = line[2:].strip()
            html_blocks.append(
                f'<h2 class="text-base sm:text-lg font-bold text-slate-900 dark:text-white mt-5 mb-2">{title}</h2>'
            )
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_blocks.append(
                    '<ul class="space-y-1.5 my-2 text-xs sm:text-sm text-slate-700 dark:text-zinc-300">'
                )
                in_list = True
            content = line[2:].strip()
            html_blocks.append(
                f'<li class="flex items-start space-x-2"><span class="text-slate-700 dark:text-zinc-300 font-bold shrink-0 mt-0.5">•</span><span class="flex-1 leading-relaxed">{content}</span></li>'
            )
        else:
            if in_list:
                html_blocks.append("</ul>")
                in_list = False
            html_blocks.append(
                f'<p class="text-xs sm:text-sm text-slate-700 dark:text-zinc-300 leading-relaxed mb-2.5">{line}</p>'
            )

    if in_list:
        html_blocks.append("</ul>")

    return Markup("\n".join(html_blocks))


def strip_markdown_filter(text: Optional[str]) -> str:
    """
    Strips raw markdown syntax characters for plain-text card previews.
    """
    if not text:
        return ""
    cleaned = str(text)
    cleaned = re.sub(r"#+\s*", "", cleaned)
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*(.+?)\*", r"\1", cleaned)
    cleaned = re.sub(r"-\s*", "", cleaned)
    return " ".join(cleaned.split())


# Register Jinja2 filters
templates.env.filters["markdown"] = render_markdown_filter
templates.env.filters["strip_markdown"] = strip_markdown_filter



def get_category_icon_info(category) -> dict:
    """
    Returns the appropriate icon image path and fallback emoji for a given category.
    Gracefully falls back to suitable emojis if the icon image is absent or fails to load.
    """
    if not category:
        return {"icon_url": None, "fallback_emoji": "📦"}

    # If category has custom image_url explicitly saved
    custom_img = getattr(category, "image_url", None)
    if custom_img and str(custom_img).strip():
        return {"icon_url": str(custom_img).strip(), "fallback_emoji": "📦"}

    name = str(getattr(category, "name", "") or "").lower().strip()
    slug = str(getattr(category, "slug", "") or "").lower().strip().replace("-", "_")

    # Match against available category icons in assets/category/
    if "electronic" in slug or "electronic" in name or "tech" in slug or "gadget" in slug or "phone" in slug:
        return {"icon_url": "/assets/category/electronics.png", "fallback_emoji": "⚡"}
    elif "fashion" in slug or "apparel" in slug or "cloth" in name or "wear" in slug or "fashion" in name or "apparel" in name:
        return {"icon_url": "/assets/category/fashion_and_apparel.png", "fallback_emoji": "👗"}
    elif "home" in slug or "living" in slug or "furniture" in slug or "decor" in name or "home" in name:
        return {"icon_url": "/assets/category/home_and_living.png", "fallback_emoji": "🛋️"}

    # Check for direct file match in assets/category/<slug>.png
    if (ASSETS_CATEGORY_DIR / f"{slug}.png").exists():
        return {"icon_url": f"/assets/category/{slug}.png", "fallback_emoji": "📦"}

    return {"icon_url": None, "fallback_emoji": "📦"}


def _get_user_wishlist_ids(db: Session, user: Optional[User]) -> set[int]:
    if not user or user.role != UserRole.CUSTOMER:
        return set()
    wishlist_service = WishlistService(db)
    items = wishlist_service.list_wishlist(user=user, limit=200)
    return {item.product_id for item in items}


templates.env.globals["get_category_icon"] = get_category_icon_info

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
    vendor_service = VendorService(db)

    plans, _ = plan_service.list_plans(only_active=True)
    categories = cat_repo.list(only_active=True, skip=0, limit=8)
    products, _ = prod_service.list_products(skip=0, limit=8)
    featured_stores, _ = vendor_service.list_public_stores(skip=0, limit=4)
    user_wishlist_ids = _get_user_wishlist_ids(db, current_user)

    active_plan_id = None
    if current_user and current_user.role == UserRole.VENDOR:
        sub_repo = SubscriptionRepository(db)
        active_sub = sub_repo.get_by_vendor_id(current_user.id)
        if active_sub and active_sub.status == SubscriptionStatus.ACTIVE and active_sub.plan_id:
            active_plan_id = active_sub.plan_id

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "current_user": current_user,
            "plans": plans,
            "categories": categories,
            "products": products,
            "featured_stores": featured_stores,
            "active_plan_id": active_plan_id,
            "user_wishlist_ids": user_wishlist_ids,
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
    user_wishlist_ids = _get_user_wishlist_ids(db, current_user)

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
            "user_wishlist_ids": user_wishlist_ids,
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

    has_purchased = False
    has_reviewed = False
    past_purchase = None
    user_review = None

    if current_user:
        order_repo = OrderRepository(db)
        past_purchase = order_repo.get_latest_purchase_info(user_id=current_user.id, product_id=product.id)
        has_purchased = (past_purchase is not None) or (current_user.role == UserRole.ADMIN)
        user_rev_model = review_service.review_repo.get_by_user_and_product(user_id=current_user.id, product_id=product.id)
        if user_rev_model:
            user_review = review_service._map_to_out(user_rev_model)
            has_reviewed = True

    user_wishlist_ids = _get_user_wishlist_ids(db, current_user)
    suggested_products = prod_service.get_suggested_products(product_id=product.id, limit=4)

    return templates.TemplateResponse(
        request=request,
        name="products/detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "product": product,
            "reviews_summary": reviews_summary,
            "has_purchased": has_purchased,
            "has_reviewed": has_reviewed,
            "past_purchase": past_purchase,
            "user_review": user_review,
            "user_wishlist_ids": user_wishlist_ids,
            "suggested_products": suggested_products,
        },
    )


@web_router.get("/stores", response_class=HTMLResponse)
async def stores_directory_page(
    request: Request,
    search: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    vendor_service = VendorService(db)
    stores, total = vendor_service.list_public_stores(search=search, skip=skip, limit=limit)

    return templates.TemplateResponse(
        request=request,
        name="stores/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "stores": stores,
            "total_stores": total,
            "search_query": search or "",
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
    user_wishlist_ids = _get_user_wishlist_ids(db, current_user)

    return templates.TemplateResponse(
        request=request,
        name="stores/detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "store": store,
            "products": products,
            "user_wishlist_ids": user_wishlist_ids,
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
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_for_web),
):
    if not current_user:
        return RedirectResponse(url="/login")

    order_service = OrderService(db)
    order = order_service.get_order_by_id(user=current_user, order_id=order_id)

    # Direct Stripe session verification on redirect (works even without webhook secret)
    if session_id and settings.is_stripe_configured and order.payment_status != PaymentStatus.SUCCESS:
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            sess = stripe.checkout.Session.retrieve(session_id)
            if sess.payment_status in ["paid", "complete"]:
                order_service.order_repo.update_order_status(
                    order=order,
                    status=OrderStatus.PAID,
                    payment_status=PaymentStatus.SUCCESS,
                    payment_reference=sess.payment_intent or sess.id,
                )
        except Exception:
            pass

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

    # Direct Stripe subscription verification on redirect (works without webhook secret)
    session_id = request.query_params.get("session_id")
    if session_id and settings.is_stripe_configured:
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            sess = stripe.checkout.Session.retrieve(session_id)
            if sess.status == "complete" or sess.payment_status in ["paid", "no_payment_required"]:
                plan_id_meta = sess.metadata.get("plan_id")
                if plan_id_meta:
                    sub_service = SubscriptionService(db)
                    sub = sub_service.assign_plan(
                        vendor_id=current_user.id,
                        plan_id=int(plan_id_meta),
                        status=SubscriptionStatus.ACTIVE,
                    )
                    sub.stripe_subscription_id = sess.subscription
                    sub.stripe_customer_id = sess.customer
                    db.commit()
        except Exception:
            pass

    vendor_service = VendorService(db)
    prod_service = ProductService(db)
    order_service = OrderService(db)
    plan_service = PlanService(db)

    vendor_dash = vendor_service.get_vendor_dashboard(vendor_user=current_user)
    _, total_products = prod_service.list_my_products(vendor_id=current_user.id)
    total_sold_units, total_net_revenue = order_service.get_vendor_sales_stats(vendor_id=current_user.id)
    available_plans, _ = plan_service.list_plans(only_active=True)

    overview = {
        "has_store": vendor_dash.vendor_profile is not None,
        "store_name": vendor_dash.vendor_profile.store_name if vendor_dash.vendor_profile else "",
        "store_slug": vendor_dash.vendor_profile.slug if vendor_dash.vendor_profile else "",
        "store_description": vendor_dash.vendor_profile.store_description if vendor_dash.vendor_profile else "",
        "support_email": vendor_dash.vendor_profile.support_email if vendor_dash.vendor_profile else "",
        "support_phone": vendor_dash.vendor_profile.support_phone if vendor_dash.vendor_profile else "",
        "business_address": vendor_dash.vendor_profile.business_address if vendor_dash.vendor_profile else "",
        "city": vendor_dash.vendor_profile.city if vendor_dash.vendor_profile else "",
        "state": vendor_dash.vendor_profile.state if vendor_dash.vendor_profile else "",
        "country": vendor_dash.vendor_profile.country if vendor_dash.vendor_profile else "",
        "postal_code": vendor_dash.vendor_profile.postal_code if vendor_dash.vendor_profile else "",
        "is_store_active": vendor_dash.vendor_profile.is_store_active if vendor_dash.vendor_profile else False,
        "active_plan_name": vendor_dash.plan_limits.plan_name if vendor_dash.plan_limits else "No Plan Selected",
        "active_plan_id": vendor_dash.plan_limits.plan_id if vendor_dash.plan_limits else None,
        "total_products": total_products,
        "max_products_allowed": vendor_dash.plan_limits.max_products if vendor_dash.plan_limits else 0,
        "total_orders": total_sold_units,
        "total_revenue": total_net_revenue,
        "commission_rate": vendor_dash.plan_limits.commission_rate if vendor_dash.plan_limits else 0.0,
        "status": vendor_dash.status,
        "can_list_products": vendor_dash.can_list_products,
        "store_is_live": vendor_dash.store_is_live,
    }

    return templates.TemplateResponse(
        request=request,
        name="vendor/dashboard.html",
        context={
            "request": request,
            "current_user": current_user,
            "overview": overview,
            "profile": vendor_dash.vendor_profile,
            "subscription": vendor_dash.subscription,
            "plans": available_plans,
        },
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

    from app.services.subscription import SubscriptionService

    admin_service = AdminService(db)
    vendor_service = VendorService(db)
    plan_service = PlanService(db)
    coupon_service = CouponService(db)
    sub_service = SubscriptionService(db)
    cat_repo = CategoryRepository(db)

    stats = admin_service.get_dashboard_stats()
    vendors, _ = vendor_service.admin_list_vendors(skip=0, limit=100)
    plans, _ = plan_service.list_plans(only_active=False, skip=0, limit=100)
    coupons, _ = coupon_service.list_coupons(user=current_user, skip=0, limit=100)
    subscriptions, _ = sub_service.list_subscriptions(skip=0, limit=100)
    categories = cat_repo.list(only_active=False, skip=0, limit=200)
    commission_transactions = admin_service.get_recent_commission_transactions(limit=50)

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "vendors": vendors,
            "plans": plans,
            "coupons": coupons,
            "subscriptions": subscriptions,
            "categories": categories,
            "commission_transactions": commission_transactions,
        },
    )
