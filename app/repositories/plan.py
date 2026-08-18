from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.schemas.plan import PlanCreate


class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, plan_id: int) -> Optional[Plan]:
        """Fetch SaaS plan by primary key."""
        stmt = select(Plan).where(Plan.id == plan_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Optional[Plan]:
        """Fetch SaaS plan by unique slug."""
        stmt = select(Plan).where(func.lower(Plan.slug) == slug.lower().strip())
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_name(self, name: str) -> Optional[Plan]:
        """Fetch SaaS plan by unique name."""
        stmt = select(Plan).where(func.lower(Plan.name) == name.lower().strip())
        return self.db.execute(stmt).scalar_one_or_none()

    def exists_by_name_or_slug(
        self,
        name: str,
        slug: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Check if plan name or slug already exists."""
        stmt = select(Plan.id).where(
            or_(
                func.lower(Plan.name) == name.lower().strip(),
                func.lower(Plan.slug) == slug.lower().strip(),
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(Plan.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def create(self, plan_in: PlanCreate) -> Plan:
        """Create and persist a new SaaS plan."""
        slug = plan_in.slug.lower().strip() if plan_in.slug else plan_in.name.lower().strip().replace(" ", "-")
        db_plan = Plan(
            name=plan_in.name.strip(),
            slug=slug,
            description=plan_in.description.strip() if plan_in.description else None,
            price=plan_in.price,
            currency=plan_in.currency.upper().strip(),
            billing_cycle=plan_in.billing_cycle.upper().strip(),
            max_products=plan_in.max_products,
            commission_rate=plan_in.commission_rate,
            is_active=plan_in.is_active,
        )
        self.db.add(db_plan)
        self.db.commit()
        self.db.refresh(db_plan)
        return db_plan

    def update(self, plan: Plan, update_data: dict) -> Plan:
        """Update fields on an existing plan."""
        for field, value in update_data.items():
            if hasattr(plan, field) and value is not None:
                if field == "slug" and isinstance(value, str):
                    value = value.lower().strip()
                elif field in ("currency", "billing_cycle") and isinstance(value, str):
                    value = value.upper().strip()
                setattr(plan, field, value)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def delete(self, plan: Plan) -> bool:
        """Delete plan from database."""
        self.db.delete(plan)
        self.db.commit()
        return True

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        only_active: bool = False,
    ) -> List[Plan]:
        """List SaaS plans with optional active filter and pagination."""
        stmt = select(Plan)
        if only_active:
            stmt = stmt.where(Plan.is_active.is_(True))
        stmt = stmt.offset(skip).limit(limit).order_by(Plan.price.asc(), Plan.id.asc())
        return list(self.db.execute(stmt).scalars().all())

    def count(self, only_active: bool = False) -> int:
        """Count total SaaS plans."""
        stmt = select(func.count(Plan.id))
        if only_active:
            stmt = stmt.where(Plan.is_active.is_(True))
        return self.db.execute(stmt).scalar() or 0
