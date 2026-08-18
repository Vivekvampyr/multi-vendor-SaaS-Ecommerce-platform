from datetime import datetime, timedelta, timezone
import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.subscription import SubscriptionStatus, VendorSubscription
from app.models.user import UserRole
from app.repositories.plan import PlanRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.sub_repo = SubscriptionRepository(db)
        self.plan_repo = PlanRepository(db)
        self.user_repo = UserRepository(db)

    def assign_plan(
        self,
        vendor_id: int,
        plan_id: int,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        duration_days: int = 30,
        admin_override: bool = False,
    ) -> VendorSubscription:
        """
        Assigns or updates a vendor's SaaS plan subscription.
        Validates vendor role and plan availability.
        """
        user = self.user_repo.get_by_id(vendor_id)
        if not user:
            raise NotFoundException(
                message=f"User with ID {vendor_id} not found",
                details={"vendor_id": vendor_id},
            )

        if user.role != UserRole.VENDOR:
            raise BadRequestException(
                message="Subscribing to a SaaS plan is only available for VENDOR accounts",
                details={"user_role": user.role.value},
            )

        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise NotFoundException(
                message=f"SaaS Plan with ID {plan_id} not found",
                details={"plan_id": plan_id},
            )

        if not plan.is_active and not admin_override:
            raise BadRequestException(
                message=f"SaaS Plan '{plan.name}' is currently deactivated",
                details={"plan_id": plan_id},
            )

        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=duration_days)

        subscription = self.sub_repo.create_or_update(
            vendor_id=vendor_id,
            plan_id=plan_id,
            status=status,
            start_date=now,
            end_date=end_date,
            auto_renew=True,
        )

        logger.info(
            "Assigned plan '%s' (ID: %d) to vendor ID %d. Status: %s",
            plan.name,
            plan.id,
            vendor_id,
            status.value,
        )
        return self.sub_repo.get_by_id(subscription.id) or subscription

    def get_subscription_by_vendor(self, vendor_id: int) -> VendorSubscription:
        """Fetch subscription for a vendor."""
        sub = self.sub_repo.get_by_vendor_id(vendor_id)
        if not sub:
            raise NotFoundException(
                message="Vendor has no subscription on file",
                details={"vendor_id": vendor_id},
            )
        return sub

    def cancel_subscription(self, vendor_id: int) -> VendorSubscription:
        """Cancel a vendor's active subscription."""
        sub = self.get_subscription_by_vendor(vendor_id)
        if sub.status == SubscriptionStatus.CANCELED:
            raise BadRequestException(message="Subscription is already canceled")

        updated = self.sub_repo.update_status(sub, SubscriptionStatus.CANCELED)
        logger.info("Canceled subscription for vendor ID %d", vendor_id)
        return self.sub_repo.get_by_id(updated.id) or updated

    def get_vendor_plan_limits(self, vendor_id: int) -> dict:
        """
        Retrieves active product listing limits and commission rate for a vendor.
        Enforces subscription active state.
        """
        sub = self.sub_repo.get_by_vendor_id(vendor_id)
        if not sub or sub.status != SubscriptionStatus.ACTIVE:
            raise ForbiddenException(
                message="Vendor does not have an active SaaS subscription. Please subscribe to a plan.",
                details={"vendor_id": vendor_id, "subscription_status": sub.status.value if sub else "NONE"},
            )

        plan = sub.plan
        return {
            "vendor_id": vendor_id,
            "plan_id": plan.id,
            "plan_name": plan.name,
            "max_products": plan.max_products,
            "commission_rate": float(plan.commission_rate),
            "subscription_status": sub.status,
            "is_active": True,
        }

    def list_subscriptions(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[SubscriptionStatus] = None,
    ) -> Tuple[List[VendorSubscription], int]:
        """List vendor subscriptions with pagination and optional status filter."""
        subs = self.sub_repo.list(skip=skip, limit=limit, status=status)
        total = self.sub_repo.count(status=status)
        return subs, total
