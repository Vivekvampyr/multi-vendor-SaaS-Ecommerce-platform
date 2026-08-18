from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Fetch order by primary key ID with items and products."""
        stmt = (
            select(Order)
            .options(
                joinedload(Order.items).joinedload(OrderItem.product),
                joinedload(Order.customer),
            )
            .where(Order.id == order_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_order_number(self, order_number: str) -> Optional[Order]:
        """Fetch order by unique order number."""
        stmt = (
            select(Order)
            .options(
                joinedload(Order.items).joinedload(OrderItem.product),
                joinedload(Order.customer),
            )
            .where(Order.order_number == order_number.strip())
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def create(self, order: Order, items: List[OrderItem]) -> Order:
        """Persist new master order and line items."""
        self.db.add(order)
        self.db.flush()

        for item in items:
            item.order_id = order.id
            self.db.add(item)

        self.db.commit()
        return self.get_by_id(order.id) or order

    def update_order_status(
        self,
        order: Order,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        payment_reference: Optional[str] = None,
    ) -> Order:
        """Update overall order lifecycle or payment status."""
        if status:
            order.status = status
            # Cascade status to all line items if order is cancelled
            if status == OrderStatus.CANCELLED:
                for item in order.items:
                    item.status = OrderStatus.CANCELLED
        if payment_status:
            order.payment_status = payment_status
        if payment_reference:
            order.payment_reference = payment_reference

        self.db.commit()
        return self.get_by_id(order.id) or order

    def list_by_customer(self, customer_id: int, skip: int = 0, limit: int = 20) -> List[Order]:
        """List orders placed by a specific customer."""
        stmt = (
            select(Order)
            .options(joinedload(Order.items))
            .where(Order.customer_id == customer_id)
            .order_by(Order.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def count_by_customer(self, customer_id: int) -> int:
        """Count orders for a customer."""
        stmt = select(func.count(Order.id)).where(Order.customer_id == customer_id)
        return self.db.execute(stmt).scalar() or 0

    def list_items_by_vendor(self, vendor_id: int, skip: int = 0, limit: int = 20) -> List[OrderItem]:
        """List order items belonging to a specific vendor."""
        stmt = (
            select(OrderItem)
            .options(
                joinedload(OrderItem.order),
                joinedload(OrderItem.product),
            )
            .where(OrderItem.vendor_id == vendor_id)
            .order_by(OrderItem.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_items_by_vendor(self, vendor_id: int) -> int:
        """Count order line items for a vendor."""
        stmt = select(func.count(OrderItem.id)).where(OrderItem.vendor_id == vendor_id)
        return self.db.execute(stmt).scalar() or 0

    def get_item_by_id(self, item_id: int) -> Optional[OrderItem]:
        """Fetch single order item."""
        stmt = (
            select(OrderItem)
            .options(joinedload(OrderItem.order))
            .where(OrderItem.id == item_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update_item_status(self, item: OrderItem, status: OrderStatus) -> OrderItem:
        """Update individual vendor order item fulfillment status."""
        item.status = status
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_all(
        self,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Order]:
        """Admin list all platform orders."""
        stmt = (
            select(Order)
            .options(joinedload(Order.items), joinedload(Order.customer))
            .order_by(Order.id.desc())
            .offset(skip)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(Order.status == status)
        return list(self.db.execute(stmt).unique().scalars().all())

    def count_all(self, status: Optional[OrderStatus] = None) -> int:
        """Admin count all platform orders."""
        stmt = select(func.count(Order.id))
        if status is not None:
            stmt = stmt.where(Order.status == status)
        return self.db.execute(stmt).scalar() or 0
