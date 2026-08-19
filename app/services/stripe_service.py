import json
import logging
from typing import Optional
import uuid
from sqlalchemy.orm import Session

import stripe

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.plan import Plan
from app.models.subscription import SubscriptionStatus, VendorSubscription
from app.models.user import User, UserRole
from app.repositories.order import OrderRepository
from app.repositories.plan import PlanRepository
from app.repositories.subscription import SubscriptionRepository
from app.repositories.user import UserRepository
from app.schemas.payment import (
    CheckoutSessionOut,
    PaymentIntentOut,
    StripeConfigOut,
    WebhookResponseOut,
)

logger = logging.getLogger(__name__)


class StripeService:
    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.plan_repo = PlanRepository(db)
        self.sub_repo = SubscriptionRepository(db)
        self.user_repo = UserRepository(db)

        if settings.is_stripe_configured:
            stripe.api_key = settings.STRIPE_SECRET_KEY

    def get_config(self) -> StripeConfigOut:
        """Returns public Stripe gateway configuration."""
        return StripeConfigOut(
            is_configured=settings.is_stripe_configured,
            publishable_key=settings.STRIPE_PUBLISHABLE_KEY or "pk_test_simulated_stripe_key",
            currency=settings.STRIPE_CURRENCY.lower(),
        )

    def create_order_checkout_session(
        self,
        user: User,
        order_id: int,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> CheckoutSessionOut:
        """
        Creates a Stripe Checkout Session for an unpaid customer order.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException(message=f"Order with ID {order_id} not found")

        if user.role != UserRole.ADMIN and order.customer_id != user.id:
            raise ForbiddenException(message="You do not have permission to pay for this order")

        if order.payment_status == PaymentStatus.SUCCESS:
            raise BadRequestException(message="This order has already been paid successfully")

        # Fallback / Simulation mode if Stripe keys are not provided
        if not settings.is_stripe_configured:
            simulated_session_id = f"cs_test_mock_{uuid.uuid4().hex[:12]}"
            sim_success = success_url or f"/orders/{order.id}/success?session_id={simulated_session_id}"
            return CheckoutSessionOut(
                session_id=simulated_session_id,
                url=sim_success,
                payment_status="unpaid",
                mode="payment",
                is_simulation=True,
            )

        # Real Stripe Checkout Session Creation
        try:
            line_items = []
            if order.items and len(order.items) > 0:
                for item in order.items:
                    line_items.append({
                        "price_data": {
                            "currency": settings.STRIPE_CURRENCY.lower(),
                            "product_data": {
                                "name": item.product_name,
                                "description": f"SKU: {item.product_sku}",
                            },
                            "unit_amount": int(round(float(item.unit_price) * 100)),
                        },
                        "quantity": item.quantity,
                    })
            else:
                line_items.append({
                    "price_data": {
                        "currency": settings.STRIPE_CURRENCY.lower(),
                        "product_data": {
                            "name": f"Order {order.order_number}",
                        },
                        "unit_amount": int(round(float(order.total_amount) * 100)),
                    },
                    "quantity": 1,
                })

            s_url = success_url or f"http://{settings.HOST}:{settings.PORT}/orders/{order.id}/success?session_id={{CHECKOUT_SESSION_ID}}"
            c_url = cancel_url or f"http://{settings.HOST}:{settings.PORT}/cart"

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                customer_email=user.email,
                client_reference_id=str(order.id),
                metadata={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "customer_id": str(user.id),
                    "type": "order_payment",
                },
                success_url=s_url,
                cancel_url=c_url,
            )

            logger.info("Created Stripe Checkout Session %s for Order ID %d", session.id, order.id)
            return CheckoutSessionOut(
                session_id=session.id,
                url=session.url,
                payment_status=session.payment_status,
                mode="payment",
                is_simulation=False,
            )
        except Exception as e:
            logger.error("Stripe Checkout Session error for Order ID %d: %s", order.id, str(e))
            raise BadRequestException(message=f"Stripe payment session error: {str(e)}")

    def create_subscription_checkout_session(
        self,
        vendor: User,
        plan_id: int,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> CheckoutSessionOut:
        """
        Creates a Stripe Checkout Session for a Vendor SaaS Plan subscription.
        """
        if vendor.role != UserRole.VENDOR and vendor.role != UserRole.ADMIN:
            raise BadRequestException(message="SaaS subscription plans are only available for VENDOR accounts")

        plan = self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise NotFoundException(message=f"SaaS Plan with ID {plan_id} not found")

        if not plan.is_active:
            raise BadRequestException(message=f"SaaS Plan '{plan.name}' is currently inactive")

        # Fallback / Simulation mode if Stripe keys are not provided
        if not settings.is_stripe_configured:
            simulated_session_id = f"cs_sub_mock_{uuid.uuid4().hex[:12]}"
            # Auto-assign plan in simulation mode
            from app.services.subscription import SubscriptionService
            sub_service = SubscriptionService(self.db)
            sub_service.assign_plan(vendor_id=vendor.id, plan_id=plan.id)

            sim_success = success_url or f"/vendor/dashboard?subscribed_plan={plan.id}&simulated=true"
            return CheckoutSessionOut(
                session_id=simulated_session_id,
                url=sim_success,
                payment_status="paid",
                mode="subscription",
                is_simulation=True,
            )

        # Real Stripe Subscription Session Creation
        try:
            s_url = success_url or f"http://{settings.HOST}:{settings.PORT}/vendor/dashboard?session_id={{CHECKOUT_SESSION_ID}}&status=success"
            c_url = cancel_url or f"http://{settings.HOST}:{settings.PORT}/#plans"

            # Create or retrieve customer
            customer_id = None
            existing_sub = self.sub_repo.get_by_vendor_id(vendor.id)
            if existing_sub and existing_sub.stripe_customer_id:
                customer_id = existing_sub.stripe_customer_id
            else:
                customer = stripe.Customer.create(
                    email=vendor.email,
                    name=vendor.full_name,
                    metadata={"vendor_id": str(vendor.id)},
                )
                customer_id = customer.id

            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": settings.STRIPE_CURRENCY.lower(),
                        "product_data": {
                            "name": f"NexusSaaS {plan.name} Tier",
                            "description": f"Max {plan.max_products} Products • {plan.commission_rate}% Commission Tier",
                        },
                        "unit_amount": int(round(float(plan.price) * 100)),
                        "recurring": {
                            "interval": "month" if plan.billing_cycle.upper() == "MONTHLY" else "year",
                        },
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                metadata={
                    "vendor_id": str(vendor.id),
                    "plan_id": str(plan.id),
                    "plan_name": plan.name,
                    "type": "saas_subscription",
                },
                success_url=s_url,
                cancel_url=c_url,
            )

            logger.info("Created Stripe Subscription Session %s for Vendor ID %d, Plan %s", session.id, vendor.id, plan.name)
            return CheckoutSessionOut(
                session_id=session.id,
                url=session.url,
                payment_status="unpaid",
                mode="subscription",
                is_simulation=False,
            )
        except Exception as e:
            logger.error("Stripe Subscription Session error for Vendor ID %d: %s", vendor.id, str(e))
            raise BadRequestException(message=f"Stripe subscription session error: {str(e)}")

    def create_order_payment_intent(self, user: User, order_id: int) -> PaymentIntentOut:
        """
        Creates a Stripe PaymentIntent for custom inline card elements.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundException(message=f"Order with ID {order_id} not found")

        if user.role != UserRole.ADMIN and order.customer_id != user.id:
            raise ForbiddenException(message="You do not have permission to pay for this order")

        if not settings.is_stripe_configured:
            mock_id = f"pi_mock_{uuid.uuid4().hex[:12]}"
            return PaymentIntentOut(
                payment_intent_id=mock_id,
                client_secret=f"{mock_id}_secret_simulated",
                amount=float(order.total_amount),
                currency=settings.STRIPE_CURRENCY.lower(),
                status="requires_payment_method",
            )

        try:
            intent = stripe.PaymentIntent.create(
                amount=int(round(float(order.total_amount) * 100)),
                currency=settings.STRIPE_CURRENCY.lower(),
                metadata={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "customer_id": str(user.id),
                },
            )
            return PaymentIntentOut(
                payment_intent_id=intent.id,
                client_secret=intent.client_secret,
                amount=float(order.total_amount),
                currency=intent.currency,
                status=intent.status,
            )
        except Exception as e:
            logger.error("PaymentIntent creation failed for Order ID %d: %s", order.id, str(e))
            raise BadRequestException(message=f"Stripe PaymentIntent error: {str(e)}")

    def handle_webhook(self, payload: bytes, sig_header: Optional[str] = None) -> WebhookResponseOut:
        """
        Validates and processes Stripe webhook events (checkout.session.completed, invoice.paid, etc.).
        """
        event = None

        if settings.STRIPE_WEBHOOK_SECRET and sig_header:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
                )
            except Exception as e:
                logger.error("Stripe Webhook Signature Verification failed: %s", str(e))
                raise BadRequestException(message=f"Invalid webhook signature: {str(e)}")
        else:
            try:
                event = json.loads(payload.decode("utf-8"))
            except Exception as e:
                logger.error("Stripe Webhook JSON parse error: %s", str(e))
                raise BadRequestException(message="Invalid webhook payload format")

        event_type = event.get("type", "unknown")
        data_object = event.get("data", {}).get("object", {})

        logger.info("Processing Stripe Webhook Event: %s", event_type)

        # 1. Checkout Session Completed
        if event_type == "checkout.session.completed":
            metadata = data_object.get("metadata", {})
            session_mode = data_object.get("mode")

            # A. Customer Order Payment
            if session_mode == "payment" or metadata.get("type") == "order_payment":
                order_id_str = metadata.get("order_id") or data_object.get("client_reference_id")
                if order_id_str:
                    try:
                        order_id = int(order_id_str)
                        order = self.order_repo.get_by_id(order_id)
                        if order:
                            payment_intent_id = data_object.get("payment_intent") or data_object.get("id")
                            self.order_repo.update_order_status(
                                order=order,
                                status=OrderStatus.PAID,
                                payment_status=PaymentStatus.SUCCESS,
                                payment_reference=str(payment_intent_id),
                            )
                            logger.info("Marked Order #%s (ID: %d) as PAID via Stripe Webhook", order.order_number, order.id)
                    except Exception as e:
                        logger.error("Error fulfilling order from webhook: %s", str(e))

            # B. Vendor SaaS Subscription Activation
            elif session_mode == "subscription" or metadata.get("type") == "saas_subscription":
                vendor_id_str = metadata.get("vendor_id")
                plan_id_str = metadata.get("plan_id")
                if vendor_id_str and plan_id_str:
                    try:
                        from app.services.subscription import SubscriptionService
                        sub_service = SubscriptionService(self.db)
                        sub = sub_service.assign_plan(
                            vendor_id=int(vendor_id_str),
                            plan_id=int(plan_id_str),
                            status=SubscriptionStatus.ACTIVE,
                        )
                        # Save Stripe Subscription & Customer IDs
                        sub.stripe_subscription_id = data_object.get("subscription")
                        sub.stripe_customer_id = data_object.get("customer")
                        self.db.commit()
                        logger.info("Activated Vendor ID %s on Plan ID %s via Stripe Webhook", vendor_id_str, plan_id_str)
                    except Exception as e:
                        logger.error("Error activating subscription from webhook: %s", str(e))

        # 2. Payment Intent Succeeded
        elif event_type == "payment_intent.succeeded":
            metadata = data_object.get("metadata", {})
            order_id_str = metadata.get("order_id")
            if order_id_str:
                try:
                    order = self.order_repo.get_by_id(int(order_id_str))
                    if order:
                        self.order_repo.update_order_status(
                            order=order,
                            status=OrderStatus.PAID,
                            payment_status=PaymentStatus.SUCCESS,
                            payment_reference=data_object.get("id"),
                        )
                        logger.info("Order ID %s confirmed via payment_intent.succeeded", order_id_str)
                except Exception as e:
                    logger.error("Error updating order on payment_intent.succeeded: %s", str(e))

        # 3. Payment Intent Failed
        elif event_type == "payment_intent.payment_failed":
            metadata = data_object.get("metadata", {})
            order_id_str = metadata.get("order_id")
            if order_id_str:
                try:
                    order = self.order_repo.get_by_id(int(order_id_str))
                    if order:
                        self.order_repo.update_order_status(
                            order=order,
                            payment_status=PaymentStatus.FAILED,
                            payment_reference=data_object.get("id"),
                        )
                except Exception as e:
                    logger.error("Error updating order on payment_intent.payment_failed: %s", str(e))

        # 4. Customer Subscription Cancelled / Deleted
        elif event_type == "customer.subscription.deleted":
            stripe_sub_id = data_object.get("id")
            if stripe_sub_id:
                sub = self.db.query(VendorSubscription).filter(
                    VendorSubscription.stripe_subscription_id == stripe_sub_id
                ).first()
                if sub:
                    sub.status = SubscriptionStatus.CANCELED
                    self.db.commit()
                    logger.info("Canceled Vendor ID %d subscription on Stripe deletion", sub.vendor_id)

        return WebhookResponseOut(received=True, event_type=event_type)
