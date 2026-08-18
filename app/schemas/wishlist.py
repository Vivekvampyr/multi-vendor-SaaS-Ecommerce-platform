from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WishlistItemAdd(BaseModel):
    product_id: int = Field(description="Product ID to add to wishlist")


class WishlistItemOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    product_name: str
    product_slug: str
    product_sku: str
    price: float
    image_url: Optional[str] = None
    in_stock: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
