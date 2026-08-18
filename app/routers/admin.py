from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.subscription import SubscriptionStatus
from app.models.user import User
from app.schemas.admin import AdminDashboardStats
from app.schemas.common import APIResponse
from app.schemas.subscription import (
    VendorPlanAssignRequest,
    VendorSubscriptionOut,
)
from app.services.admin import AdminService
from app.services.subscription import SubscriptionService

router = APIRouter(prefix="/admin", tags=["Admin & Analytics"])


@router.get(
    "/dashboard",
    response_model=APIResponse[AdminDashboardStats],
    status_code=status.HTTP_200_OK,
    summary="Admin Dashboard Analytics & Platform Metrics",
)
def get_dashboard_stats(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[AdminDashboardStats]:
    admin_service = AdminService(db)
    stats = admin_service.get_dashboard_stats()
    return APIResponse(
        success=True,
        message="Admin metrics loaded successfully",
        data=stats,
    )


@router.get(
    "/subscriptions",
    response_model=APIResponse[List[VendorSubscriptionOut]],
    status_code=status.HTTP_200_OK,
    summary="List all vendor subscriptions (Admin only)",
)
def list_vendor_subscriptions(
    status_filter: Optional[SubscriptionStatus] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[List[VendorSubscriptionOut]]:
    sub_service = SubscriptionService(db)
    subs, total = sub_service.list_subscriptions(skip=skip, limit=limit, status=status_filter)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(subs)} subscriptions (total: {total})",
        data=[VendorSubscriptionOut.model_validate(s) for s in subs],
    )


@router.post(
    "/vendors/{vendor_id}/assign-plan",
    response_model=APIResponse[VendorSubscriptionOut],
    status_code=status.HTTP_200_OK,
    summary="Manually assign or override vendor plan (Admin only)",
)
def assign_vendor_plan(
    vendor_id: int,
    request: VendorPlanAssignRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[VendorSubscriptionOut]:
    sub_service = SubscriptionService(db)
    subscription = sub_service.assign_plan(
        vendor_id=vendor_id,
        plan_id=request.plan_id,
        status=request.status,
        duration_days=request.duration_days or 30,
        admin_override=True,
    )
    return APIResponse(
        success=True,
        message="Vendor plan assigned successfully",
        data=VendorSubscriptionOut.model_validate(subscription),
    )
