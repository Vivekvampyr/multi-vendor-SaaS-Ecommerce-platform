from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper."""
    success: bool = Field(default=True, description="Indicates request success")
    message: Optional[str] = Field(default=None, description="Human-readable status message")
    data: Optional[T] = Field(default=None, description="Payload data")

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error explanation")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context or validation details")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Always False for error responses")
    error: ErrorDetail


class MessageResponse(BaseModel):
    success: bool = True
    message: str


class DatabaseHealth(BaseModel):
    connected: bool
    message: str


class HealthData(BaseModel):
    app_name: str
    version: str
    environment: str
    status: str
    database: DatabaseHealth


class HealthResponse(APIResponse[HealthData]):
    pass
