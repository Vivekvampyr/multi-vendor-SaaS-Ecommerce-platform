"""create cart and orders tables

Revision ID: 2026_08_18_0006
Revises: 2026_08_18_0005
Create Date: 2026-08-18 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2026_08_18_0006"
down_revision: Union[str, None] = "2026_08_18_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create carts table
    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("session_token", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_carts_id"), "carts", ["id"], unique=False)
    op.create_index(op.f("ix_carts_user_id"), "carts", ["user_id"], unique=False)
    op.create_index(op.f("ix_carts_session_token"), "carts", ["session_token"], unique=False)

    # 2. Create cart_items table
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("price_at_addition", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cart_items_id"), "cart_items", ["id"], unique=False)
    op.create_index(op.f("ix_cart_items_cart_id"), "cart_items", ["cart_id"], unique=False)
    op.create_index(op.f("ix_cart_items_product_id"), "cart_items", ["product_id"], unique=False)
    op.create_index(op.f("ix_cart_items_vendor_id"), "cart_items", ["vendor_id"], unique=False)

    # 3. Create orders table
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_number", sa.String(length=50), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PAID", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED", "REFUNDED", name="order_status_enum", native_enum=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "payment_status",
            sa.Enum("PENDING", "SUCCESS", "FAILED", "REFUNDED", name="payment_status_enum", native_enum=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("payment_method", sa.String(length=50), nullable=False, server_default="MOCK_GATEWAY"),
        sa.Column("payment_reference", sa.String(length=150), nullable=True),
        sa.Column("subtotal_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("coupon_id", sa.Integer(), nullable=True),
        sa.Column("tax_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("shipping_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("shipping_address", sa.Text(), nullable=True),
        sa.Column("billing_address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_id"), "orders", ["id"], unique=False)
    op.create_index(op.f("ix_orders_order_number"), "orders", ["order_number"], unique=True)
    op.create_index(op.f("ix_orders_customer_id"), "orders", ["customer_id"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(op.f("ix_orders_payment_status"), "orders", ["payment_status"], unique=False)
    op.create_index(op.f("ix_orders_coupon_id"), "orders", ["coupon_id"], unique=False)

    # 4. Create order_items table
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("product_sku", sa.String(length=100), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("commission_rate", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("commission_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("vendor_earnings", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PAID", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED", "REFUNDED", name="order_item_status_enum", native_enum=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vendor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_id"), "order_items", ["id"], unique=False)
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_product_id"), "order_items", ["product_id"], unique=False)
    op.create_index(op.f("ix_order_items_vendor_id"), "order_items", ["vendor_id"], unique=False)
    op.create_index(op.f("ix_order_items_status"), "order_items", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_order_items_status"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_vendor_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_id"), table_name="order_items")
    op.drop_table("order_items")

    op.drop_index(op.f("ix_orders_coupon_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_payment_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_customer_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_order_number"), table_name="orders")
    op.drop_index(op.f("ix_orders_id"), table_name="orders")
    op.drop_table("orders")

    op.drop_index(op.f("ix_cart_items_vendor_id"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_product_id"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_cart_id"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_id"), table_name="cart_items")
    op.drop_table("cart_items")

    op.drop_index(op.f("ix_carts_session_token"), table_name="carts")
    op.drop_index(op.f("ix_carts_user_id"), table_name="carts")
    op.drop_index(op.f("ix_carts_id"), table_name="carts")
    op.drop_table("carts")
