from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_customer
from app.models.user import User
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.wishlist import WishlistItemAdd, WishlistItemOut, WishlistToggleOut
from app.services.wishlist import WishlistService

router = APIRouter(prefix="/wishlist", tags=["Customer Wishlist"])


@router.get(
    "",
    response_model=APIResponse[List[WishlistItemOut]],
    status_code=status.HTTP_200_OK,
    summary="Get customer wishlist (Customer only)",
)
def get_my_wishlist(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> APIResponse[List[WishlistItemOut]]:
    wishlist_service = WishlistService(db)
    items = wishlist_service.list_wishlist(user=customer, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} wishlist items",
        data=items,
    )


@router.post(
    "/toggle",
    response_model=APIResponse[WishlistToggleOut],
    status_code=status.HTTP_200_OK,
    summary="Toggle product in customer wishlist (Customer only)",
)
def toggle_wishlist(
    item_in: WishlistItemAdd,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> APIResponse[WishlistToggleOut]:
    wishlist_service = WishlistService(db)
    result = wishlist_service.toggle_wishlist(user=customer, product_id=item_in.product_id)
    return APIResponse(
        success=True,
        message=result["message"],
        data=WishlistToggleOut(in_wishlist=result["in_wishlist"], product_id=item_in.product_id),
    )


@router.post(
    "",
    response_model=APIResponse[WishlistItemOut],
    status_code=status.HTTP_201_CREATED,
    summary="Add product to wishlist (Customer only)",
)
def add_to_wishlist(
    item_in: WishlistItemAdd,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> APIResponse[WishlistItemOut]:
    wishlist_service = WishlistService(db)
    created = wishlist_service.add_to_wishlist(user=customer, product_id=item_in.product_id)
    return APIResponse(
        success=True,
        message="Product added to wishlist",
        data=created,
    )


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove product from wishlist (Customer only)",
)
def remove_from_wishlist(
    product_id: int,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> MessageResponse:
    wishlist_service = WishlistService(db)
    wishlist_service.remove_from_wishlist(user=customer, product_id=product_id)
    return MessageResponse(
        success=True,
        message="Product removed from wishlist",
    )
