from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CartItemAdd(BaseModel):
    product_id: int = Field(description="Product ID to add to cart")
    quantity: int = Field(default=1, ge=1, description="Quantity to purchase")


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, description="Updated quantity")


class CartItemOut(BaseModel):
    id: int
    cart_id: int
    product_id: int
    vendor_id: int
    product_name: str
    product_sku: str
    quantity: int
    unit_price: float
    subtotal: float
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CartOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    items: List[CartItemOut] = Field(default_factory=list)
    subtotal: float
    total_items: int

    model_config = ConfigDict(from_attributes=True)
