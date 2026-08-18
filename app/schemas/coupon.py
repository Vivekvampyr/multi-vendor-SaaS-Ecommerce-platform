from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.coupon import DiscountType


class CouponBase(BaseModel):
    code: str = Field(min_length=3, max_length=50, description="Unique coupon code (e.g. SAVE20)")
    description: Optional[str] = Field(default=None, description="Brief description of the promotion")
    discount_type: DiscountType = Field(default=DiscountType.PERCENTAGE, description="PERCENTAGE or FIXED")
    discount_value: float = Field(gt=0, description="Discount amount (% or currency value)")
    max_discount_amount: Optional[float] = Field(default=None, gt=0, description="Maximum discount cap for percentage types")
    min_order_amount: float = Field(default=0.0, ge=0, description="Minimum order subtotal required to apply")
    start_date: Optional[datetime] = Field(default=None, description="Promotion start date")
    end_date: Optional[datetime] = Field(default=None, description="Promotion expiration date")
    usage_limit: Optional[int] = Field(default=None, ge=1, description="Total redemption limit across all users")
    user_limit: int = Field(default=1, ge=1, description="Max redemptions permitted per customer user")
    vendor_id: Optional[int] = Field(default=None, description="Null for platform coupon, or specific vendor ID")
    is_active: bool = Field(default=True, description="Whether the coupon is active")


class CouponCreate(CouponBase):
    @model_validator(mode="before")
    @classmethod
    def clean_coupon_code(cls, data):
        if isinstance(data, dict):
            code = data.get("code")
            if code and isinstance(code, str):
                data["code"] = code.strip().upper()
        return data


class CouponUpdate(BaseModel):
    description: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = Field(default=None, gt=0)
    max_discount_amount: Optional[float] = Field(default=None, gt=0)
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    usage_limit: Optional[int] = Field(default=None, ge=1)
    user_limit: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class CouponOut(CouponBase):
    id: int
    used_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CouponValidateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50, description="Coupon code to validate")
    subtotal: float = Field(ge=0.01, description="Order subtotal amount to calculate discount on")
    vendor_id: Optional[int] = Field(default=None, description="Target vendor ID if validating for specific vendor items")


class CouponValidationResult(BaseModel):
    valid: bool
    code: str
    discount_type: DiscountType
    discount_value: float
    discount_amount: float
    subtotal: float
    final_total: float
    message: str

    model_config = ConfigDict(from_attributes=True)
