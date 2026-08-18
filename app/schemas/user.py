from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr = Field(description="User's unique email address")
    full_name: str = Field(min_length=2, max_length=255, description="Full name of the user")
    phone_number: Optional[str] = Field(default=None, max_length=50, description="Optional phone number")


class UserCreate(UserBase):
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Plain text password (minimum 8 characters)",
    )
    role: UserRole = Field(
        default=UserRole.CUSTOMER,
        description="Role assigned to the user (CUSTOMER or VENDOR upon registration)",
    )


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    phone_number: Optional[str] = Field(default=None, max_length=50)


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(min_length=1, description="Current password")
    new_password: str = Field(min_length=8, max_length=128, description="New password")


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    phone_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
