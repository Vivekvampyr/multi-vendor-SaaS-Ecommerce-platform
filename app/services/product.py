import logging
from typing import List, Optional, Tuple
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.models.product import Product, ProductStatus
from app.models.product_image import ProductImage
from app.models.subscription import SubscriptionStatus
from app.models.user import User, UserRole
from app.models.vendor import VendorStatus
from app.repositories.category import CategoryRepository
from app.repositories.product import ProductImageRepository, ProductRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.vendor import VendorRepository
from app.schemas.plan import slugify
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.uploads import delete_product_image_file, save_product_image_file

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self, db: Session):
        self.db = db
        self.prod_repo = ProductRepository(db)
        self.image_repo = ProductImageRepository(db)
        self.cat_repo = CategoryRepository(db)
        self.sub_repo = SubscriptionRepository(db)
        self.vendor_repo = VendorRepository(db)

    def create_product(self, vendor_user: User, product_in: ProductCreate) -> Product:
        """
        Creates a new product for an approved vendor.
        Strictly enforces SaaS Plan listing limits (e.g. Silver ≤ 10, Gold ≤ 20).
        """
        if vendor_user.role != UserRole.VENDOR:
            raise ForbiddenException(
                message="Only accounts with role VENDOR can list products",
                details={"user_role": vendor_user.role.value},
            )

        # 1. Verify Vendor Store Status
        vendor_profile = self.vendor_repo.get_by_user_id(vendor_user.id)
        if not vendor_profile or vendor_profile.status != VendorStatus.APPROVED:
            current_status = vendor_profile.status.value if vendor_profile else "NOT_CONFIGURED"
            raise ForbiddenException(
                message="Your vendor store must be approved by an administrator before you can list products.",
                details={"vendor_status": current_status},
            )

        # 2. Verify Active SaaS Subscription & Enforce Plan Product Limit
        sub = self.sub_repo.get_by_vendor_id(vendor_user.id)
        if not sub or sub.status != SubscriptionStatus.ACTIVE or not sub.plan:
            raise ForbiddenException(
                message="An active SaaS subscription is required to list products. Please subscribe to a plan.",
                details={"subscription_status": sub.status.value if sub else "NONE"},
            )

        plan = sub.plan
        current_product_count = self.prod_repo.count_by_vendor(vendor_user.id)
        if current_product_count >= plan.max_products:
            raise ForbiddenException(
                message=(
                    f"Product listing limit reached! Your active '{plan.name}' plan permits a maximum "
                    f"of {plan.max_products} products (currently: {current_product_count}). "
                    f"Please upgrade your SaaS plan to list more products."
                ),
                details={
                    "plan_name": plan.name,
                    "max_products": plan.max_products,
                    "current_products": current_product_count,
                },
            )

        # 3. Verify Category
        category = self.cat_repo.get_by_id(product_in.category_id)
        if not category or not category.is_active:
            raise BadRequestException(
                message=f"Category with ID {product_in.category_id} not found or inactive",
                details={"category_id": product_in.category_id},
            )

        # 4. Verify SKU Uniqueness
        sku = product_in.sku.strip().upper()
        if self.prod_repo.exists_by_sku(sku):
            raise ConflictException(
                message=f"Product with SKU '{sku}' already exists",
                details={"sku": sku},
            )

        # 5. Generate and Verify Slug Uniqueness
        base_slug = product_in.slug or slugify(product_in.name)
        slug = base_slug
        counter = 1
        while self.prod_repo.exists_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        product_in_dict = product_in.model_dump()
        product_in_dict["slug"] = slug
        product_in_dict["sku"] = sku

        created_prod = self.prod_repo.create(vendor_id=vendor_user.id, product_in=ProductCreate(**product_in_dict))
        logger.info(
            "Created product ID %d ('%s') for vendor ID %d. Total products: %d/%d",
            created_prod.id,
            created_prod.name,
            vendor_user.id,
            current_product_count + 1,
            plan.max_products,
        )
        return created_prod

    def get_product_by_id(self, product_id: int, user: Optional[User] = None) -> Product:
        """Fetch product by ID with ownership access rules."""
        prod = self.prod_repo.get_by_id(product_id)
        if not prod:
            raise NotFoundException(
                message=f"Product with ID {product_id} not found",
                details={"product_id": product_id},
            )

        # If user is not admin or the owner vendor, only published products are accessible
        if user is None or (user.role != UserRole.ADMIN and user.id != prod.vendor_id):
            if prod.status != ProductStatus.PUBLISHED or not prod.is_approved:
                raise NotFoundException(message="Product not found or unavailable")

        return prod

    def get_product_by_slug(self, slug: str) -> Product:
        """Fetch published product by slug for public storefront."""
        prod = self.prod_repo.get_by_slug(slug)
        if not prod or prod.status != ProductStatus.PUBLISHED or not prod.is_approved:
            raise NotFoundException(
                message=f"Product '{slug}' not found or unavailable",
                details={"slug": slug},
            )
        return prod

    def update_product(
        self,
        user: User,
        product_id: int,
        update_in: ProductUpdate,
    ) -> Product:
        """Update product ensuring vendor ownership or admin privileges."""
        prod = self.prod_repo.get_by_id(product_id)
        if not prod:
            raise NotFoundException(message=f"Product with ID {product_id} not found")

        if user.role != UserRole.ADMIN and prod.vendor_id != user.id:
            raise ForbiddenException(
                message="You do not have permission to modify this product",
                details={"user_id": user.id, "vendor_id": prod.vendor_id},
            )

        update_data = update_in.model_dump(exclude_unset=True)
        if not update_data:
            return prod

        if "sku" in update_data:
            sku = update_data["sku"].strip().upper()
            if self.prod_repo.exists_by_sku(sku, exclude_product_id=prod.id):
                raise ConflictException(message=f"SKU '{sku}' is already in use by another product")
            update_data["sku"] = sku

        if "name" in update_data and not update_in.slug:
            slug = slugify(update_data["name"])
            if self.prod_repo.exists_by_slug(slug, exclude_product_id=prod.id):
                slug = f"{slug}-{prod.id}"
            update_data["slug"] = slug
        elif "slug" in update_data:
            slug = update_data["slug"].lower().strip()
            if self.prod_repo.exists_by_slug(slug, exclude_product_id=prod.id):
                raise ConflictException(message=f"Slug '{slug}' is already in use")
            update_data["slug"] = slug

        if "category_id" in update_data and update_data["category_id"] is not None:
            cat = self.cat_repo.get_by_id(update_data["category_id"])
            if not cat or not cat.is_active:
                raise BadRequestException(message="Selected category does not exist or is inactive")

        return self.prod_repo.update(prod, update_data)

    def delete_product(self, user: User, product_id: int) -> bool:
        """Delete product and all associated image files."""
        prod = self.prod_repo.get_by_id(product_id)
        if not prod:
            raise NotFoundException(message=f"Product with ID {product_id} not found")

        if user.role != UserRole.ADMIN and prod.vendor_id != user.id:
            raise ForbiddenException(message="You do not have permission to delete this product")

        # Delete physical images from disk
        for img in prod.images:
            delete_product_image_file(img.image_url)

        return self.prod_repo.delete(prod)

    async def upload_product_images(
        self,
        user: User,
        product_id: int,
        files: List[UploadFile],
    ) -> List[ProductImage]:
        """Upload and associate multiple images with a product."""
        prod = self.prod_repo.get_by_id(product_id)
        if not prod:
            raise NotFoundException(message=f"Product with ID {product_id} not found")

        if user.role != UserRole.ADMIN and prod.vendor_id != user.id:
            raise ForbiddenException(message="You do not have permission to upload images for this product")

        if not files:
            raise BadRequestException(message="No files provided for upload")

        existing_images = self.image_repo.get_images_by_product_id(product_id)
        has_primary = any(img.is_primary for img in existing_images)

        created_images: List[ProductImage] = []
        for i, file in enumerate(files):
            image_url = await save_product_image_file(file)
            is_primary = not has_primary and i == 0
            if is_primary:
                has_primary = True

            display_order = len(existing_images) + i
            img_record = self.image_repo.add_image(
                product_id=product_id,
                image_url=image_url,
                is_primary=is_primary,
                display_order=display_order,
                alt_text=prod.name,
            )
            created_images.append(img_record)

        logger.info("Uploaded %d images for product ID %d", len(created_images), product_id)
        return created_images

    def set_primary_image(self, user: User, product_id: int, image_id: int) -> ProductImage:
        """Set primary display image for a product."""
        prod = self.prod_repo.get_by_id(product_id)
        if not prod:
            raise NotFoundException(message=f"Product with ID {product_id} not found")

        if user.role != UserRole.ADMIN and prod.vendor_id != user.id:
            raise ForbiddenException(message="You do not have permission to modify this product")

        image = self.image_repo.get_by_id(image_id)
        if not image or image.product_id != product_id:
            raise NotFoundException(message="Image not found on this product")

        updated_image = self.image_repo.set_primary(product_id, image_id)
        if not updated_image:
            raise BadRequestException(message="Failed to set primary image")
        return updated_image

    def delete_product_image(self, user: User, product_id: int, image_id: int) -> bool:
        """Delete an individual product image and remove its file from disk."""
        prod = self.prod_repo.get_by_id(product_id)
        if not prod:
            raise NotFoundException(message=f"Product with ID {product_id} not found")

        if user.role != UserRole.ADMIN and prod.vendor_id != user.id:
            raise ForbiddenException(message="You do not have permission to modify this product")

        image = self.image_repo.get_by_id(image_id)
        if not image or image.product_id != product_id:
            raise NotFoundException(message="Image not found on this product")

        delete_product_image_file(image.image_url)
        self.image_repo.delete_image(image)

        # If deleted image was primary, assign first remaining image as primary
        remaining = self.image_repo.get_images_by_product_id(product_id)
        if remaining and not any(img.is_primary for img in remaining):
            self.image_repo.set_primary(product_id, remaining[0].id)

        return True

    def list_products(
        self,
        category_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        status: Optional[ProductStatus] = ProductStatus.PUBLISHED,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Product], int]:
        """List products with catalog filters."""
        prods = self.prod_repo.list(
            category_id=category_id,
            vendor_id=vendor_id,
            status=status,
            min_price=min_price,
            max_price=max_price,
            search=search,
            skip=skip,
            limit=limit,
        )
        total = self.prod_repo.count(
            category_id=category_id,
            vendor_id=vendor_id,
            status=status,
            min_price=min_price,
            max_price=max_price,
            search=search,
        )
        return prods, total

    def list_my_products(
        self,
        vendor_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Product], int]:
        """List all products for a vendor regardless of draft/published state."""
        prods = self.prod_repo.list(
            vendor_id=vendor_id,
            status=None,
            skip=skip,
            limit=limit,
        )
        total = self.prod_repo.count(vendor_id=vendor_id, status=None)
        return prods, total
