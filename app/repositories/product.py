from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product, ProductStatus
from app.models.product_image import ProductImage
from app.schemas.product import ProductCreate


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Fetch product by ID with eager-loaded images and category."""
        stmt = (
            select(Product)
            .options(
                joinedload(Product.images),
                joinedload(Product.category),
                joinedload(Product.vendor),
            )
            .where(Product.id == product_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Optional[Product]:
        """Fetch product by unique slug."""
        stmt = (
            select(Product)
            .options(
                joinedload(Product.images),
                joinedload(Product.category),
                joinedload(Product.vendor),
            )
            .where(func.lower(Product.slug) == slug.lower().strip())
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_sku(self, sku: str) -> Optional[Product]:
        """Fetch product by SKU."""
        stmt = select(Product).where(func.lower(Product.sku) == sku.lower().strip())
        return self.db.execute(stmt).scalar_one_or_none()

    def exists_by_sku(self, sku: str, exclude_product_id: Optional[int] = None) -> bool:
        """Check if SKU already exists."""
        stmt = select(Product.id).where(func.lower(Product.sku) == sku.lower().strip())
        if exclude_product_id is not None:
            stmt = stmt.where(Product.id != exclude_product_id)
        return self.db.execute(stmt).first() is not None

    def exists_by_slug(self, slug: str, exclude_product_id: Optional[int] = None) -> bool:
        """Check if slug already exists."""
        stmt = select(Product.id).where(func.lower(Product.slug) == slug.lower().strip())
        if exclude_product_id is not None:
            stmt = stmt.where(Product.id != exclude_product_id)
        return self.db.execute(stmt).first() is not None

    def count_by_vendor(self, vendor_id: int) -> int:
        """Count total products created by a specific vendor."""
        stmt = select(func.count(Product.id)).where(Product.vendor_id == vendor_id)
        return self.db.execute(stmt).scalar() or 0

    def create(self, vendor_id: int, product_in: ProductCreate) -> Product:
        """Create and persist a new product."""
        slug = product_in.slug.lower().strip() if product_in.slug else product_in.name.lower().strip().replace(" ", "-")
        db_product = Product(
            vendor_id=vendor_id,
            category_id=product_in.category_id,
            name=product_in.name.strip(),
            slug=slug,
            sku=product_in.sku.strip().upper(),
            description=product_in.description,
            short_description=product_in.short_description,
            price=product_in.price,
            compare_at_price=product_in.compare_at_price,
            stock_quantity=product_in.stock_quantity,
            status=product_in.status,
            is_approved=True,
        )
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return self.get_by_id(db_product.id) or db_product

    def update(self, product: Product, update_data: dict) -> Product:
        """Update fields on an existing product."""
        for field, value in update_data.items():
            if hasattr(product, field) and value is not None:
                if field == "sku" and isinstance(value, str):
                    value = value.strip().upper()
                elif field == "slug" and isinstance(value, str):
                    value = value.lower().strip()
                setattr(product, field, value)
        self.db.commit()
        self.db.refresh(product)
        return self.get_by_id(product.id) or product

    def delete(self, product: Product) -> bool:
        """Delete product from database."""
        self.db.delete(product)
        self.db.commit()
        return True

    def list(
        self,
        category_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        status: Optional[ProductStatus] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Product]:
        """List products with filters and pagination."""
        stmt = (
            select(Product)
            .options(
                joinedload(Product.images),
                joinedload(Product.category),
            )
        )

        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if vendor_id is not None:
            stmt = stmt.where(Product.vendor_id == vendor_id)
        if status is not None:
            stmt = stmt.where(Product.status == status)
        if min_price is not None:
            stmt = stmt.where(Product.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Product.price <= max_price)
        if search:
            pattern = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Product.name).like(pattern),
                    func.lower(Product.description).like(pattern),
                    func.lower(Product.sku).like(pattern),
                )
            )

        stmt = stmt.offset(skip).limit(limit).order_by(Product.id.desc())
        return list(self.db.execute(stmt).unique().scalars().all())

    def count(
        self,
        category_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        status: Optional[ProductStatus] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count total products matching filter parameters."""
        stmt = select(func.count(Product.id))
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if vendor_id is not None:
            stmt = stmt.where(Product.vendor_id == vendor_id)
        if status is not None:
            stmt = stmt.where(Product.status == status)
        if min_price is not None:
            stmt = stmt.where(Product.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Product.price <= max_price)
        if search:
            pattern = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Product.name).like(pattern),
                    func.lower(Product.description).like(pattern),
                    func.lower(Product.sku).like(pattern),
                )
            )
        return self.db.execute(stmt).scalar() or 0

    def get_suggested_products(
        self,
        product_id: int,
        category_id: Optional[int] = None,
        limit: int = 4,
    ) -> List[Product]:
        """
        Fetch product suggestions strictly from the same category:
        1. Must match the exact category_id.
        2. Must exclude current product_id.
        3. Must be PUBLISHED and approved.
        4. Ordered by stock availability and recency.
        """
        if category_id is None:
            return []

        stmt = (
            select(Product)
            .options(
                joinedload(Product.images),
                joinedload(Product.category),
                joinedload(Product.vendor),
            )
            .where(
                Product.category_id == category_id,
                Product.id != product_id,
                Product.status == ProductStatus.PUBLISHED,
                Product.is_approved.is_(True),
            )
            .order_by(Product.stock_quantity.desc(), Product.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())


class ProductImageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, image_id: int) -> Optional[ProductImage]:
        """Fetch image by ID."""
        stmt = select(ProductImage).where(ProductImage.id == image_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def add_image(
        self,
        product_id: int,
        image_url: str,
        is_primary: bool = False,
        display_order: int = 0,
        alt_text: Optional[str] = None,
    ) -> ProductImage:
        """Add image to product."""
        if is_primary:
            # Unset existing primary image if new one is marked primary
            self.unset_all_primary(product_id)

        db_image = ProductImage(
            product_id=product_id,
            image_url=image_url,
            is_primary=is_primary,
            display_order=display_order,
            alt_text=alt_text,
        )
        self.db.add(db_image)
        self.db.commit()
        self.db.refresh(db_image)
        return db_image

    def unset_all_primary(self, product_id: int) -> None:
        """Unset primary status for all images of a product."""
        stmt = select(ProductImage).where(
            ProductImage.product_id == product_id,
            ProductImage.is_primary.is_(True),
        )
        images = self.db.execute(stmt).scalars().all()
        for img in images:
            img.is_primary = False
        self.db.commit()

    def set_primary(self, product_id: int, image_id: int) -> Optional[ProductImage]:
        """Set a specific image as the primary image."""
        self.unset_all_primary(product_id)
        image = self.get_by_id(image_id)
        if image and image.product_id == product_id:
            image.is_primary = True
            self.db.commit()
            self.db.refresh(image)
            return image
        return None

    def delete_image(self, image: ProductImage) -> bool:
        """Delete image from database."""
        self.db.delete(image)
        self.db.commit()
        return True

    def get_images_by_product_id(self, product_id: int) -> List[ProductImage]:
        """Fetch all images for a product ordered by display_order."""
        stmt = (
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.display_order.asc(), ProductImage.id.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
