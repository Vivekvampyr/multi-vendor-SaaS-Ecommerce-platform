from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.cart import Cart, CartItem
from app.models.product import Product


class CartRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, cart_id: int) -> Optional[Cart]:
        """Fetch cart by ID with eager-loaded items and products."""
        stmt = (
            select(Cart)
            .options(
                joinedload(Cart.items).joinedload(CartItem.product).joinedload(Product.images),
            )
            .where(Cart.id == cart_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_user_id(self, user_id: int) -> Optional[Cart]:
        """Fetch cart by customer user ID."""
        stmt = (
            select(Cart)
            .options(
                joinedload(Cart.items).joinedload(CartItem.product).joinedload(Product.images),
            )
            .where(Cart.user_id == user_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_session(self, session_token: str) -> Optional[Cart]:
        """Fetch guest cart by session token."""
        stmt = (
            select(Cart)
            .options(
                joinedload(Cart.items).joinedload(CartItem.product).joinedload(Product.images),
            )
            .where(Cart.session_token == session_token)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_or_create(self, user_id: Optional[int] = None, session_token: Optional[str] = None) -> Cart:
        """Fetch existing cart or create a new one."""
        cart = None
        if user_id:
            cart = self.get_by_user_id(user_id)
        elif session_token:
            cart = self.get_by_session(session_token)

        if not cart:
            cart = Cart(user_id=user_id, session_token=session_token)
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        return cart

    def get_item(self, item_id: int) -> Optional[CartItem]:
        """Fetch a specific cart item."""
        stmt = select(CartItem).where(CartItem.id == item_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def add_or_update_item(
        self,
        cart_id: int,
        product_id: int,
        vendor_id: int,
        price: float,
        quantity: int = 1,
    ) -> CartItem:
        """Add product to cart or increment quantity if already present."""
        stmt = select(CartItem).where(
            CartItem.cart_id == cart_id,
            CartItem.product_id == product_id,
        )
        item = self.db.execute(stmt).scalar_one_or_none()
        if item:
            item.quantity += quantity
            item.price_at_addition = price
        else:
            item = CartItem(
                cart_id=cart_id,
                product_id=product_id,
                vendor_id=vendor_id,
                price_at_addition=price,
                quantity=quantity,
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(item)
        return item

    def update_item_quantity(self, item: CartItem, quantity: int) -> CartItem:
        """Set specific quantity for cart item."""
        item.quantity = quantity
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_item(self, item: CartItem) -> bool:
        """Remove single item from cart."""
        self.db.delete(item)
        self.db.commit()
        return True

    def clear_cart(self, cart: Cart) -> bool:
        """Remove all items from cart."""
        for item in cart.items:
            self.db.delete(item)
        self.db.commit()
        return True
