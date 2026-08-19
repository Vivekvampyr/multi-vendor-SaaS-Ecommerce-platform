from typing import List, Optional
from pydantic import BaseModel, Field


class AIDescriptionGenerateRequest(BaseModel):
    """
    Input schema for generating product descriptions via Gemini AI.
    """
    title: str = Field(..., min_length=2, max_length=250, description="Product title or brand name")
    category_name: Optional[str] = Field(default=None, max_length=100, description="Product category name")
    keywords: Optional[str] = Field(default=None, max_length=500, description="Key features, specs, or target audience")
    tone: Optional[str] = Field(
        default="professional",
        description="Tone of copy: 'professional', 'exciting', 'minimalist', 'technical'",
    )


class AIDescriptionGenerateResponse(BaseModel):
    """
    Output schema containing generated marketing descriptions and SEO tags.
    """
    short_description: str = Field(..., description="Concise 1-2 sentence summary for cards")
    description: str = Field(..., description="Rich detailed product description with features and specs")
    seo_tags: List[str] = Field(default_factory=list, description="Relevant SEO search keywords")
    model_used: str = Field(default="gemini-2.5-flash-lite", description="AI model version used for generation")
