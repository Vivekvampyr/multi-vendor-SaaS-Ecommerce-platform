import enum
from sqlalchemy import Column, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class Order(BaseModel):
    """
    Master Order entity representing customer purchases across multiple vendors.
    """
    __tablename__ = "orders"

    order_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(
            OrderStatus,
            name="order_status_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )
    payment_status = Column(
        Enum(
            PaymentStatus,
            name="payment_status_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )
    payment_method = Column(String(50), default="MOCK_GATEWAY", nullable=False)
    payment_reference = Column(String(150), nullable=True)
    subtotal_amount = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    coupon_id = Column(
        Integer,
        ForeignKey("coupons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tax_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    shipping_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    shipping_address = Column(Text, nullable=True)
    billing_address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    customer = relationship("User", backref="orders")
    coupon = relationship("Coupon")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, number='{self.order_number}', total={self.total_amount}, status={self.status})>"


class OrderItem(BaseModel):
    """
    Line item for an order. Tracks product snapshot, unit price, quantity,
    platform commission calculation, and vendor earnings.
    """
    __tablename__ = "order_items"

    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    commission_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    commission_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    vendor_earnings = Column(Numeric(10, 2), default=0.00, nullable=False)
    status = Column(
        Enum(
            OrderStatus,
            name="order_item_status_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    vendor = relationship("User")

    def __repr__(self) -> str:
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, vendor_id={self.vendor_id}, subtotal={self.subtotal}, earnings={self.vendor_earnings})>"
