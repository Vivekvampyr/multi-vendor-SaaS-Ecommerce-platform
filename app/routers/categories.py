from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import APIResponse, MessageResponse
from app.services.category import CategoryService

router = APIRouter(prefix="/categories", tags=["Product Categories"])


@router.get(
    "",
    response_model=APIResponse[List[CategoryOut]],
    status_code=status.HTTP_200_OK,
    summary="List product categories (Public)",
)
def list_categories(
    only_active: bool = Query(default=True, description="Filter only active categories"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> APIResponse[List[CategoryOut]]:
    cat_service = CategoryService(db)
    categories, total = cat_service.list_categories(only_active=only_active, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(categories)} categories (total: {total})",
        data=[CategoryOut.model_validate(c) for c in categories],
    )


@router.get(
    "/{category_id}",
    response_model=APIResponse[CategoryOut],
    status_code=status.HTTP_200_OK,
    summary="Get category details",
)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
) -> APIResponse[CategoryOut]:
    cat_service = CategoryService(db)
    category = cat_service.get_category_by_id(category_id)
    return APIResponse(
        success=True,
        message="Category details retrieved",
        data=CategoryOut.model_validate(category),
    )


@router.post(
    "",
    response_model=APIResponse[CategoryOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product category (Admin only)",
)
def create_category(
    category_in: CategoryCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[CategoryOut]:
    cat_service = CategoryService(db)
    created = cat_service.create_category(category_in)
    return APIResponse(
        success=True,
        message="Category created successfully",
        data=CategoryOut.model_validate(created),
    )


@router.put(
    "/{category_id}",
    response_model=APIResponse[CategoryOut],
    status_code=status.HTTP_200_OK,
    summary="Update category (Admin only)",
)
def update_category(
    category_id: int,
    update_in: CategoryUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[CategoryOut]:
    cat_service = CategoryService(db)
    updated = cat_service.update_category(category_id, update_in)
    return APIResponse(
        success=True,
        message="Category updated successfully",
        data=CategoryOut.model_validate(updated),
    )


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete category (Admin only)",
)
def delete_category(
    category_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MessageResponse:
    cat_service = CategoryService(db)
    cat_service.delete_category(category_id)
    return MessageResponse(
        success=True,
        message="Category deleted successfully",
    )
