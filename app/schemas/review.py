from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5, description="Star rating from 1 to 5")
    title: Optional[str] = Field(default=None, max_length=150, description="Review headline")
    comment: Optional[str] = Field(default=None, description="Detailed review text")


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    title: Optional[str] = None
    comment: Optional[str] = None


class ReviewReplyCreate(BaseModel):
    reply: str = Field(min_length=1, max_length=2000, description="Vendor's official response text")


class ReviewOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    product_id: int
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    is_verified_purchase: bool
    vendor_reply: Optional[str] = None
    vendor_reply_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductReviewSummary(BaseModel):
    average_rating: float
    total_reviews: int
    rating_breakdown: Dict[int, int]
    reviews: List[ReviewOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
