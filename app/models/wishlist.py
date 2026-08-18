from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WishlistItem(BaseModel):
    """
    Wishlist entity tracking products saved by customers for later purchase.
    """
    __tablename__ = "wishlist_items"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_product_wishlist"),
    )

    # Relationships
    user = relationship("User", backref="wishlist_items")
    product = relationship("Product")

    def __repr__(self) -> str:
        return f"<WishlistItem(id={self.id}, user_id={self.user_id}, product_id={self.product_id})>"
