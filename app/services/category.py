import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.models.category import Category
from app.repositories.category import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.plan import slugify

logger = logging.getLogger(__name__)


class CategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.cat_repo = CategoryRepository(db)

    def create_category(self, category_in: CategoryCreate) -> Category:
        """Create a new product category."""
        slug = category_in.slug or slugify(category_in.name)
        if self.cat_repo.exists_by_name_or_slug(category_in.name, slug):
            raise ConflictException(
                message=f"Category with name '{category_in.name}' or slug '{slug}' already exists",
                details={"name": category_in.name, "slug": slug},
            )

        if category_in.parent_id:
            parent = self.cat_repo.get_by_id(category_in.parent_id)
            if not parent:
                raise NotFoundException(
                    message=f"Parent category with ID {category_in.parent_id} does not exist",
                    details={"parent_id": category_in.parent_id},
                )

        category = self.cat_repo.create(category_in)
        logger.info("Created Category: ID=%d, Name='%s'", category.id, category.name)
        return category

    def get_category_by_id(self, category_id: int) -> Category:
        """Fetch category by ID or 404."""
        cat = self.cat_repo.get_by_id(category_id)
        if not cat:
            raise NotFoundException(
                message=f"Category with ID {category_id} not found",
                details={"category_id": category_id},
            )
        return cat

    def get_category_by_slug(self, slug: str) -> Category:
        """Fetch category by slug or 404."""
        cat = self.cat_repo.get_by_slug(slug)
        if not cat:
            raise NotFoundException(
                message=f"Category with slug '{slug}' not found",
                details={"slug": slug},
            )
        return cat

    def update_category(self, category_id: int, update_in: CategoryUpdate) -> Category:
        """Update category fields."""
        cat = self.get_category_by_id(category_id)
        update_data = update_in.model_dump(exclude_unset=True)

        if not update_data:
            return cat

        name = update_data.get("name", cat.name)
        slug = update_data.get("slug", cat.slug)
        if "name" in update_data and not update_in.slug:
            slug = slugify(name)
            update_data["slug"] = slug

        if self.cat_repo.exists_by_name_or_slug(name, slug, exclude_id=cat.id):
            raise ConflictException(
                message="Another category with this name or slug already exists",
                details={"name": name, "slug": slug},
            )

        if "parent_id" in update_data and update_data["parent_id"] is not None:
            if update_data["parent_id"] == cat.id:
                raise ConflictException(message="A category cannot be its own parent")
            parent = self.cat_repo.get_by_id(update_data["parent_id"])
            if not parent:
                raise NotFoundException(message="Parent category not found")

        return self.cat_repo.update(cat, update_data)

    def delete_category(self, category_id: int) -> bool:
        """Delete category."""
        cat = self.get_category_by_id(category_id)
        if cat.products:
            raise ConflictException(
                message="Cannot delete category containing products. Reassign or delete products first.",
                details={"product_count": len(cat.products)},
            )
        return self.cat_repo.delete(cat)

    def list_categories(
        self,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Category], int]:
        """List categories with total count."""
        cats = self.cat_repo.list(only_active=only_active, skip=skip, limit=limit)
        total = self.cat_repo.count(only_active=only_active)
        return cats, total
