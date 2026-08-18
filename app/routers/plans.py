from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.plan import PlanCreate, PlanOut, PlanUpdate
from app.services.plan import PlanService

router = APIRouter(prefix="/plans", tags=["SaaS Plans"])


@router.get(
    "",
    response_model=APIResponse[List[PlanOut]],
    status_code=status.HTTP_200_OK,
    summary="List available SaaS Plans",
    description="Retrieve list of SaaS plans. Defaults to active plans.",
)
def list_plans(
    only_active: bool = Query(default=True, description="Filter only active plans"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> APIResponse[List[PlanOut]]:
    plan_service = PlanService(db)
    plans, total = plan_service.list_plans(only_active=only_active, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(plans)} plans (total: {total})",
        data=[PlanOut.model_validate(p) for p in plans],
    )


@router.get(
    "/{plan_id}",
    response_model=APIResponse[PlanOut],
    status_code=status.HTTP_200_OK,
    summary="Get SaaS Plan details",
)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
) -> APIResponse[PlanOut]:
    plan_service = PlanService(db)
    plan = plan_service.get_plan_by_id(plan_id)
    return APIResponse(
        success=True,
        message="Plan details retrieved",
        data=PlanOut.model_validate(plan),
    )


@router.post(
    "",
    response_model=APIResponse[PlanOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new SaaS Plan (Admin only)",
    description="Create a new vendor plan with listing limits and platform commission percentage.",
)
def create_plan(
    plan_in: PlanCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[PlanOut]:
    plan_service = PlanService(db)
    created_plan = plan_service.create_plan(plan_in)
    return APIResponse(
        success=True,
        message="SaaS Plan created successfully",
        data=PlanOut.model_validate(created_plan),
    )


@router.put(
    "/{plan_id}",
    response_model=APIResponse[PlanOut],
    status_code=status.HTTP_200_OK,
    summary="Update a SaaS Plan (Admin only)",
)
def update_plan(
    plan_id: int,
    update_in: PlanUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[PlanOut]:
    plan_service = PlanService(db)
    updated_plan = plan_service.update_plan(plan_id, update_in)
    return APIResponse(
        success=True,
        message="SaaS Plan updated successfully",
        data=PlanOut.model_validate(updated_plan),
    )


@router.delete(
    "/{plan_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a SaaS Plan (Admin only)",
)
def delete_plan(
    plan_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MessageResponse:
    plan_service = PlanService(db)
    plan_service.delete_plan(plan_id)
    return MessageResponse(
        success=True,
        message="SaaS Plan deleted successfully",
    )
