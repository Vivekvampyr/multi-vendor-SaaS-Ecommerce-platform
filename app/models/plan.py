from sqlalchemy import Boolean, Column, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Plan(BaseModel):
    """
    SaaS Subscription Plan defined by Administrator.
    Controls vendor product listing limits and platform commission percentage.
    """
    __tablename__ = "plans"

    name = Column(String(100), unique=True, index=True, nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), default=0.00, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    billing_cycle = Column(String(20), default="MONTHLY", nullable=False)
    max_products = Column(Integer, default=10, nullable=False)
    commission_rate = Column(Numeric(5, 2), default=20.00, nullable=False)  # e.g., 20.00%
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    subscriptions = relationship(
        "VendorSubscription",
        back_populates="plan",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Plan(id={self.id}, name='{self.name}', "
            f"max_products={self.max_products}, commission_rate={self.commission_rate}%)>"
        )
