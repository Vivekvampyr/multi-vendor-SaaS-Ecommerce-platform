import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class DiscountType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class Coupon(BaseModel):
    """
    Coupon entity representing promotional discounts.
    Can be platform-wide (vendor_id = None) or vendor-specific.
    """
    __tablename__ = "coupons"

    code = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(
        Enum(
            DiscountType,
            name="discount_type_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=DiscountType.PERCENTAGE,
        nullable=False,
    )
    discount_value = Column(Numeric(10, 2), nullable=False)
    max_discount_amount = Column(Numeric(10, 2), nullable=True)
    min_order_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    usage_limit = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0, nullable=False)
    user_limit = Column(Integer, default=1, nullable=False)
    vendor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    vendor = relationship("User", backref="coupons")
    usages = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Coupon(id={self.id}, code='{self.code}', type={self.discount_type}, value={self.discount_value})>"
