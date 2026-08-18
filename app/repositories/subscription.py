from datetime import datetime
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.subscription import SubscriptionStatus, VendorSubscription


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, subscription_id: int) -> Optional[VendorSubscription]:
        """Fetch subscription by ID with joined plan and vendor."""
        stmt = (
            select(VendorSubscription)
            .options(joinedload(VendorSubscription.plan), joinedload(VendorSubscription.vendor))
            .where(VendorSubscription.id == subscription_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_vendor_id(self, vendor_id: int) -> Optional[VendorSubscription]:
        """Fetch active or latest subscription for a vendor."""
        stmt = (
            select(VendorSubscription)
            .options(joinedload(VendorSubscription.plan))
            .where(VendorSubscription.vendor_id == vendor_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create_or_update(
        self,
        vendor_id: int,
        plan_id: int,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        auto_renew: bool = True,
    ) -> VendorSubscription:
        """Create new subscription or update existing one for a vendor."""
        existing = self.get_by_vendor_id(vendor_id)
        if existing:
            existing.plan_id = plan_id
            existing.status = status
            if start_date:
                existing.start_date = start_date
            existing.end_date = end_date
            existing.auto_renew = auto_renew
            self.db.commit()
            self.db.refresh(existing)
            return existing

        db_sub = VendorSubscription(
            vendor_id=vendor_id,
            plan_id=plan_id,
            status=status,
            start_date=start_date or datetime.now(),
            end_date=end_date,
            auto_renew=auto_renew,
        )
        self.db.add(db_sub)
        self.db.commit()
        self.db.refresh(db_sub)
        return db_sub

    def update_status(
        self,
        subscription: VendorSubscription,
        status: SubscriptionStatus,
    ) -> VendorSubscription:
        """Update subscription status."""
        subscription.status = status
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[SubscriptionStatus] = None,
    ) -> List[VendorSubscription]:
        """List vendor subscriptions with optional status filter."""
        stmt = (
            select(VendorSubscription)
            .options(joinedload(VendorSubscription.plan))
            .offset(skip)
            .limit(limit)
            .order_by(VendorSubscription.id.desc())
        )
        if status is not None:
            stmt = stmt.where(VendorSubscription.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def count(self, status: Optional[SubscriptionStatus] = None) -> int:
        """Count total subscriptions."""
        stmt = select(func.count(VendorSubscription.id))
        if status is not None:
            stmt = stmt.where(VendorSubscription.status == status)
        return self.db.execute(stmt).scalar() or 0
