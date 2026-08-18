from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ProductImage(BaseModel):
    """
    Product Image entity supporting multiple images per product,
    primary selection, and custom display ordering.
    """
    __tablename__ = "product_images"

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    alt_text = Column(String(255), nullable=True)

    # Relationships
    product = relationship("Product", back_populates="images")

    def __repr__(self) -> str:
        return f"<ProductImage(id={self.id}, product_id={self.product_id}, is_primary={self.is_primary})>"
