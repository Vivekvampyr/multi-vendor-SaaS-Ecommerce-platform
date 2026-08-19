from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_active_user,
    require_customer,
    require_vendor,
)
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.payment import (
    CheckoutSessionOut,
    OrderCheckoutSessionRequest,
    PaymentIntentOut,
    StripeConfigOut,
    SubscriptionCheckoutSessionRequest,
    WebhookResponseOut,
)
from app.services.stripe_service import StripeService

router = APIRouter(prefix="/payments", tags=["Stripe & Payments"])


@router.get(
    "/config",
    response_model=APIResponse[StripeConfigOut],
    status_code=status.HTTP_200_OK,
    summary="Get Stripe public configuration",
)
def get_stripe_config(
    db: Session = Depends(get_db),
) -> APIResponse[StripeConfigOut]:
    stripe_service = StripeService(db)
    config = stripe_service.get_config()
    return APIResponse(
        success=True,
        message="Stripe configuration retrieved",
        data=config,
    )


@router.post(
    "/checkout-session/order",
    response_model=APIResponse[CheckoutSessionOut],
    status_code=status.HTTP_200_OK,
    summary="Create Stripe Checkout session for customer order (Customer only)",
)
def create_order_checkout_session(
    request: OrderCheckoutSessionRequest,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> APIResponse[CheckoutSessionOut]:
    stripe_service = StripeService(db)
    session_out = stripe_service.create_order_checkout_session(
        user=customer,
        order_id=request.order_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )
    return APIResponse(
        success=True,
        message="Stripe order checkout session created",
        data=session_out,
    )


@router.post(
    "/checkout-session/subscription",
    response_model=APIResponse[CheckoutSessionOut],
    status_code=status.HTTP_200_OK,
    summary="Create Stripe Checkout session for vendor SaaS plan (Vendor only)",
)
def create_subscription_checkout_session(
    request: SubscriptionCheckoutSessionRequest,
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[CheckoutSessionOut]:
    stripe_service = StripeService(db)
    session_out = stripe_service.create_subscription_checkout_session(
        vendor=vendor,
        plan_id=request.plan_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )
    return APIResponse(
        success=True,
        message="Stripe subscription checkout session created",
        data=session_out,
    )


@router.post(
    "/payment-intent/order/{order_id}",
    response_model=APIResponse[PaymentIntentOut],
    status_code=status.HTTP_200_OK,
    summary="Create Stripe PaymentIntent for order",
)
def create_order_payment_intent(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[PaymentIntentOut]:
    stripe_service = StripeService(db)
    intent_out = stripe_service.create_order_payment_intent(user=current_user, order_id=order_id)
    return APIResponse(
        success=True,
        message="PaymentIntent created successfully",
        data=intent_out,
    )


@router.post(
    "/webhook",
    response_model=WebhookResponseOut,
    status_code=status.HTTP_200_OK,
    summary="Public Stripe Webhook Event Listener",
)
async def stripe_webhook_endpoint(
    request: Request,
    stripe_signature: str = Header(default=None, alias="stripe-signature"),
    db: Session = Depends(get_db),
) -> WebhookResponseOut:
    payload = await request.body()
    stripe_service = StripeService(db)
    result = stripe_service.handle_webhook(payload=payload, sig_header=stripe_signature)
    return result
