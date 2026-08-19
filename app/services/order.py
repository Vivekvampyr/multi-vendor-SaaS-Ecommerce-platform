from datetime import datetime, timezone
import logging
from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.product import ProductStatus
from app.models.subscription import SubscriptionStatus
from app.models.user import User, UserRole
from app.repositories.cart import CartRepository
from app.repositories.coupon import CouponRepository
from app.repositories.order import OrderRepository
from app.repositories.product import ProductRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.coupon import CouponValidateRequest
from app.schemas.order import OrderCheckoutRequest, OrderItemStatusUpdate, OrderPayRequest
from app.services.coupon import CouponService

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.cart_repo = CartRepository(db)
        self.prod_repo = ProductRepository(db)
        self.sub_repo = SubscriptionRepository(db)
        self.coupon_repo = CouponRepository(db)
        self.coupon_service = CouponService(db)

    def _generate_order_number(self) -> str:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"ORD-{date_str}-{random_suffix}"

    def checkout(self, customer: User, request: OrderCheckoutRequest) -> Order:
        """
        Processes cart checkout into a multi-vendor Order with item-level commission splits,
        inventory decrement, and optional promotional coupon redemption.
        """
        # 1. Retrieve Customer Cart
        cart = self.cart_repo.get_by_user_id(customer.id)
        if not cart or not cart.items:
            raise BadRequestException("Your shopping cart is empty. Add products before checking out.")

        # 2. Validate inventory and calculate subtotal
        subtotal_amount = 0.0
        for item in cart.items:
            prod = self.prod_repo.get_by_id(item.product_id)
            if not prod or prod.status != ProductStatus.PUBLISHED or not prod.is_approved:
                raise BadRequestException(f"Product '{item.product.name if item.product else item.product_id}' is no longer available")

            if prod.stock_quantity < item.quantity:
                raise BadRequestException(
                    f"Insufficient stock for '{prod.name}' (Requested: {item.quantity}, Available: {prod.stock_quantity})"
                )

            unit_price = float(prod.price)
            subtotal_amount += round(unit_price * item.quantity, 2)

        subtotal_amount = round(subtotal_amount, 2)

        # 3. Apply Coupon if provided
        discount_amount = 0.0
        applied_coupon = None
        if request.coupon_code:
            val_result = self.coupon_service.validate_coupon(
                request=CouponValidateRequest(code=request.coupon_code, subtotal=subtotal_amount),
                user=customer,
            )
            if not val_result.valid:
                raise BadRequestException(f"Coupon error: {val_result.message}")

            discount_amount = val_result.discount_amount
            applied_coupon = self.coupon_repo.get_by_code(request.coupon_code)

        total_amount = round(max(0.0, subtotal_amount - discount_amount), 2)
        order_number = self._generate_order_number()

        # 4. Build Order Entity
        order = Order(
            order_number=order_number,
            customer_id=customer.id,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            payment_method=request.payment_method,
            subtotal_amount=subtotal_amount,
            discount_amount=discount_amount,
            coupon_id=applied_coupon.id if applied_coupon else None,
            tax_amount=0.00,
            shipping_amount=0.00,
            total_amount=total_amount,
            shipping_address=request.shipping_address,
            billing_address=request.billing_address or request.shipping_address,
            notes=request.notes,
        )

        # 5. Build Line Items and Commission Splits
        order_items: List[OrderItem] = []
        for item in cart.items:
            prod = self.prod_repo.get_by_id(item.product_id)
            unit_price = float(prod.price)
            line_subtotal = round(unit_price * item.quantity, 2)

            # Determine Vendor Commission Rate from active SaaS Plan
            vendor_sub = self.sub_repo.get_by_vendor_id(prod.vendor_id)
            commission_rate = 20.00  # Standard fallback rate
            if vendor_sub and vendor_sub.status == SubscriptionStatus.ACTIVE and vendor_sub.plan:
                commission_rate = float(vendor_sub.plan.commission_rate)

            commission_amt = round((line_subtotal * commission_rate) / 100.0, 2)
            vendor_earn = round(line_subtotal - commission_amt, 2)

            order_item = OrderItem(
                product_id=prod.id,
                vendor_id=prod.vendor_id,
                product_name=prod.name,
                product_sku=prod.sku,
                unit_price=unit_price,
                quantity=item.quantity,
                subtotal=line_subtotal,
                commission_rate=commission_rate,
                commission_amount=commission_amt,
                vendor_earnings=vendor_earn,
                status=OrderStatus.PENDING,
            )
            order_items.append(order_item)

            # Decrement Inventory Stock
            prod.stock_quantity -= item.quantity
            if prod.stock_quantity <= 0:
                prod.status = ProductStatus.OUT_OF_STOCK
            self.db.commit()

        # 6. Persist Master Order and Items
        created_order = self.order_repo.create(order=order, items=order_items)

        # 7. Record Coupon Usage
        if applied_coupon:
            self.coupon_repo.increment_used_count(applied_coupon)
            self.coupon_repo.record_usage(
                coupon_id=applied_coupon.id,
                user_id=customer.id,
                order_id=created_order.id,
                discount_amount=discount_amount,
            )

        # 8. Clear Customer Cart
        self.cart_repo.clear_cart(cart)

        logger.info(
            "Created Order %s for customer ID %d (Total: $%s, Items: %d)",
            created_order.order_number,
            customer.id,
            str(created_order.total_amount),
            len(order_items),
        )
        return created_order

    def process_payment(self, user: User, order_id: int, request: OrderPayRequest) -> Order:
        """Simulate payment execution for an order."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException(message=f"Order with ID {order_id} not found")

        if user.role != UserRole.ADMIN and order.customer_id != user.id:
            raise ForbiddenException(message="You do not have permission to pay for this order")

        if order.payment_status == PaymentStatus.SUCCESS:
            return order

        payment_ref = request.payment_reference or f"TXN-{uuid.uuid4().hex[:12].upper()}"
        if request.simulate_status == PaymentStatus.SUCCESS:
            updated = self.order_repo.update_order_status(
                order=order,
                status=OrderStatus.PAID,
                payment_status=PaymentStatus.SUCCESS,
                payment_reference=payment_ref,
            )
        else:
            updated = self.order_repo.update_order_status(
                order=order,
                payment_status=PaymentStatus.FAILED,
                payment_reference=payment_ref,
            )

        return updated

    def get_order_by_id(self, user: User, order_id: int) -> Order:
        """Fetch order with customer, vendor, and admin access control."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException(message=f"Order with ID {order_id} not found")

        if user.role == UserRole.ADMIN:
            return order

        if user.role == UserRole.CUSTOMER and order.customer_id == user.id:
            return order

        if user.role == UserRole.VENDOR:
            # Vendor can view order if it contains their items
            has_vendor_item = any(item.vendor_id == user.id for item in order.items)
            if has_vendor_item:
                return order

        raise ForbiddenException("You do not have permission to view this order")

    def list_my_orders(self, customer_id: int, skip: int = 0, limit: int = 20) -> Tuple[List[Order], int]:
        """List orders placed by authenticated customer."""
        orders = self.order_repo.list_by_customer(customer_id=customer_id, skip=skip, limit=limit)
        total = self.order_repo.count_by_customer(customer_id=customer_id)
        return orders, total

    def list_vendor_order_items(self, vendor_id: int, skip: int = 0, limit: int = 20) -> Tuple[List[OrderItem], int]:
        """List order line items sold by a vendor."""
        items = self.order_repo.list_items_by_vendor(vendor_id=vendor_id, skip=skip, limit=limit)
        total = self.order_repo.count_items_by_vendor(vendor_id=vendor_id)
        return items, total

    def update_order_item_status(
        self,
        user: User,
        item_id: int,
        update_in: OrderItemStatusUpdate,
    ) -> OrderItem:
        """Update fulfillment status for a vendor's line item."""
        item = self.order_repo.get_item_by_id(item_id)
        if not item:
            raise NotFoundException(message=f"Order item {item_id} not found")

        if user.role != UserRole.ADMIN and item.vendor_id != user.id:
            raise ForbiddenException("You do not have permission to update this order item")

        if item.status == OrderStatus.CANCELLED and update_in.status != OrderStatus.CANCELLED:
            raise BadRequestException("Cannot modify the status of a cancelled order item")

        # Business Rule: Online orders must be paid before vendor can ship/deliver
        if update_in.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            if item.order and item.order.payment_method != "COD" and item.order.payment_status != PaymentStatus.SUCCESS:
                raise BadRequestException(
                    "Cannot ship or deliver an unpaid online order. The customer must complete online payment first."
                )

        updated = self.order_repo.update_item_status(item, update_in.status)

        # Synchronize master Order status based on all constituent line items
        if item.order:
            item_statuses = [i.status for i in item.order.items]
            has_delivered = any(s == OrderStatus.DELIVERED for s in item_statuses)
            has_shipped = any(s == OrderStatus.SHIPPED for s in item_statuses)
            has_processing = any(s == OrderStatus.PROCESSING for s in item_statuses)
            all_delivered_or_cancelled = all(s in [OrderStatus.DELIVERED, OrderStatus.CANCELLED] for s in item_statuses)
            all_cancelled = all(s == OrderStatus.CANCELLED for s in item_statuses)

            if all_cancelled:
                item.order.status = OrderStatus.CANCELLED
            elif all_delivered_or_cancelled and has_delivered:
                item.order.status = OrderStatus.DELIVERED
                # For COD orders, delivery confirms cash collection
                if item.order.payment_method == "COD":
                    item.order.payment_status = PaymentStatus.SUCCESS
            elif has_delivered or has_shipped:
                item.order.status = OrderStatus.SHIPPED
            elif has_processing:
                item.order.status = OrderStatus.PROCESSING

            self.db.commit()

        return updated

    def cancel_order(
        self,
        user: User,
        order_id: int,
        reason: Optional[str] = None,
    ) -> Order:
        """
        Allows customer or admin to cancel an order and automatically restores product inventory stock.
        Rejects cancellation if the order or any constituent item has already been SHIPPED or DELIVERED.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException(message=f"Order with ID {order_id} not found")

        if user.role != UserRole.ADMIN and order.customer_id != user.id:
            raise ForbiddenException("You do not have permission to cancel this order")

        # Strict check: Cannot cancel if order or ANY line item is SHIPPED or DELIVERED
        has_shipped_or_delivered_item = any(
            item.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]
            for item in order.items
        )
        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED] or has_shipped_or_delivered_item:
            current_state = order.status.value if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED] else "shipped/delivered"
            raise BadRequestException(
                f"Cannot cancel order #{order.order_number} because it is already {current_state}"
            )

        if order.status == OrderStatus.CANCELLED:
            raise BadRequestException(f"Order #{order.order_number} is already cancelled")

        # 1. Update Master Order Status
        order.status = OrderStatus.CANCELLED
        if order.payment_status == PaymentStatus.SUCCESS:
            order.payment_status = PaymentStatus.REFUNDED

        # 2. Update line items and restore product inventory
        for item in order.items:
            item.status = OrderStatus.CANCELLED
            prod = self.prod_repo.get_by_id(item.product_id)
            if prod:
                prod.stock_quantity += item.quantity
                if prod.status == ProductStatus.OUT_OF_STOCK and prod.stock_quantity > 0:
                    prod.status = ProductStatus.PUBLISHED

        self.db.commit()
        self.db.refresh(order)
        logger.info(
            "Order %s successfully cancelled by User ID %d (Reason: %s). Inventory restored.",
            order.order_number,
            user.id,
            reason or "Customer request",
        )
        return order

    def admin_list_orders(
        self,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Order], int]:
        """Admin list all platform orders."""
        orders = self.order_repo.list_all(status=status, skip=skip, limit=limit)
        total = self.order_repo.count_all(status=status)
        return orders, total
