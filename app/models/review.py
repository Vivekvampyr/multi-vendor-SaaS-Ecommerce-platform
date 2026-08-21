from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Review(BaseModel):
    """
    Product Review and Star Rating entity submitted by customers.
    Supports official vendor replies from product merchants.
    """
    __tablename__ = "reviews"

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
    rating = Column(Integer, nullable=False)  # 1 to 5 stars
    title = Column(String(150), nullable=True)
    comment = Column(Text, nullable=True)
    is_verified_purchase = Column(Boolean, default=False, nullable=False)
    vendor_reply = Column(Text, nullable=True)
    vendor_reply_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="reviews")
    product = relationship("Product", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, product_id={self.product_id}, rating={self.rating}, verified={self.is_verified_purchase})>"
