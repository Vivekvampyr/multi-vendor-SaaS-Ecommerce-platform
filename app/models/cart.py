from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Cart(BaseModel):
    """
    Shopping Cart entity supporting customer users or guest sessions.
    """
    __tablename__ = "carts"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    session_token = Column(String(100), nullable=True, index=True)

    # Relationships
    user = relationship("User", backref="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Cart(id={self.id}, user_id={self.user_id}, items_count={len(self.items)})>"


class CartItem(BaseModel):
    """
    Individual item line in a shopping cart with vendor association and price capture.
    """
    __tablename__ = "cart_items"

    cart_id = Column(
        Integer,
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity = Column(Integer, default=1, nullable=False)
    price_at_addition = Column(Numeric(10, 2), nullable=False)

    # Relationships
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
    vendor = relationship("User")

    def __repr__(self) -> str:
        return f"<CartItem(id={self.id}, cart_id={self.cart_id}, product_id={self.product_id}, qty={self.quantity})>"
