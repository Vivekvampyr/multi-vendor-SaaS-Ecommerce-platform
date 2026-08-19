from typing import List
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.plan import Plan
from app.models.subscription import SubscriptionStatus, VendorSubscription
from app.models.user import User, UserRole
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
        """Aggregate high-level platform statistics and financial analytics for the administrator."""
        total_users = self.user_repo.count()
        total_admins = self.user_repo.count(role=UserRole.ADMIN)
        total_vendors = self.user_repo.count(role=UserRole.VENDOR)
        total_customers = self.user_repo.count(role=UserRole.CUSTOMER)

        total_plans = self.plan_repo.count()
        total_active_plans = self.plan_repo.count(only_active=True)

        total_subscriptions = self.sub_repo.count()
        total_active_subscriptions = self.sub_repo.count(status=SubscriptionStatus.ACTIVE)

        # 1. SaaS Subscription Revenue (Monthly recurring revenue from active vendor subscriptions)
        sub_rev_stmt = (
            select(func.coalesce(func.sum(Plan.price), 0.0))
            .select_from(VendorSubscription)
            .join(Plan, VendorSubscription.plan_id == Plan.id)
            .where(VendorSubscription.status == SubscriptionStatus.ACTIVE)
        )
        subscription_revenue = float(self.db.execute(sub_rev_stmt).scalar() or 0.0)

        # 2. Marketplace Product Sales Commission (from paid orders / order items)
        comm_rev_stmt = (
            select(func.coalesce(func.sum(OrderItem.commission_amount), 0.0))
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                (Order.payment_status == PaymentStatus.SUCCESS)
                | (Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
            )
        )
        commission_revenue = float(self.db.execute(comm_rev_stmt).scalar() or 0.0)

        # 3. Total Combined Admin Revenue
        total_revenue = round(subscription_revenue + commission_revenue, 2)

        # 4. Gross Merchandise Value (GMV) of all paid sales
        gmv_stmt = (
            select(func.coalesce(func.sum(Order.total_amount), 0.0))
            .where(
                (Order.payment_status == PaymentStatus.SUCCESS)
                | (Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
            )
        )
        total_gmv = float(self.db.execute(gmv_stmt).scalar() or 0.0)

        # 5. Vendor Net Payouts (after platform commission)
        payout_stmt = (
            select(func.coalesce(func.sum(OrderItem.vendor_earnings), 0.0))
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                (Order.payment_status == PaymentStatus.SUCCESS)
                | (Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
            )
        )
        total_vendor_payouts = float(self.db.execute(payout_stmt).scalar() or 0.0)

        # 6. Paid Orders Count
        paid_orders_stmt = (
            select(func.count(Order.id))
            .where(
                (Order.payment_status == PaymentStatus.SUCCESS)
                | (Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
            )
        )
        total_paid_orders = int(self.db.execute(paid_orders_stmt).scalar() or 0)

        # 7. Products Sold Quantity
        items_sold_stmt = (
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .select_from(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                (Order.payment_status == PaymentStatus.SUCCESS)
                | (Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
            )
        )
        total_products_sold = int(self.db.execute(items_sold_stmt).scalar() or 0)

        return AdminDashboardStats(
            total_users=total_users,
            total_admins=total_admins,
            total_vendors=total_vendors,
            total_customers=total_customers,
            total_plans=total_plans,
            total_active_plans=total_active_plans,
            total_subscriptions=total_subscriptions,
            total_active_subscriptions=total_active_subscriptions,
            subscription_revenue=round(subscription_revenue, 2),
            commission_revenue=round(commission_revenue, 2),
            total_revenue=total_revenue,
            total_gmv=round(total_gmv, 2),
            total_vendor_payouts=round(total_vendor_payouts, 2),
            total_paid_orders=total_paid_orders,
            total_products_sold=total_products_sold,
        )

    def get_recent_commission_transactions(self, limit: int = 50) -> List[OrderItem]:
        """Fetch recent order items with commission calculations for administrative auditing."""
        stmt = (
            select(OrderItem)
            .options(
                joinedload(OrderItem.order).joinedload(Order.customer),
                joinedload(OrderItem.vendor).joinedload(User.vendor_profile),
                joinedload(OrderItem.product),
            )
            .order_by(OrderItem.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
