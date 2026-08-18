from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Fetch category by primary key ID."""
        stmt = select(Category).where(Category.id == category_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Optional[Category]:
        """Fetch category by unique slug."""
        stmt = select(Category).where(func.lower(Category.slug) == slug.lower().strip())
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_name(self, name: str) -> Optional[Category]:
        """Fetch category by name."""
        stmt = select(Category).where(func.lower(Category.name) == name.lower().strip())
        return self.db.execute(stmt).scalar_one_or_none()

    def exists_by_name_or_slug(
        self,
        name: str,
        slug: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Check if category name or slug is already in use."""
        stmt = select(Category.id).where(
            or_(
                func.lower(Category.name) == name.lower().strip(),
                func.lower(Category.slug) == slug.lower().strip(),
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def create(self, category_in: CategoryCreate) -> Category:
        """Create and persist a new category."""
        slug = category_in.slug.lower().strip() if category_in.slug else category_in.name.lower().strip().replace(" ", "-")
        db_category = Category(
            name=category_in.name.strip(),
            slug=slug,
            description=category_in.description.strip() if category_in.description else None,
            parent_id=category_in.parent_id,
            is_active=category_in.is_active,
        )
        self.db.add(db_category)
        self.db.commit()
        self.db.refresh(db_category)
        return db_category

    def update(self, category: Category, update_data: dict) -> Category:
        """Update existing category fields."""
        for field, value in update_data.items():
            if hasattr(category, field) and value is not None:
                if field == "slug" and isinstance(value, str):
                    value = value.lower().strip()
                setattr(category, field, value)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category: Category) -> bool:
        """Delete category from database."""
        self.db.delete(category)
        self.db.commit()
        return True

    def list(
        self,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Category]:
        """List categories with optional active filter and pagination."""
        stmt = select(Category)
        if only_active:
            stmt = stmt.where(Category.is_active.is_(True))
        stmt = stmt.offset(skip).limit(limit).order_by(Category.name.asc())
        return list(self.db.execute(stmt).scalars().all())

    def count(self, only_active: bool = True) -> int:
        """Count total categories."""
        stmt = select(func.count(Category.id))
        if only_active:
            stmt = stmt.where(Category.is_active.is_(True))
        return self.db.execute(stmt).scalar() or 0
