import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.cart import Cart
from app.models.product import ProductStatus
from app.models.user import User
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
        prod = self.prod_repo.get_by_id(item_in.product_id)
        if not prod or prod.status != ProductStatus.PUBLISHED or not prod.is_approved:
            raise NotFoundException(message=f"Product with ID {item_in.product_id} is not available for purchase")

        if prod.stock_quantity < item_in.quantity:
            raise BadRequestException(
                message=f"Requested quantity ({item_in.quantity}) exceeds available stock ({prod.stock_quantity})",
                details={"available_stock": prod.stock_quantity, "requested": item_in.quantity},
            )

        cart = self._get_cart(user, session_token)
        self.cart_repo.add_or_update_item(
            cart_id=cart.id,
            product_id=prod.id,
            vendor_id=prod.vendor_id,
            price=float(prod.price),
            quantity=item_in.quantity,
        )
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
        cart = self.cart_repo.get_by_id(cart.id)
        return self._build_cart_out(cart)

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
        self.db.expire(cart)
        cart = self.cart_repo.get_by_id(cart.id)
        return self._build_cart_out(cart)

    def clear_cart(self, user: Optional[User], session_token: Optional[str]) -> CartOut:
        """Empty shopping cart."""
        cart = self._get_cart(user, session_token)
        self.cart_repo.clear_cart(cart)
        self.db.expire(cart)
        cart = self.cart_repo.get_by_id(cart.id)
        return self._build_cart_out(cart)
