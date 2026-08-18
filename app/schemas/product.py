from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.product import ProductStatus
from app.schemas.category import CategoryOut
from app.schemas.plan import slugify


class ProductImageOut(BaseModel):
    id: int
    product_id: int
    image_url: str
    is_primary: bool
    display_order: int
    alt_text: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    category_id: int = Field(description="Target Category ID")
    name: str = Field(min_length=2, max_length=255, description="Product title")
    slug: Optional[str] = Field(default=None, max_length=255, description="Unique product slug")
    sku: str = Field(min_length=2, max_length=100, description="Unique Stock Keeping Unit (SKU)")
    description: Optional[str] = Field(default=None, description="Full product description")
    short_description: Optional[str] = Field(default=None, max_length=500, description="Brief summary for listings")
    price: float = Field(ge=0.01, description="Selling price")
    compare_at_price: Optional[float] = Field(default=None, ge=0.01, description="Original reference price for discounts")
    stock_quantity: int = Field(default=0, ge=0, description="Available inventory count")
    status: ProductStatus = Field(default=ProductStatus.DRAFT, description="Product catalog status")


class ProductCreate(ProductBase):
    @model_validator(mode="before")
    @classmethod
    def generate_slug_if_missing(cls, data):
        if isinstance(data, dict):
            name = data.get("name")
            slug = data.get("slug")
            if name and not slug:
                data["slug"] = slugify(name)
            sku = data.get("sku")
            if sku and isinstance(sku, str):
                data["sku"] = sku.strip().upper()
        return data


class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    sku: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = None
    short_description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[float] = Field(default=None, ge=0.01)
    compare_at_price: Optional[float] = Field(default=None, ge=0.01)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    status: Optional[ProductStatus] = None
    is_approved: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    vendor_id: int
    category_id: int
    name: str
    slug: str
    sku: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: float
    compare_at_price: Optional[float] = None
    stock_quantity: int
    status: ProductStatus
    is_approved: bool
    images: List[ProductImageOut] = Field(default_factory=list)
    category: Optional[CategoryOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
