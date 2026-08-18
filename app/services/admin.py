from sqlalchemy.orm import Session

from app.models.subscription import SubscriptionStatus
from app.models.user import UserRole
from app.repositories.plan import PlanRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.user import UserRepository
from app.schemas.admin import AdminDashboardStats


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.plan_repo = PlanRepository(db)
        self.sub_repo = SubscriptionRepository(db)

    def get_dashboard_stats(self) -> AdminDashboardStats:
        """Aggregate high-level platform statistics for the administrator."""
        total_users = self.user_repo.count()
        total_admins = self.user_repo.count(role=UserRole.ADMIN)
        total_vendors = self.user_repo.count(role=UserRole.VENDOR)
        total_customers = self.user_repo.count(role=UserRole.CUSTOMER)

        total_plans = self.plan_repo.count()
        total_active_plans = self.plan_repo.count(only_active=True)

        total_subscriptions = self.sub_repo.count()
        total_active_subscriptions = self.sub_repo.count(status=SubscriptionStatus.ACTIVE)

        return AdminDashboardStats(
            total_users=total_users,
            total_admins=total_admins,
            total_vendors=total_vendors,
            total_customers=total_customers,
            total_plans=total_plans,
            total_active_plans=total_active_plans,
            total_subscriptions=total_subscriptions,
            total_active_subscriptions=total_active_subscriptions,
        )
