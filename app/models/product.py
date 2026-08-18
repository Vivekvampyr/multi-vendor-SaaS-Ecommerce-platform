import enum
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ProductStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    ARCHIVED = "ARCHIVED"


class Product(BaseModel):
    """
    Product entity representing goods listed by vendors.
    Maintains SKU, pricing, inventory stock, ownership, and image associations.
    """
    __tablename__ = "products"

    vendor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    compare_at_price = Column(Numeric(10, 2), nullable=True)
    stock_quantity = Column(Integer, default=0, nullable=False)
    status = Column(
        Enum(
            ProductStatus,
            name="product_status_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ProductStatus.DRAFT,
        nullable=False,
        index=True,
    )
    is_approved = Column(Boolean, default=True, nullable=False)

    # Relationships
    vendor = relationship("User", backref="products")
    category = relationship("Category", back_populates="products")
    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.display_order.asc()",
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', sku='{self.sku}', price={self.price})>"
