from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.vendor import VendorProfile, VendorStatus
from app.schemas.vendor import VendorProfileCreate


class VendorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, profile_id: int) -> Optional[VendorProfile]:
        """Fetch vendor profile by primary key."""
        stmt = (
            select(VendorProfile)
            .options(joinedload(VendorProfile.user))
            .where(VendorProfile.id == profile_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_id(self, user_id: int) -> Optional[VendorProfile]:
        """Fetch vendor profile by owner user_id."""
        stmt = (
            select(VendorProfile)
            .options(joinedload(VendorProfile.user))
            .where(VendorProfile.user_id == user_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Optional[VendorProfile]:
        """Fetch vendor profile by URL slug."""
        stmt = (
            select(VendorProfile)
            .options(joinedload(VendorProfile.user))
            .where(func.lower(VendorProfile.slug) == slug.lower().strip())
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_store_name(self, store_name: str) -> Optional[VendorProfile]:
        """Fetch vendor profile by store name."""
        stmt = (
            select(VendorProfile)
            .where(func.lower(VendorProfile.store_name) == store_name.lower().strip())
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def exists_by_name_or_slug(
        self,
        store_name: str,
        slug: str,
        exclude_user_id: Optional[int] = None,
    ) -> bool:
        """Check if store name or slug is already claimed."""
        stmt = select(VendorProfile.id).where(
            or_(
                func.lower(VendorProfile.store_name) == store_name.lower().strip(),
                func.lower(VendorProfile.slug) == slug.lower().strip(),
            )
        )
        if exclude_user_id is not None:
            stmt = stmt.where(VendorProfile.user_id != exclude_user_id)
        return self.db.execute(stmt).first() is not None

    def create(self, user_id: int, profile_in: VendorProfileCreate) -> VendorProfile:
        """Create and persist a new vendor profile."""
        slug = profile_in.slug.lower().strip() if profile_in.slug else profile_in.store_name.lower().strip().replace(" ", "-")
        db_profile = VendorProfile(
            user_id=user_id,
            store_name=profile_in.store_name.strip(),
            slug=slug,
            store_description=profile_in.store_description.strip() if profile_in.store_description else None,
            logo_url=profile_in.logo_url.strip() if profile_in.logo_url else None,
            banner_url=profile_in.banner_url.strip() if profile_in.banner_url else None,
            support_email=profile_in.support_email.lower().strip() if profile_in.support_email else None,
            support_phone=profile_in.support_phone.strip() if profile_in.support_phone else None,
            business_address=profile_in.business_address.strip() if profile_in.business_address else None,
            city=profile_in.city.strip() if profile_in.city else None,
            state=profile_in.state.strip() if profile_in.state else None,
            country=profile_in.country.strip() if profile_in.country else None,
            postal_code=profile_in.postal_code.strip() if profile_in.postal_code else None,
            tax_id=profile_in.tax_id.strip() if profile_in.tax_id else None,
            status=VendorStatus.PENDING,
            is_store_active=profile_in.is_store_active,
        )
        self.db.add(db_profile)
        self.db.commit()
        self.db.refresh(db_profile)
        return db_profile

    def update(self, profile: VendorProfile, update_data: dict) -> VendorProfile:
        """Update fields on an existing vendor profile."""
        for field, value in update_data.items():
            if hasattr(profile, field) and value is not None:
                if field == "slug" and isinstance(value, str):
                    value = value.lower().strip()
                elif field == "support_email" and isinstance(value, str):
                    value = value.lower().strip()
                setattr(profile, field, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_status(
        self,
        profile: VendorProfile,
        status: VendorStatus,
        rejection_reason: Optional[str] = None,
    ) -> VendorProfile:
        """Update verification status (approve, reject, suspend)."""
        profile.status = status
        profile.rejection_reason = rejection_reason if status in (VendorStatus.REJECTED, VendorStatus.SUSPENDED) else None
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[VendorStatus] = None,
    ) -> List[VendorProfile]:
        """List vendor profiles with optional status filter."""
        stmt = (
            select(VendorProfile)
            .options(joinedload(VendorProfile.user))
            .offset(skip)
            .limit(limit)
            .order_by(VendorProfile.id.desc())
        )
        if status is not None:
            stmt = stmt.where(VendorProfile.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def delete(self, profile: VendorProfile) -> bool:
        """Delete vendor profile from database."""
        self.db.delete(profile)
        self.db.commit()
        return True

    def count(self, status: Optional[VendorStatus] = None) -> int:
        """Count total vendor profiles."""
        stmt = select(func.count(VendorProfile.id))
        if status is not None:
            stmt = stmt.where(VendorProfile.status == status)
        return self.db.execute(stmt).scalar() or 0

    def list_public_stores(
        self,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[tuple[VendorProfile, int]]:
        """
        List active and approved vendor profiles with their product count.
        """
        from app.models.product import Product, ProductStatus

        prod_count_sub = (
            select(func.count(Product.id))
            .where(
                Product.vendor_id == VendorProfile.user_id,
                Product.status == ProductStatus.PUBLISHED,
                Product.is_approved.is_(True),
            )
            .correlate(VendorProfile)
            .scalar_subquery()
        )

        stmt = (
            select(VendorProfile, prod_count_sub.label("product_count"))
            .options(joinedload(VendorProfile.user))
            .where(
                VendorProfile.status == VendorStatus.APPROVED,
                VendorProfile.is_store_active.is_(True),
            )
        )

        if search:
            pattern = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(VendorProfile.store_name).like(pattern),
                    func.lower(VendorProfile.store_description).like(pattern),
                    func.lower(VendorProfile.city).like(pattern),
                    func.lower(VendorProfile.country).like(pattern),
                )
            )

        stmt = stmt.offset(skip).limit(limit).order_by(VendorProfile.id.desc())
        results = self.db.execute(stmt).all()
        return [(row[0], row[1] or 0) for row in results]

    def count_public_stores(self, search: Optional[str] = None) -> int:
        """Count active, approved vendor profiles matching search."""
        stmt = select(func.count(VendorProfile.id)).where(
            VendorProfile.status == VendorStatus.APPROVED,
            VendorProfile.is_store_active.is_(True),
        )
        if search:
            pattern = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(VendorProfile.store_name).like(pattern),
                    func.lower(VendorProfile.store_description).like(pattern),
                    func.lower(VendorProfile.city).like(pattern),
                    func.lower(VendorProfile.country).like(pattern),
                )
            )
        return self.db.execute(stmt).scalar() or 0
