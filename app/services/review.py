import logging
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.models.review import Review
from app.models.user import User, UserRole
from app.repositories.product import ProductRepository
from app.repositories.review import ReviewRepository
from app.schemas.review import (
    ProductReviewSummary,
    ReviewCreate,
    ReviewOut,
    ReviewUpdate,
)

logger = logging.getLogger(__name__)


class ReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.review_repo = ReviewRepository(db)
        self.prod_repo = ProductRepository(db)

    def _map_to_out(self, review: Review) -> ReviewOut:
        user_name = review.user.full_name if review.user else "Anonymous"
        return ReviewOut(
            id=review.id,
            user_id=review.user_id,
            user_name=user_name,
            product_id=review.product_id,
            rating=review.rating,
            title=review.title,
            comment=review.comment,
            is_verified_purchase=review.is_verified_purchase,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )

    def create_review(self, user: User, product_id: int, review_in: ReviewCreate) -> ReviewOut:
        """Create a product review with automated verified purchase checking."""
        prod = self.prod_repo.get_by_id(product_id)
        if not prod or not prod.is_approved:
            raise NotFoundException(message=f"Product with ID {product_id} not found")

        existing = self.review_repo.get_by_user_and_product(user_id=user.id, product_id=product_id)
        if existing:
            raise ConflictException(
                message="You have already reviewed this product. Please update your existing review.",
                details={"review_id": existing.id},
            )

        # Check if customer has verified purchase history for this product
        is_verified = self.review_repo.check_has_purchased(user_id=user.id, product_id=product_id)
        review = self.review_repo.create(
            user_id=user.id,
            product_id=product_id,
            review_in=review_in,
            is_verified=is_verified,
        )
        logger.info(
            "Created review ID %d for product ID %d by User ID %d (Verified Purchase: %s)",
            review.id,
            product_id,
            user.id,
            str(is_verified),
        )
        return self._map_to_out(review)

    def update_review(self, user: User, review_id: int, update_in: ReviewUpdate) -> ReviewOut:
        """Update existing review."""
        review = self.review_repo.get_by_id(review_id)
        if not review:
            raise NotFoundException(message=f"Review with ID {review_id} not found")

        if user.role != UserRole.ADMIN and review.user_id != user.id:
            raise ForbiddenException(message="You do not have permission to modify this review")

        update_data = update_in.model_dump(exclude_unset=True)
        updated = self.review_repo.update(review, update_data)
        return self._map_to_out(updated)

    def delete_review(self, user: User, review_id: int) -> bool:
        """Delete review."""
        review = self.review_repo.get_by_id(review_id)
        if not review:
            raise NotFoundException(message=f"Review with ID {review_id} not found")

        if user.role != UserRole.ADMIN and review.user_id != user.id:
            raise ForbiddenException(message="You do not have permission to delete this review")

        return self.review_repo.delete(review)

    def get_product_reviews(
        self,
        product_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> ProductReviewSummary:
        """Get product reviews and aggregated rating statistics."""
        prod = self.prod_repo.get_by_id(product_id)
        if not prod:
            raise NotFoundException(message=f"Product with ID {product_id} not found")

        reviews = self.review_repo.list_by_product(product_id=product_id, skip=skip, limit=limit)
        avg_rating, total_reviews, breakdown = self.review_repo.get_product_rating_stats(product_id=product_id)

        return ProductReviewSummary(
            average_rating=avg_rating,
            total_reviews=total_reviews,
            rating_breakdown=breakdown,
            reviews=[self._map_to_out(r) for r in reviews],
        )
