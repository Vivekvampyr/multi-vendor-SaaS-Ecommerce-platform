import logging
from typing import List
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.product import ProductStatus
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.repositories.product import ProductRepository
from app.repositories.wishlist import WishlistRepository
from app.schemas.wishlist import WishlistItemOut

logger = logging.getLogger(__name__)


class WishlistService:
    def __init__(self, db: Session):
        self.db = db
        self.wishlist_repo = WishlistRepository(db)
        self.prod_repo = ProductRepository(db)

    def _map_to_out(self, item: WishlistItem) -> WishlistItemOut:
        prod = item.product
        primary_img = None
        if prod and prod.images:
            primary_img = next((img.image_url for img in prod.images if img.is_primary), prod.images[0].image_url)

        return WishlistItemOut(
            id=item.id,
            user_id=item.user_id,
            product_id=item.product_id,
            product_name=prod.name if prod else "Unknown",
            product_slug=prod.slug if prod else "",
            product_sku=prod.sku if prod else "",
            price=float(prod.price) if prod else 0.0,
            image_url=primary_img,
            in_stock=(prod is not None and prod.stock_quantity > 0 and prod.status == ProductStatus.PUBLISHED),
            created_at=item.created_at,
        )

    def add_to_wishlist(self, user: User, product_id: int) -> WishlistItemOut:
        """Add product to customer wishlist."""
        prod = self.prod_repo.get_by_id(product_id)
        if not prod or not prod.is_approved:
            raise NotFoundException(message=f"Product with ID {product_id} not found")

        item = self.wishlist_repo.add_item(user_id=user.id, product_id=product_id)
        return self._map_to_out(item)

    def remove_from_wishlist(self, user: User, product_id: int) -> bool:
        """Remove product from customer wishlist."""
        return self.wishlist_repo.remove_item(user_id=user.id, product_id=product_id)

    def list_wishlist(self, user: User, skip: int = 0, limit: int = 50) -> List[WishlistItemOut]:
        """List all products in customer wishlist."""
        items = self.wishlist_repo.list_by_user(user_id=user.id, skip=skip, limit=limit)
        return [self._map_to_out(item) for item in items]
