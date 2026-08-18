from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, PaymentStatus


class OrderItemOut(BaseModel):
    id: int
    order_id: int
    product_id: Optional[int] = None
    vendor_id: int
    product_name: str
    product_sku: str
    unit_price: float
    quantity: int
    subtotal: float
    commission_rate: float
    commission_amount: float
    vendor_earnings: float
    status: OrderStatus

    model_config = ConfigDict(from_attributes=True)


class OrderCheckoutRequest(BaseModel):
    shipping_address: str = Field(min_length=5, description="Full delivery street address")
    billing_address: Optional[str] = Field(default=None, description="Billing address if different from shipping")
    payment_method: str = Field(default="MOCK_GATEWAY", description="Payment gateway (e.g. STRIPE, RAZORPAY, COD, MOCK_GATEWAY)")
    coupon_code: Optional[str] = Field(default=None, description="Optional promotional discount code")
    notes: Optional[str] = Field(default=None, description="Order delivery instructions or special notes")


class OrderPayRequest(BaseModel):
    payment_reference: Optional[str] = Field(default=None, description="Transaction identifier from payment gateway")
    simulate_status: PaymentStatus = Field(default=PaymentStatus.SUCCESS, description="Simulated outcome (SUCCESS, FAILED)")


class OrderItemStatusUpdate(BaseModel):
    status: OrderStatus = Field(description="Updated status (PROCESSING, SHIPPED, DELIVERED, CANCELLED)")


class OrderOut(BaseModel):
    id: int
    order_number: str
    customer_id: int
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: str
    payment_reference: Optional[str] = None
    subtotal_amount: float
    discount_amount: float
    tax_amount: float
    shipping_amount: float
    total_amount: float
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    items: List[OrderItemOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
