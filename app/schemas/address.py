from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.address import AddressType


class AddressBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=255, description="Recipient full legal name")
    phone_number: str = Field(min_length=5, max_length=50, description="Contact phone number")
    address_line1: str = Field(min_length=3, max_length=255, description="Street address")
    address_line2: Optional[str] = Field(default=None, max_length=255, description="Apartment, suite, unit, etc.")
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=2, max_length=20)
    country: str = Field(default="USA", max_length=100)
    is_default: bool = Field(default=False, description="Set as default shipping address")
    address_type: AddressType = Field(default=AddressType.HOME, description="HOME, WORK, or OTHER")


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    phone_number: Optional[str] = Field(default=None, min_length=5, max_length=50)
    address_line1: Optional[str] = Field(default=None, min_length=3, max_length=255)
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_default: Optional[bool] = None
    address_type: Optional[AddressType] = None


class AddressOut(AddressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
