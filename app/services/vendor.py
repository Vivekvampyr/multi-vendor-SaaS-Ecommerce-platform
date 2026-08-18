import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.models.subscription import SubscriptionStatus
from app.models.user import User, UserRole
from app.models.vendor import VendorProfile, VendorStatus
from app.repositories.subscription import SubscriptionRepository
from app.repositories.vendor import VendorRepository
from app.schemas.plan import slugify
from app.schemas.subscription import VendorPlanLimitsOut, VendorSubscriptionOut
from app.schemas.vendor import (
    VendorDashboardOverview,
    VendorProfileCreate,
    VendorProfileOut,
    VendorProfileUpdate,
    VendorStatusUpdate,
)

logger = logging.getLogger(__name__)


class VendorService:
    def __init__(self, db: Session):
        self.db = db
        self.vendor_repo = VendorRepository(db)
        self.sub_repo = SubscriptionRepository(db)

    def create_or_update_profile(
        self,
        vendor_user: User,
        profile_in: VendorProfileCreate,
    ) -> VendorProfile:
        """
        Create a new vendor store profile or update if it already exists.
        Validates store name and slug uniqueness.
        """
        if vendor_user.role != UserRole.VENDOR:
            raise BadRequestException(
                message="Only accounts with role VENDOR can configure a store profile",
                details={"user_role": vendor_user.role.value},
            )

        slug = profile_in.slug or slugify(profile_in.store_name)
        if self.vendor_repo.exists_by_name_or_slug(
            store_name=profile_in.store_name,
            slug=slug,
            exclude_user_id=vendor_user.id,
        ):
            raise ConflictException(
                message=f"Store name '{profile_in.store_name}' or slug '{slug}' is already taken",
                details={"store_name": profile_in.store_name, "slug": slug},
            )

        existing = self.vendor_repo.get_by_user_id(vendor_user.id)
        if existing:
            update_data = profile_in.model_dump(exclude_unset=True)
            update_data["slug"] = slug
            return self.vendor_repo.update(existing, update_data)

        profile = self.vendor_repo.create(user_id=vendor_user.id, profile_in=profile_in)
        logger.info("Created store profile for vendor %d: StoreName='%s'", vendor_user.id, profile.store_name)
        return profile

    def update_profile(
        self,
        vendor_user: User,
        update_in: VendorProfileUpdate,
    ) -> VendorProfile:
        """Update existing vendor profile."""
        profile = self.vendor_repo.get_by_user_id(vendor_user.id)
        if not profile:
            raise NotFoundException(
                message="Vendor profile has not been created yet. Please create a store profile first.",
                details={"user_id": vendor_user.id},
            )

        update_data = update_in.model_dump(exclude_unset=True)
        if not update_data:
            return profile

        store_name = update_data.get("store_name", profile.store_name)
        slug = update_data.get("slug", profile.slug)
        if "store_name" in update_data and not update_in.slug:
            slug = slugify(store_name)
            update_data["slug"] = slug

        if self.vendor_repo.exists_by_name_or_slug(store_name, slug, exclude_user_id=vendor_user.id):
            raise ConflictException(
                message=f"Store name '{store_name}' or slug '{slug}' is already taken",
                details={"store_name": store_name, "slug": slug},
            )

        return self.vendor_repo.update(profile, update_data)

    def get_my_profile(self, vendor_id: int) -> VendorProfile:
        """Fetch own vendor profile or 404."""
        profile = self.vendor_repo.get_by_user_id(vendor_id)
        if not profile:
            raise NotFoundException(
                message="Store profile not found for this vendor account",
                details={"vendor_id": vendor_id},
            )
        return profile

    def get_public_store_profile(self, slug: str) -> VendorProfile:
        """Fetch public vendor store profile by slug."""
        profile = self.vendor_repo.get_by_slug(slug)
        if not profile or profile.status != VendorStatus.APPROVED or not profile.is_store_active:
            raise NotFoundException(
                message=f"Store '{slug}' is not found or currently unavailable",
                details={"slug": slug},
            )
        return profile

    def get_vendor_dashboard(self, vendor_user: User) -> VendorDashboardOverview:
        """
        Aggregates vendor dashboard information including store profile,
        active subscription, plan limits, and operational status.
        """
        profile = self.vendor_repo.get_by_user_id(vendor_user.id)
        subscription = self.sub_repo.get_by_vendor_id(vendor_user.id)

        plan_limits = None
        has_active_sub = False
        if subscription and subscription.status == SubscriptionStatus.ACTIVE and subscription.plan:
            has_active_sub = True
            plan_limits = VendorPlanLimitsOut(
                vendor_id=vendor_user.id,
                plan_id=subscription.plan.id,
                plan_name=subscription.plan.name,
                max_products=subscription.plan.max_products,
                commission_rate=float(subscription.plan.commission_rate),
                subscription_status=subscription.status,
                is_active=True,
            )

        status = profile.status if profile else VendorStatus.PENDING
        can_list_products = (
            profile is not None
            and profile.status == VendorStatus.APPROVED
            and has_active_sub
        )
        store_is_live = (
            profile is not None
            and profile.status == VendorStatus.APPROVED
            and profile.is_store_active
        )

        return VendorDashboardOverview(
            vendor_profile=VendorProfileOut.model_validate(profile) if profile else None,
            subscription=VendorSubscriptionOut.model_validate(subscription) if subscription else None,
            plan_limits=plan_limits,
            status=status,
            can_list_products=can_list_products,
            store_is_live=store_is_live,
        )

    def admin_update_vendor_status(
        self,
        vendor_user_id: int,
        status_in: VendorStatusUpdate,
    ) -> VendorProfile:
        """Admin operation to approve, reject, or suspend a vendor profile."""
        profile = self.vendor_repo.get_by_user_id(vendor_user_id)
        if not profile:
            raise NotFoundException(
                message=f"No store profile found for vendor user ID {vendor_user_id}",
                details={"vendor_user_id": vendor_user_id},
            )

        updated = self.vendor_repo.update_status(
            profile=profile,
            status=status_in.status,
            rejection_reason=status_in.rejection_reason,
        )
        logger.info(
            "Admin updated vendor status: UserID=%d, Status=%s",
            vendor_user_id,
            status_in.status.value,
        )
        return updated

    def admin_list_vendors(
        self,
        status: Optional[VendorStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[VendorProfile], int]:
        """Admin list of vendor store profiles."""
        profiles = self.vendor_repo.list(skip=skip, limit=limit, status=status)
        total = self.vendor_repo.count(status=status)
        return profiles, total
