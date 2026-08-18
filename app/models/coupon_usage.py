from sqlalchemy import Column, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class CouponUsage(BaseModel):
    """
    Tracks individual customer redemptions of a promotional coupon code.
    """
    __tablename__ = "coupon_usages"

    coupon_id = Column(
        Integer,
        ForeignKey("coupons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id = Column(Integer, nullable=True, index=True)
    discount_amount = Column(Numeric(10, 2), nullable=False)

    # Relationships
    coupon = relationship("Coupon", back_populates="usages")
    user = relationship("User", backref="coupon_usages")

    def __repr__(self) -> str:
        return f"<CouponUsage(id={self.id}, coupon_id={self.coupon_id}, user_id={self.user_id}, discount={self.discount_amount})>"
