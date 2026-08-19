from typing import Optional
from pydantic import BaseModel, Field


class StripeConfigOut(BaseModel):
    is_configured: bool = Field(description="Whether live Stripe keys are configured")
    publishable_key: str = Field(description="Stripe Publishable Key for frontend Stripe.js")
    currency: str = Field(default="usd", description="Platform settlement currency")


class OrderCheckoutSessionRequest(BaseModel):
    order_id: int = Field(description="Unpaid order ID to create a Stripe payment session for")
    success_url: Optional[str] = Field(default=None, description="Custom redirect URL on successful payment")
    cancel_url: Optional[str] = Field(default=None, description="Custom redirect URL on payment cancel")


class SubscriptionCheckoutSessionRequest(BaseModel):
    plan_id: int = Field(description="SaaS Plan ID for vendor subscription")
    success_url: Optional[str] = Field(default=None, description="Custom redirect URL on successful subscription")
    cancel_url: Optional[str] = Field(default=None, description="Custom redirect URL on subscription cancel")


class CheckoutSessionOut(BaseModel):
    session_id: str = Field(description="Stripe Checkout Session ID")
    url: Optional[str] = Field(default=None, description="Hosted Stripe Checkout URL to redirect the user to")
    client_secret: Optional[str] = Field(default=None, description="Stripe client secret if using embedded/custom UI")
    payment_status: Optional[str] = Field(default="unpaid", description="Current payment status of the session")
    mode: str = Field(description="Session mode: 'payment' for orders or 'subscription' for SaaS plans")
    is_simulation: bool = Field(default=False, description="True if operating in mock/fallback simulation mode")


class PaymentIntentOut(BaseModel):
    payment_intent_id: str = Field(description="Stripe Payment Intent ID")
    client_secret: str = Field(description="Client secret for Stripe Elements")
    amount: float = Field(description="Total transaction amount in standard currency unit")
    currency: str = Field(description="Currency code (e.g. usd)")
    status: str = Field(description="Stripe payment intent status")


class WebhookResponseOut(BaseModel):
    received: bool = Field(default=True)
    event_type: str = Field(description="Stripe webhook event type processed")
