from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_optional_user
from app.models.user import User
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.coupon import (
    CouponCreate,
    CouponOut,
    CouponUpdate,
    CouponValidateRequest,
    CouponValidationResult,
)
from app.services.coupon import CouponService

router = APIRouter(prefix="/coupons", tags=["Coupons & Discounts"])


@router.post(
    "",
    response_model=APIResponse[CouponOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a coupon (Admin: platform-wide or vendor; Vendor: own store)",
)
def create_coupon(
    coupon_in: CouponCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[CouponOut]:
    coupon_service = CouponService(db)
    created = coupon_service.create_coupon(user=current_user, coupon_in=coupon_in)
    return APIResponse(
        success=True,
        message="Coupon created successfully",
        data=CouponOut.model_validate(created),
    )


@router.get(
    "",
    response_model=APIResponse[List[CouponOut]],
    status_code=status.HTTP_200_OK,
    summary="List coupons (Admin sees all; Vendor sees own store coupons)",
)
def list_coupons(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[CouponOut]]:
    coupon_service = CouponService(db)
    coupons, total = coupon_service.list_coupons(user=current_user, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(coupons)} coupons (total: {total})",
        data=[CouponOut.model_validate(c) for c in coupons],
    )


@router.get(
    "/{coupon_id}",
    response_model=APIResponse[CouponOut],
    status_code=status.HTTP_200_OK,
    summary="Get coupon details (Vendor owner or Admin)",
)
def get_coupon(
    coupon_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[CouponOut]:
    coupon_service = CouponService(db)
    coupon = coupon_service.get_coupon_by_id(user=current_user, coupon_id=coupon_id)
    return APIResponse(
        success=True,
        message="Coupon details retrieved",
        data=CouponOut.model_validate(coupon),
    )


@router.put(
    "/{coupon_id}",
    response_model=APIResponse[CouponOut],
    status_code=status.HTTP_200_OK,
    summary="Update coupon (Vendor owner or Admin)",
)
def update_coupon(
    coupon_id: int,
    update_in: CouponUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[CouponOut]:
    coupon_service = CouponService(db)
    updated = coupon_service.update_coupon(user=current_user, coupon_id=coupon_id, update_in=update_in)
    return APIResponse(
        success=True,
        message="Coupon updated successfully",
        data=CouponOut.model_validate(updated),
    )


@router.delete(
    "/{coupon_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete coupon (Vendor owner or Admin)",
)
def delete_coupon(
    coupon_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    coupon_service = CouponService(db)
    coupon_service.delete_coupon(user=current_user, coupon_id=coupon_id)
    return MessageResponse(
        success=True,
        message="Coupon deleted successfully",
    )


@router.post(
    "/validate",
    response_model=APIResponse[CouponValidationResult],
    status_code=status.HTTP_200_OK,
    summary="Validate coupon code and compute real-time cart discount (Public / Customer)",
)
def validate_coupon(
    request: CouponValidateRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> APIResponse[CouponValidationResult]:
    coupon_service = CouponService(db)
    result = coupon_service.validate_coupon(request=request, user=current_user)
    return APIResponse(
        success=result.valid,
        message=result.message,
        data=result,
    )
