"""
Pydantic validation and serialization schemas.
"""

from app.schemas.admin import AdminDashboardStats
from app.schemas.auth import (
    TokenPayload,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserLogin,
)
from app.schemas.category import (
    CategoryBase,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
)
from app.schemas.common import (
    APIResponse,
    ErrorDetail,
    ErrorResponse,
    HealthData,
    HealthResponse,
    MessageResponse,
)
from app.schemas.plan import PlanBase, PlanCreate, PlanOut, PlanUpdate
from app.schemas.product import (
    ProductBase,
    ProductCreate,
    ProductImageOut,
    ProductOut,
    ProductUpdate,
)
from app.schemas.subscription import (
    VendorPlanAssignRequest,
    VendorPlanLimitsOut,
    VendorPlanSelectRequest,
    VendorSubscriptionBase,
    VendorSubscriptionOut,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserOut,
    UserPasswordUpdate,
    UserUpdate,
)
from app.schemas.vendor import (
    VendorDashboardOverview,
    VendorProfileBase,
    VendorProfileCreate,
    VendorProfileOut,
    VendorProfileUpdate,
    VendorStatusUpdate,
)

__all__ = [
    "APIResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthData",
    "HealthResponse",
    "MessageResponse",
    "UserBase",
    "UserCreate",
    "UserOut",
    "UserUpdate",
    "UserPasswordUpdate",
    "UserLogin",
    "TokenResponse",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "TokenPayload",
    "PlanBase",
    "PlanCreate",
    "PlanOut",
    "PlanUpdate",
    "VendorSubscriptionBase",
    "VendorSubscriptionOut",
    "VendorPlanSelectRequest",
    "VendorPlanAssignRequest",
    "VendorPlanLimitsOut",
    "AdminDashboardStats",
    "VendorProfileBase",
    "VendorProfileCreate",
    "VendorProfileUpdate",
    "VendorProfileOut",
    "VendorStatusUpdate",
    "VendorDashboardOverview",
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryOut",
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductOut",
    "ProductImageOut",
]
