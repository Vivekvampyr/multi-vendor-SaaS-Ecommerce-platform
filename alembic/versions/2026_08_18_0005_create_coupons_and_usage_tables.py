"""create coupons and coupon_usages tables

Revision ID: 2026_08_18_0005
Revises: 2026_08_18_0004
Create Date: 2026-08-18 12:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2026_08_18_0005"
down_revision: Union[str, None] = "2026_08_18_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create coupons table
    op.create_table(
        "coupons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "discount_type",
            sa.Enum("PERCENTAGE", "FIXED", name="discount_type_enum", native_enum=False),
            nullable=False,
            server_default="PERCENTAGE",
        ),
        sa.Column("discount_value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("max_discount_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("min_order_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("user_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("vendor_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_coupons_id"), "coupons", ["id"], unique=False)
    op.create_index(op.f("ix_coupons_code"), "coupons", ["code"], unique=True)
    op.create_index(op.f("ix_coupons_vendor_id"), "coupons", ["vendor_id"], unique=False)
    op.create_index(op.f("ix_coupons_is_active"), "coupons", ["is_active"], unique=False)

    # 2. Create coupon_usages table
    op.create_table(
        "coupon_usages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("coupon_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("discount_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_coupon_usages_id"), "coupon_usages", ["id"], unique=False)
    op.create_index(op.f("ix_coupon_usages_coupon_id"), "coupon_usages", ["coupon_id"], unique=False)
    op.create_index(op.f("ix_coupon_usages_user_id"), "coupon_usages", ["user_id"], unique=False)
    op.create_index(op.f("ix_coupon_usages_order_id"), "coupon_usages", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_coupon_usages_order_id"), table_name="coupon_usages")
    op.drop_index(op.f("ix_coupon_usages_user_id"), table_name="coupon_usages")
    op.drop_index(op.f("ix_coupon_usages_coupon_id"), table_name="coupon_usages")
    op.drop_index(op.f("ix_coupon_usages_id"), table_name="coupon_usages")
    op.drop_table("coupon_usages")

    op.drop_index(op.f("ix_coupons_is_active"), table_name="coupons")
    op.drop_index(op.f("ix_coupons_vendor_id"), table_name="coupons")
    op.drop_index(op.f("ix_coupons_code"), table_name="coupons")
    op.drop_index(op.f("ix_coupons_id"), table_name="coupons")
    op.drop_table("coupons")
