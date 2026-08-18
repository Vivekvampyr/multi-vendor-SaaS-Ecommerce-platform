from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.plan import slugify


class CategoryBase(BaseModel):
    name: str = Field(min_length=2, max_length=100, description="Category name (e.g., Electronics, Fashion)")
    slug: Optional[str] = Field(default=None, max_length=100, description="URL-friendly unique slug")
    description: Optional[str] = Field(default=None, description="Category summary")
    parent_id: Optional[int] = Field(default=None, description="Parent category ID for subcategories")
    is_active: bool = Field(default=True, description="Whether the category is visible")


class CategoryCreate(CategoryBase):
    @model_validator(mode="before")
    @classmethod
    def generate_slug_if_missing(cls, data):
        if isinstance(data, dict):
            name = data.get("name")
            slug = data.get("slug")
            if name and not slug:
                data["slug"] = slugify(name)
        return data


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryOut(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
