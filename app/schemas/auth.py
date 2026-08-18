from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserOut


class UserLogin(BaseModel):
    email: EmailStr = Field(description="Registered email address")
    password: str = Field(description="Account password")


class TokenResponse(BaseModel):
    access_token: str = Field(description="Signed JWT access token")
    refresh_token: str = Field(description="Signed JWT refresh token")
    token_type: str = Field(default="bearer", description="Token authorization type")
    expires_in: int = Field(description="Access token lifespan in seconds")
    user: UserOut = Field(description="Authenticated user profile")


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(description="Valid JWT refresh token")


class TokenRefreshResponse(BaseModel):
    access_token: str = Field(description="New signed JWT access token")
    token_type: str = Field(default="bearer", description="Token authorization type")
    expires_in: int = Field(description="Access token lifespan in seconds")


class TokenPayload(BaseModel):
    sub: str
    role: Optional[str] = None
    type: str
    iat: int
    exp: int
