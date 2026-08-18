from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    check_resource_ownership,
    get_current_active_user,
    require_admin,
)
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.user import UserOut, UserPasswordUpdate, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
)
def get_my_profile(
    current_user: User = Depends(get_current_active_user),
) -> APIResponse[UserOut]:
    return APIResponse(
        success=True,
        message="User profile fetched",
        data=UserOut.model_validate(current_user),
    )


@router.put(
    "/me",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
)
def update_my_profile(
    update_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[UserOut]:
    user_service = UserService(db)
    updated_user = user_service.update_profile(current_user.id, update_in)
    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data=UserOut.model_validate(updated_user),
    )


@router.put(
    "/me/password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change account password",
)
def change_my_password(
    password_in: UserPasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    user_service = UserService(db)
    user_service.change_password(current_user.id, password_in)
    return MessageResponse(
        success=True,
        message="Password changed successfully",
    )


@router.get(
    "",
    response_model=APIResponse[List[UserOut]],
    status_code=status.HTTP_200_OK,
    summary="List users (Admin only)",
    description="Retrieve paginated list of users with optional role filtering.",
)
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    role: Optional[UserRole] = Query(default=None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[List[UserOut]]:
    user_service = UserService(db)
    users, total = user_service.list_users(skip=skip, limit=limit, role=role)
    return APIResponse(
        success=True,
        message=f"Fetched {len(users)} users (total: {total})",
        data=[UserOut.model_validate(u) for u in users],
    )


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_200_OK,
    summary="Get user by ID (Admin or Self)",
)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[UserOut]:
    check_resource_ownership(current_user, user_id, allow_admin=True)
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    return APIResponse(
        success=True,
        message="User details retrieved",
        data=UserOut.model_validate(user),
    )
