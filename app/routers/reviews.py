from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_customer
from app.models.user import User
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.review import (
    ProductReviewSummary,
    ReviewCreate,
    ReviewOut,
    ReviewReplyCreate,
    ReviewUpdate,
)
from app.services.review import ReviewService

router = APIRouter(tags=["Product Reviews & Ratings"])


@router.get(
    "/products/{product_id}/reviews",
    response_model=APIResponse[ProductReviewSummary],
    status_code=status.HTTP_200_OK,
    summary="Get product reviews & star rating summary (Public)",
)
def get_product_reviews(
    product_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> APIResponse[ProductReviewSummary]:
    review_service = ReviewService(db)
    summary = review_service.get_product_reviews(product_id=product_id, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message="Product reviews retrieved",
        data=summary,
    )


@router.post(
    "/products/{product_id}/reviews",
    response_model=APIResponse[ReviewOut],
    status_code=status.HTTP_201_CREATED,
    summary="Submit a product review & rating (Customer only)",
)
def create_review(
    product_id: int,
    review_in: ReviewCreate,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> APIResponse[ReviewOut]:
    review_service = ReviewService(db)
    created = review_service.create_review(user=customer, product_id=product_id, review_in=review_in)
    return APIResponse(
        success=True,
        message="Review submitted successfully",
        data=created,
    )


@router.put(
    "/reviews/{review_id}",
    response_model=APIResponse[ReviewOut],
    status_code=status.HTTP_200_OK,
    summary="Update review (Customer owner or Admin)",
)
def update_review(
    review_id: int,
    update_in: ReviewUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[ReviewOut]:
    review_service = ReviewService(db)
    updated = review_service.update_review(user=current_user, review_id=review_id, update_in=update_in)
    return APIResponse(
        success=True,
        message="Review updated successfully",
        data=updated,
    )


@router.delete(
    "/reviews/{review_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete review (Customer owner or Admin)",
)
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    review_service = ReviewService(db)
    review_service.delete_review(user=current_user, review_id=review_id)
    return MessageResponse(
        success=True,
        message="Review deleted successfully",
    )


@router.post(
    "/reviews/{review_id}/reply",
    response_model=APIResponse[ReviewOut],
    status_code=status.HTTP_200_OK,
    summary="Reply to customer review (Product Vendor or Admin)",
)
def reply_to_review(
    review_id: int,
    reply_in: ReviewReplyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[ReviewOut]:
    review_service = ReviewService(db)
    updated = review_service.reply_to_review(
        user=current_user,
        review_id=review_id,
        reply_text=reply_in.reply,
    )
    return APIResponse(
        success=True,
        message="Merchant reply posted successfully",
        data=updated,
    )


@router.delete(
    "/reviews/{review_id}/reply",
    response_model=APIResponse[ReviewOut],
    status_code=status.HTTP_200_OK,
    summary="Delete merchant reply (Product Vendor or Admin)",
)
def delete_vendor_reply(
    review_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[ReviewOut]:
    review_service = ReviewService(db)
    updated = review_service.delete_vendor_reply(user=current_user, review_id=review_id)
    return APIResponse(
        success=True,
        message="Merchant reply removed",
        data=updated,
    )

