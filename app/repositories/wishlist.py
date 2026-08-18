from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.wishlist import WishlistItem


class WishlistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_item(self, user_id: int, product_id: int) -> Optional[WishlistItem]:
        """Fetch wishlist item for a specific user and product."""
        stmt = select(WishlistItem).where(
            WishlistItem.user_id == user_id,
            WishlistItem.product_id == product_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def add_item(self, user_id: int, product_id: int) -> WishlistItem:
        """Add product to user's wishlist."""
        existing = self.get_item(user_id, product_id)
        if existing:
            return existing

        item = WishlistItem(user_id=user_id, product_id=product_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_item(self, user_id: int, product_id: int) -> bool:
        """Remove product from user's wishlist."""
        item = self.get_item(user_id, product_id)
        if item:
            self.db.delete(item)
            self.db.commit()
            return True
        return False

    def list_by_user(self, user_id: int, skip: int = 0, limit: int = 50) -> List[WishlistItem]:
        """List wishlist items with product and images eager-loaded."""
        stmt = (
            select(WishlistItem)
            .options(
                joinedload(WishlistItem.product).joinedload(Product.images),
            )
            .where(WishlistItem.user_id == user_id)
            .order_by(WishlistItem.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def count_by_user(self, user_id: int) -> int:
        """Count total items in user's wishlist."""
        stmt = select(func.count(WishlistItem.id)).where(WishlistItem.user_id == user_id)
        return self.db.execute(stmt).scalar() or 0

    def is_in_wishlist(self, user_id: int, product_id: int) -> bool:
        """Check if product exists in user's wishlist."""
        return self.get_item(user_id, product_id) is not None
