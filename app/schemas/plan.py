import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")


class PlanBase(BaseModel):
    name: str = Field(min_length=2, max_length=100, description="Plan name (e.g. Silver, Gold)")
    slug: Optional[str] = Field(default=None, max_length=100, description="Unique plan slug identifier")
    description: Optional[str] = Field(default=None, description="Detailed description of plan features")
    price: float = Field(default=0.0, ge=0.0, description="Subscription price per cycle")
    currency: str = Field(default="USD", max_length=10, description="Currency code (e.g. USD, INR)")
    billing_cycle: str = Field(default="MONTHLY", description="Billing periodicity (MONTHLY, YEARLY)")
    max_products: int = Field(default=10, ge=1, description="Maximum product listings allowed")
    commission_rate: float = Field(
        default=20.0,
        ge=0.0,
        le=100.0,
        description="Platform commission percentage (e.g. 20.0 for 20%)",
    )
    is_active: bool = Field(default=True, description="Whether the plan is available for selection")


class PlanCreate(PlanBase):
    @model_validator(mode="before")
    @classmethod
    def generate_slug_if_missing(cls, data):
        if isinstance(data, dict):
            name = data.get("name")
            slug = data.get("slug")
            if name and not slug:
                data["slug"] = slugify(name)
        return data


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    currency: Optional[str] = Field(default=None, max_length=10)
    billing_cycle: Optional[str] = None
    max_products: Optional[int] = Field(default=None, ge=1)
    commission_rate: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    is_active: Optional[bool] = None


class PlanOut(PlanBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
