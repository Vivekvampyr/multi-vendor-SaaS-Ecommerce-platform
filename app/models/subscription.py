import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    TRIALING = "TRIALING"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class VendorSubscription(BaseModel):
    """
    Vendor SaaS Plan Subscription.
    Links a Vendor user to an active SaaS Plan and tracks subscription lifecycle.
    """
    __tablename__ = "vendor_subscriptions"

    vendor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    plan_id = Column(
        Integer,
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(
            SubscriptionStatus,
            name="subscription_status_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    auto_renew = Column(Boolean, default=True, nullable=False)
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)

    # Relationships
    vendor = relationship("User", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")

    def __repr__(self) -> str:
        return (
            f"<VendorSubscription(id={self.id}, vendor_id={self.vendor_id}, "
            f"plan_id={self.plan_id}, status='{self.status}')>"
        )
