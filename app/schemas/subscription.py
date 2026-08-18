from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.subscription import SubscriptionStatus
from app.schemas.plan import PlanOut


class VendorSubscriptionBase(BaseModel):
    vendor_id: int
    plan_id: int
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    start_date: datetime
    end_date: Optional[datetime] = None
    auto_renew: bool = Field(default=True)


class VendorSubscriptionOut(VendorSubscriptionBase):
    id: int
    plan: PlanOut
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorPlanSelectRequest(BaseModel):
    plan_id: int = Field(description="Target SaaS Plan ID to subscribe to")


class VendorPlanAssignRequest(BaseModel):
    plan_id: int = Field(description="SaaS Plan ID to assign to vendor")
    status: SubscriptionStatus = Field(
        default=SubscriptionStatus.ACTIVE,
        description="Subscription state to set",
    )
    duration_days: Optional[int] = Field(
        default=30,
        ge=1,
        description="Subscription duration in days",
    )


class VendorPlanLimitsOut(BaseModel):
    vendor_id: int
    plan_id: int
    plan_name: str
    max_products: int
    commission_rate: float
    subscription_status: SubscriptionStatus
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
