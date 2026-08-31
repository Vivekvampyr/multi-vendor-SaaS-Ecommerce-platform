from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin, require_vendor
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.vendor import (
    PublicVendorStoreOut,
    VendorDashboardOverview,
    VendorProfileCreate,
    VendorProfileOut,
    VendorProfileUpdate,
    VendorStatusUpdate,
)
from app.services.vendor import VendorService

router = APIRouter(prefix="/vendors", tags=["Vendor Management"])


@router.get(
    "",
    response_model=APIResponse[List[PublicVendorStoreOut]],
    status_code=status.HTTP_200_OK,
    summary="List all approved public vendor stores (Public)",
    description="Returns verified, approved and active vendor storefront profiles with product counts.",
)
def list_public_stores(
    search: Optional[str] = Query(default=None, description="Filter by store name, bio, city, or country"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> APIResponse[List[PublicVendorStoreOut]]:
    vendor_service = VendorService(db)
    stores, total = vendor_service.list_public_stores(search=search, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(stores)} public vendor stores (total: {total})",
        data=[PublicVendorStoreOut.model_validate(s) for s in stores],
    )


@router.get(
    "/dashboard",
    response_model=APIResponse[VendorDashboardOverview],
    status_code=status.HTTP_200_OK,
    summary="Vendor Dashboard Overview (Vendor only)",
    description="Returns store profile, active plan subscription, product listing limits, and live operational status.",
)
def get_vendor_dashboard(
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[VendorDashboardOverview]:
    vendor_service = VendorService(db)
    dashboard_data = vendor_service.get_vendor_dashboard(vendor)
    return APIResponse(
        success=True,
        message="Vendor dashboard overview retrieved",
        data=dashboard_data,
    )


@router.get(
    "/me",
    response_model=APIResponse[VendorProfileOut],
    status_code=status.HTTP_200_OK,
    summary="Get vendor store profile (Vendor only)",
)
def get_my_store_profile(
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[VendorProfileOut]:
    vendor_service = VendorService(db)
    profile = vendor_service.get_my_profile(vendor.id)
    return APIResponse(
        success=True,
        message="Store profile retrieved successfully",
        data=VendorProfileOut.model_validate(profile),
    )


@router.post(
    "/me",
    response_model=APIResponse[VendorProfileOut],
    status_code=status.HTTP_201_CREATED,
    summary="Setup vendor store profile (Vendor only)",
    description="Creates or initialises the vendor's storefront configuration.",
)
def setup_store_profile(
    profile_in: VendorProfileCreate,
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[VendorProfileOut]:
    vendor_service = VendorService(db)
    profile = vendor_service.create_or_update_profile(vendor, profile_in)
    return APIResponse(
        success=True,
        message="Store profile configured successfully. Pending administrative verification.",
        data=VendorProfileOut.model_validate(profile),
    )


@router.put(
    "/me",
    response_model=APIResponse[VendorProfileOut],
    status_code=status.HTTP_200_OK,
    summary="Update vendor store settings (Vendor only)",
)
def update_store_profile(
    update_in: VendorProfileUpdate,
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[VendorProfileOut]:
    vendor_service = VendorService(db)
    updated_profile = vendor_service.update_profile(vendor, update_in)
    return APIResponse(
        success=True,
        message="Store profile updated successfully",
        data=VendorProfileOut.model_validate(updated_profile),
    )


@router.delete(
    "/me",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete vendor store profile (Vendor only)",
)
def delete_store_profile(
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    vendor_service = VendorService(db)
    vendor_service.delete_profile(vendor)
    return APIResponse(
        success=True,
        message="Store profile deleted successfully",
        data={"deleted": True},
    )


@router.put(
    "/{vendor_user_id}/status",
    response_model=APIResponse[VendorProfileOut],
    status_code=status.HTTP_200_OK,
    summary="Approve, reject, or suspend a vendor store (Admin only alias)",
)
def update_vendor_status_alias(
    vendor_user_id: int,
    status_in: VendorStatusUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[VendorProfileOut]:
    vendor_service = VendorService(db)
    updated = vendor_service.admin_update_vendor_status(vendor_user_id, status_in)
    return APIResponse(
        success=True,
        message=f"Vendor status updated to {updated.status.value}",
        data=VendorProfileOut.model_validate(updated),
    )


@router.get(
    "/store/{slug}",
    response_model=APIResponse[VendorProfileOut],
    status_code=status.HTTP_200_OK,
    summary="View public vendor store profile (Public)",
    description="Retrieve storefront information for an approved and active vendor.",
)
def get_public_store(
    slug: str,
    db: Session = Depends(get_db),
) -> APIResponse[VendorProfileOut]:
    vendor_service = VendorService(db)
    profile = vendor_service.get_public_store_profile(slug)
    return APIResponse(
        success=True,
        message="Public storefront retrieved",
        data=VendorProfileOut.model_validate(profile),
    )
