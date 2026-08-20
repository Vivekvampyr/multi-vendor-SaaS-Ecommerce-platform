from typing import List, Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_vendor
from app.models.product import ProductStatus
from app.models.user import User
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.product import (
    ProductCreate,
    ProductImageOut,
    ProductImageUrlCreate,
    ProductOut,
    ProductUpdate,
)
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["Product Management"])


@router.get(
    "",
    response_model=APIResponse[List[ProductOut]],
    status_code=status.HTTP_200_OK,
    summary="Browse and search published products (Public)",
)
def list_published_products(
    category_id: Optional[int] = Query(default=None, description="Filter by Category ID"),
    vendor_id: Optional[int] = Query(default=None, description="Filter by Vendor User ID"),
    min_price: Optional[float] = Query(default=None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(default=None, ge=0, description="Maximum price filter"),
    search: Optional[str] = Query(default=None, description="Search term across name, SKU, or description"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> APIResponse[List[ProductOut]]:
    prod_service = ProductService(db)
    prods, total = prod_service.list_products(
        category_id=category_id,
        vendor_id=vendor_id,
        status=ProductStatus.PUBLISHED,
        min_price=min_price,
        max_price=max_price,
        search=search,
        skip=skip,
        limit=limit,
    )
    return APIResponse(
        success=True,
        message=f"Retrieved {len(prods)} products (total: {total})",
        data=[ProductOut.model_validate(p) for p in prods],
    )


@router.get(
    "/vendor/my-products",
    response_model=APIResponse[List[ProductOut]],
    status_code=status.HTTP_200_OK,
    summary="List all vendor's products across all statuses (Vendor only)",
)
def list_vendor_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[List[ProductOut]]:
    prod_service = ProductService(db)
    prods, total = prod_service.list_my_products(vendor_id=vendor.id, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(prods)} products (total: {total})",
        data=[ProductOut.model_validate(p) for p in prods],
    )


@router.get(
    "/{product_id}",
    response_model=APIResponse[ProductOut],
    status_code=status.HTTP_200_OK,
    summary="Get product details",
)
def get_product_details(
    product_id: int,
    db: Session = Depends(get_db),
) -> APIResponse[ProductOut]:
    prod_service = ProductService(db)
    prod = prod_service.get_product_by_id(product_id)
    return APIResponse(
        success=True,
        message="Product details retrieved",
        data=ProductOut.model_validate(prod),
    )


@router.post(
    "",
    response_model=APIResponse[ProductOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product listing (Vendor only, Plan limits enforced)",
    description="Creates a product. Automatically enforces product listing limits defined by the vendor's active SaaS plan.",
)
def create_product(
    product_in: ProductCreate,
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[ProductOut]:
    prod_service = ProductService(db)
    created = prod_service.create_product(vendor_user=vendor, product_in=product_in)
    return APIResponse(
        success=True,
        message="Product created successfully",
        data=ProductOut.model_validate(created),
    )


@router.put(
    "/{product_id}",
    response_model=APIResponse[ProductOut],
    status_code=status.HTTP_200_OK,
    summary="Update product (Vendor owner or Admin)",
)
def update_product(
    product_id: int,
    update_in: ProductUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[ProductOut]:
    prod_service = ProductService(db)
    updated = prod_service.update_product(user=current_user, product_id=product_id, update_in=update_in)
    return APIResponse(
        success=True,
        message="Product updated successfully",
        data=ProductOut.model_validate(updated),
    )


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete product (Vendor owner or Admin)",
)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    prod_service = ProductService(db)
    prod_service.delete_product(user=current_user, product_id=product_id)
    return MessageResponse(
        success=True,
        message="Product and associated images deleted successfully",
    )


@router.post(
    "/{product_id}/images",
    response_model=APIResponse[List[ProductImageOut]],
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple images for product (Vendor owner or Admin)",
)
async def upload_product_images(
    product_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[ProductImageOut]]:
    prod_service = ProductService(db)
    images = await prod_service.upload_product_images(user=current_user, product_id=product_id, files=files)
    return APIResponse(
        success=True,
        message=f"Successfully uploaded {len(images)} images",
        data=[ProductImageOut.model_validate(img) for img in images],
    )


@router.post(
    "/{product_id}/images/url",
    response_model=APIResponse[ProductImageOut],
    status_code=status.HTTP_201_CREATED,
    summary="Add an image URL to product (Vendor owner or Admin)",
)
def add_product_image_url(
    product_id: int,
    image_in: ProductImageUrlCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[ProductImageOut]:
    prod_service = ProductService(db)
    img = prod_service.add_image_url(
        user=current_user,
        product_id=product_id,
        image_url=image_in.image_url,
        is_primary=image_in.is_primary,
        alt_text=image_in.alt_text,
    )
    return APIResponse(
        success=True,
        message="Image URL added successfully",
        data=ProductImageOut.model_validate(img),
    )


@router.put(
    "/{product_id}/images/{image_id}/primary",
    response_model=APIResponse[ProductImageOut],
    status_code=status.HTTP_200_OK,
    summary="Set primary display image for product (Vendor owner or Admin)",
)
def set_primary_image(
    product_id: int,
    image_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[ProductImageOut]:
    prod_service = ProductService(db)
    img = prod_service.set_primary_image(user=current_user, product_id=product_id, image_id=image_id)
    return APIResponse(
        success=True,
        message="Primary image set successfully",
        data=ProductImageOut.model_validate(img),
    )


@router.delete(
    "/{product_id}/images/{image_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete product image (Vendor owner or Admin)",
)
def delete_product_image(
    product_id: int,
    image_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    prod_service = ProductService(db)
    prod_service.delete_product_image(user=current_user, product_id=product_id, image_id=image_id)
    return MessageResponse(
        success=True,
        message="Product image deleted successfully",
    )
