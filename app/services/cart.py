import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.cart import Cart
from app.models.product import ProductStatus
from app.models.user import User, UserRole
from app.repositories.cart import CartRepository
from app.repositories.product import ProductRepository
from app.schemas.cart import CartItemAdd, CartItemOut, CartItemUpdate, CartOut

logger = logging.getLogger(__name__)


class CartService:
    def __init__(self, db: Session):
        self.db = db
        self.cart_repo = CartRepository(db)
        self.prod_repo = ProductRepository(db)

    def _get_cart(self, user: Optional[User], session_token: Optional[str] = None) -> Cart:
        user_id = user.id if user else None
        return self.cart_repo.get_or_create(user_id=user_id, session_token=session_token)

    def _build_cart_out(self, cart: Cart) -> CartOut:
        items_out: list[CartItemOut] = []
        subtotal = 0.0
        total_items = 0

        for item in cart.items:
            prod = item.product
            if not prod:
                continue

            price = float(prod.price)
            line_subtotal = round(price * item.quantity, 2)
            subtotal += line_subtotal
            total_items += item.quantity

            primary_img = next((img.image_url for img in prod.images if img.is_primary), None)
            if not primary_img and prod.images:
                primary_img = prod.images[0].image_url

            items_out.append(
                CartItemOut(
                    id=item.id,
                    cart_id=item.cart_id,
                    product_id=item.product_id,
                    vendor_id=item.vendor_id,
                    product_name=prod.name,
                    product_sku=prod.sku,
                    quantity=item.quantity,
                    unit_price=price,
                    subtotal=line_subtotal,
                    image_url=primary_img,
                )
            )

        return CartOut(
            id=cart.id,
            user_id=cart.user_id,
            items=items_out,
            subtotal=round(subtotal, 2),
            total_items=total_items,
        )

    def get_cart(self, user: Optional[User], session_token: Optional[str] = None) -> CartOut:
        """Retrieve current cart content and calculated subtotal."""
        cart = self._get_cart(user, session_token)
        return self._build_cart_out(cart)

    def add_item(
        self,
        user: Optional[User],
        session_token: Optional[str],
        item_in: CartItemAdd,
    ) -> CartOut:
        """Add product to cart with inventory availability checks."""
        if user and user.role == UserRole.VENDOR:
            raise ForbiddenException("A Customer account is required to perform this action.")

        prod = self.prod_repo.get_by_id(item_in.product_id)
        if not prod or prod.status != ProductStatus.PUBLISHED or not prod.is_approved:
            raise NotFoundException(message=f"Product with ID {item_in.product_id} is not available for purchase")

        if prod.stock_quantity <= 0:
            raise BadRequestException(
                message=f"Product '{prod.name}' is currently out of stock.",
                details={"available_stock": 0, "requested": item_in.quantity},
            )

        cart = self._get_cart(user, session_token)

        # Check existing quantity of this product already in cart
        existing_item = next((item for item in cart.items if item.product_id == prod.id), None)
        current_cart_qty = existing_item.quantity if existing_item else 0
        total_requested_qty = current_cart_qty + item_in.quantity

        if total_requested_qty > prod.stock_quantity:
            if current_cart_qty > 0:
                raise BadRequestException(
                    message=(
                        f"Cannot add {item_in.quantity} more unit(s) of '{prod.name}'. "
                        f"You already have {current_cart_qty} in your cart (maximum available: {prod.stock_quantity})."
                    ),
                    details={"available_stock": prod.stock_quantity, "in_cart": current_cart_qty, "requested": item_in.quantity},
                )
            else:
                raise BadRequestException(
                    message=f"Requested quantity ({item_in.quantity}) exceeds available stock ({prod.stock_quantity})",
                    details={"available_stock": prod.stock_quantity, "requested": item_in.quantity},
                )

        self.cart_repo.add_or_update_item(
            cart_id=cart.id,
            product_id=prod.id,
            vendor_id=prod.vendor_id,
            price=float(prod.price),
            quantity=item_in.quantity,
        )
        self.db.expire_all()
        # Reload cart
        cart = self.cart_repo.get_by_id(cart.id)
        return self._build_cart_out(cart)

    def update_item_quantity(
        self,
        user: Optional[User],
        session_token: Optional[str],
        item_id: int,
        update_in: CartItemUpdate,
    ) -> CartOut:
        """Update line item quantity."""
        cart = self._get_cart(user, session_token)
        item = self.cart_repo.get_item(item_id)
        if not item or item.cart_id != cart.id:
            raise NotFoundException(message=f"Cart item {item_id} not found in current cart")

        prod = self.prod_repo.get_by_id(item.product_id)
        if prod and prod.stock_quantity < update_in.quantity:
            raise BadRequestException(
                message=f"Requested quantity ({update_in.quantity}) exceeds available stock ({prod.stock_quantity})",
                details={"available_stock": prod.stock_quantity, "requested": update_in.quantity},
            )

        self.cart_repo.update_item_quantity(item, update_in.quantity)
        self.db.expire_all()
        cart = self.cart_repo.get_by_id(cart.id)
        return self._build_cart_out(cart)

    def merge_guest_cart(self, user: User, session_token: Optional[str]) -> Optional[Cart]:
        """Transfers guest cart items into the authenticated customer's cart upon login."""
        if not session_token:
            return None

        guest_cart = self.cart_repo.get_by_session(session_token)
        if not guest_cart or not guest_cart.items:
            return None

        user_cart = self.cart_repo.get_or_create(user_id=user.id)

        for g_item in guest_cart.items:
            prod = self.prod_repo.get_by_id(g_item.product_id)
            if prod and prod.status == ProductStatus.PUBLISHED and prod.is_approved:
                existing = next((i for i in user_cart.items if i.product_id == prod.id), None)
                if existing:
                    existing.quantity = min(existing.quantity + g_item.quantity, prod.stock_quantity)
                else:
                    qty = min(g_item.quantity, prod.stock_quantity)
                    if qty > 0:
                        self.cart_repo.add_or_update_item(
                            cart_id=user_cart.id,
                            product_id=prod.id,
                            vendor_id=prod.vendor_id,
                            price=float(prod.price),
                            quantity=qty,
                        )

        self.cart_repo.clear_cart(guest_cart)
        self.db.commit()
        self.db.expire_all()
        return user_cart

    def remove_item(
        self,
        user: Optional[User],
        session_token: Optional[str],
        item_id: int,
    ) -> CartOut:
        """Remove item from cart."""
        cart = self._get_cart(user, session_token)
        item = self.cart_repo.get_item(item_id)
        if not item or item.cart_id != cart.id:
            raise NotFoundException(message=f"Cart item {item_id} not found in current cart")

        self.cart_repo.remove_item(item)
        self.db.expire_all()
        cart = self.cart_repo.get_by_id(cart.id)
        return self._build_cart_out(cart)

    def clear_cart(self, user: Optional[User], session_token: Optional[str]) -> CartOut:
        """Clear entire shopping cart."""
        cart = self._get_cart(user, session_token)
        self.cart_repo.clear_cart(cart)
        self.db.expire_all()
        cart = self.cart_repo.get_by_id(cart.id)
        return self._build_cart_out(cart)
