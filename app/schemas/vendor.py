from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.vendor import VendorStatus
from app.schemas.plan import slugify
from app.schemas.subscription import VendorPlanLimitsOut, VendorSubscriptionOut


class VendorProfileBase(BaseModel):
    store_name: str = Field(min_length=2, max_length=150, description="Display name for the vendor store")
    slug: Optional[str] = Field(default=None, max_length=150, description="URL-friendly unique store slug")
    store_description: Optional[str] = Field(default=None, description="About the store / bio")
    logo_url: Optional[str] = Field(default=None, description="URL to store logo")
    banner_url: Optional[str] = Field(default=None, description="URL to store banner")
    support_email: Optional[EmailStr] = Field(default=None, description="Customer support email")
    support_phone: Optional[str] = Field(default=None, max_length=50, description="Customer support phone number")
    business_address: Optional[str] = Field(default=None, description="Registered business street address")
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    tax_id: Optional[str] = Field(default=None, max_length=100, description="Tax / VAT registration ID")
    is_store_active: bool = Field(default=True, description="Toggle whether store is open for business")


class VendorProfileCreate(VendorProfileBase):
    @model_validator(mode="before")
    @classmethod
    def generate_slug_if_missing(cls, data):
        if isinstance(data, dict):
            name = data.get("store_name")
            slug = data.get("slug")
            if name and not slug:
                data["slug"] = slugify(name)
        return data


class VendorProfileUpdate(BaseModel):
    store_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    slug: Optional[str] = Field(default=None, max_length=150)
    store_description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    support_email: Optional[EmailStr] = None
    support_phone: Optional[str] = None
    business_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    tax_id: Optional[str] = None
    is_store_active: Optional[bool] = None


class VendorProfileOut(VendorProfileBase):
    id: int
    user_id: int
    status: VendorStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorStatusUpdate(BaseModel):
    status: VendorStatus = Field(description="Target verification state (APPROVED, REJECTED, SUSPENDED, PENDING)")
    rejection_reason: Optional[str] = Field(default=None, description="Reason if rejected or suspended")


class VendorDashboardOverview(BaseModel):
    vendor_profile: Optional[VendorProfileOut] = None
    subscription: Optional[VendorSubscriptionOut] = None
    plan_limits: Optional[VendorPlanLimitsOut] = None
    status: VendorStatus
    can_list_products: bool = Field(description="Whether the vendor is approved and has an active subscription")
    store_is_live: bool = Field(description="Whether the store is approved and active for public viewing")

    model_config = ConfigDict(from_attributes=True)


class PublicVendorStoreOut(BaseModel):
    id: int
    user_id: int
    store_name: str
    slug: str
    store_description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    status: VendorStatus
    is_store_active: bool
    product_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
