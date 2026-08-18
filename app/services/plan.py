import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.models.plan import Plan
from app.models.subscription import SubscriptionStatus
from app.repositories.plan import PlanRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.plan import PlanCreate, PlanUpdate

logger = logging.getLogger(__name__)


class PlanService:
    def __init__(self, db: Session):
        self.db = db
        self.plan_repo = PlanRepository(db)
        self.sub_repo = SubscriptionRepository(db)

    def create_plan(self, plan_in: PlanCreate) -> Plan:
        """Create a new SaaS Plan after validating uniqueness and constraints."""
        slug = plan_in.slug or plan_in.name.lower().strip().replace(" ", "-")
        if self.plan_repo.exists_by_name_or_slug(plan_in.name, slug):
            raise ConflictException(
                message=f"A plan with name '{plan_in.name}' or slug '{slug}' already exists",
                details={"name": plan_in.name, "slug": slug},
            )

        if not (0.0 <= plan_in.commission_rate <= 100.0):
            raise BadRequestException(
                message="Commission rate must be between 0.0% and 100.0%",
                details={"commission_rate": plan_in.commission_rate},
            )

        if plan_in.max_products < 1:
            raise BadRequestException(
                message="Maximum products limit must be at least 1",
                details={"max_products": plan_in.max_products},
            )

        created_plan = self.plan_repo.create(plan_in)
        logger.info("Created new SaaS Plan: ID=%d, Name='%s', MaxProducts=%d, Commission=%s%%",
                    created_plan.id, created_plan.name, created_plan.max_products, created_plan.commission_rate)
        return created_plan

    def get_plan_by_id(self, plan_id: int) -> Plan:
        """Retrieve a plan by ID or raise NotFoundException."""
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise NotFoundException(
                message=f"SaaS Plan with ID {plan_id} does not exist",
                details={"plan_id": plan_id},
            )
        return plan

    def get_plan_by_slug(self, slug: str) -> Plan:
        """Retrieve a plan by slug or raise NotFoundException."""
        plan = self.plan_repo.get_by_slug(slug)
        if not plan:
            raise NotFoundException(
                message=f"SaaS Plan with slug '{slug}' does not exist",
                details={"slug": slug},
            )
        return plan

    def update_plan(self, plan_id: int, update_in: PlanUpdate) -> Plan:
        """Update an existing SaaS Plan."""
        plan = self.get_plan_by_id(plan_id)
        update_data = update_in.model_dump(exclude_unset=True)

        if not update_data:
            return plan

        name = update_data.get("name", plan.name)
        slug = update_data.get("slug", plan.slug)
        if self.plan_repo.exists_by_name_or_slug(name, slug, exclude_id=plan.id):
            raise ConflictException(
                message="Another plan with this name or slug already exists",
                details={"name": name, "slug": slug},
            )

        if "commission_rate" in update_data:
            comm = update_data["commission_rate"]
            if not (0.0 <= comm <= 100.0):
                raise BadRequestException(message="Commission rate must be between 0.0% and 100.0%")

        if "max_products" in update_data:
            if update_data["max_products"] < 1:
                raise BadRequestException(message="Maximum products limit must be at least 1")

        return self.plan_repo.update(plan, update_data)

    def delete_plan(self, plan_id: int) -> bool:
        """Delete a SaaS Plan or disallow if active subscribers exist."""
        plan = self.get_plan_by_id(plan_id)
        active_subs = [s for s in plan.subscriptions if s.status == SubscriptionStatus.ACTIVE]
        if active_subs:
            raise ConflictException(
                message="Cannot delete plan with active vendor subscriptions. Deactivate it instead.",
                details={"active_subscribers_count": len(active_subs)},
            )
        return self.plan_repo.delete(plan)

    def list_plans(
        self,
        only_active: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Plan], int]:
        """List SaaS plans with total count."""
        plans = self.plan_repo.list(skip=skip, limit=limit, only_active=only_active)
        total = self.plan_repo.count(only_active=only_active)
        return plans, total
