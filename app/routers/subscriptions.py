from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_vendor
from app.models.user import User
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.subscription import (
    VendorPlanLimitsOut,
    VendorPlanSelectRequest,
    VendorSubscriptionOut,
)
from app.services.subscription import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Vendor Subscriptions"])


@router.get(
    "/my-plan",
    response_model=APIResponse[VendorPlanLimitsOut],
    status_code=status.HTTP_200_OK,
    summary="Get vendor's active plan limits & commission (Vendor only)",
    description="Returns current vendor plan limits, maximum product count, and platform commission rate.",
)
def get_my_plan(
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[VendorPlanLimitsOut]:
    sub_service = SubscriptionService(db)
    limits = sub_service.get_vendor_plan_limits(vendor.id)
    return APIResponse(
        success=True,
        message="Active plan limits retrieved",
        data=VendorPlanLimitsOut(**limits),
    )


@router.post(
    "/select-plan",
    response_model=APIResponse[VendorSubscriptionOut],
    status_code=status.HTTP_200_OK,
    summary="Select or change SaaS Plan (Vendor only)",
    description="Allows an authenticated vendor to select or upgrade their SaaS subscription plan.",
)
def select_plan(
    request: VendorPlanSelectRequest,
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[VendorSubscriptionOut]:
    sub_service = SubscriptionService(db)
    subscription = sub_service.assign_plan(vendor_id=vendor.id, plan_id=request.plan_id)
    return APIResponse(
        success=True,
        message="SaaS Plan successfully selected",
        data=VendorSubscriptionOut.model_validate(subscription),
    )


@router.post(
    "/cancel",
    response_model=APIResponse[VendorSubscriptionOut],
    status_code=status.HTTP_200_OK,
    summary="Cancel active SaaS Plan (Vendor only)",
)
def cancel_my_subscription(
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[VendorSubscriptionOut]:
    sub_service = SubscriptionService(db)
    canceled = sub_service.cancel_subscription(vendor.id)
    return APIResponse(
        success=True,
        message="Subscription successfully canceled",
        data=VendorSubscriptionOut.model_validate(canceled),
    )
