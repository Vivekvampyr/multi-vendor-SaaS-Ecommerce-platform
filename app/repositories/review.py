from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem, OrderStatus
from app.models.review import Review
from app.schemas.review import ReviewCreate


class ReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, review_id: int) -> Optional[Review]:
        """Fetch review by ID."""
        stmt = (
            select(Review)
            .options(joinedload(Review.user))
            .where(Review.id == review_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_and_product(self, user_id: int, product_id: int) -> Optional[Review]:
        """Fetch user's review for a specific product."""
        stmt = select(Review).where(Review.user_id == user_id, Review.product_id == product_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def check_has_purchased(self, user_id: int, product_id: int) -> bool:
        """Check if user has purchased this product in a completed or paid order."""
        stmt = (
            select(OrderItem.id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.customer_id == user_id,
                OrderItem.product_id == product_id,
                Order.status.in_([
                    OrderStatus.PAID,
                    OrderStatus.PROCESSING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED,
                ]),
            )
        )
        return self.db.execute(stmt).first() is not None

    def create(
        self,
        user_id: int,
        product_id: int,
        review_in: ReviewCreate,
        is_verified: bool = False,
    ) -> Review:
        """Create and persist a new review."""
        db_review = Review(
            user_id=user_id,
            product_id=product_id,
            rating=review_in.rating,
            title=review_in.title.strip() if review_in.title else None,
            comment=review_in.comment.strip() if review_in.comment else None,
            is_verified_purchase=is_verified,
        )
        self.db.add(db_review)
        self.db.commit()
        self.db.refresh(db_review)
        return self.get_by_id(db_review.id) or db_review

    def update(self, review: Review, update_data: dict) -> Review:
        """Update review fields."""
        for field, value in update_data.items():
            if hasattr(review, field) and value is not None:
                setattr(review, field, value)
        self.db.commit()
        self.db.refresh(review)
        return self.get_by_id(review.id) or review

    def delete(self, review: Review) -> bool:
        """Delete review."""
        self.db.delete(review)
        self.db.commit()
        return True

    def list_by_product(
        self,
        product_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Review]:
        """List reviews for a product."""
        stmt = (
            select(Review)
            .options(joinedload(Review.user))
            .where(Review.product_id == product_id)
            .order_by(Review.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_product(self, product_id: int) -> int:
        """Count reviews for a product."""
        stmt = select(func.count(Review.id)).where(Review.product_id == product_id)
        return self.db.execute(stmt).scalar() or 0

    def get_product_rating_stats(self, product_id: int) -> Tuple[float, int, Dict[int, int]]:
        """Compute average rating and count breakdown (1 to 5 stars) for a product."""
        avg_stmt = select(func.avg(Review.rating)).where(Review.product_id == product_id)
        avg_val = self.db.execute(avg_stmt).scalar() or 0.0
        avg_rating = round(float(avg_val), 1)

        total_stmt = select(func.count(Review.id)).where(Review.product_id == product_id)
        total_reviews = self.db.execute(total_stmt).scalar() or 0

        breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        group_stmt = (
            select(Review.rating, func.count(Review.id))
            .where(Review.product_id == product_id)
            .group_by(Review.rating)
        )
        for star, count in self.db.execute(group_stmt).all():
            if star in breakdown:
                breakdown[star] = count

        return avg_rating, total_reviews, breakdown
