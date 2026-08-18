"""create plans and subscriptions tables

Revision ID: 2026_08_18_0002
Revises: 2026_08_18_0001
Create Date: 2026-08-18 11:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2026_08_18_0002"
down_revision: Union[str, None] = "2026_08_18_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create plans table
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("billing_cycle", sa.String(length=20), nullable=False, server_default="MONTHLY"),
        sa.Column("max_products", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("commission_rate", sa.Numeric(precision=5, scale=2), nullable=False, server_default="20.00"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plans_id"), "plans", ["id"], unique=False)
    op.create_index(op.f("ix_plans_name"), "plans", ["name"], unique=True)
    op.create_index(op.f("ix_plans_slug"), "plans", ["slug"], unique=True)
    op.create_index(op.f("ix_plans_is_active"), "plans", ["is_active"], unique=False)

    # 2. Create vendor_subscriptions table
    op.create_table(
        "vendor_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "TRIALING", "PAST_DUE", "CANCELED", "EXPIRED", name="subscription_status_enum", native_enum=False),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_subscriptions_id"), "vendor_subscriptions", ["id"], unique=False)
    op.create_index(op.f("ix_vendor_subscriptions_vendor_id"), "vendor_subscriptions", ["vendor_id"], unique=True)
    op.create_index(op.f("ix_vendor_subscriptions_plan_id"), "vendor_subscriptions", ["plan_id"], unique=False)
    op.create_index(op.f("ix_vendor_subscriptions_status"), "vendor_subscriptions", ["status"], unique=False)
    op.create_index(op.f("ix_vendor_subscriptions_stripe_subscription_id"), "vendor_subscriptions", ["stripe_subscription_id"], unique=False)
    op.create_index(op.f("ix_vendor_subscriptions_stripe_customer_id"), "vendor_subscriptions", ["stripe_customer_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_vendor_subscriptions_stripe_customer_id"), table_name="vendor_subscriptions")
    op.drop_index(op.f("ix_vendor_subscriptions_stripe_subscription_id"), table_name="vendor_subscriptions")
    op.drop_index(op.f("ix_vendor_subscriptions_status"), table_name="vendor_subscriptions")
    op.drop_index(op.f("ix_vendor_subscriptions_plan_id"), table_name="vendor_subscriptions")
    op.drop_index(op.f("ix_vendor_subscriptions_vendor_id"), table_name="vendor_subscriptions")
    op.drop_index(op.f("ix_vendor_subscriptions_id"), table_name="vendor_subscriptions")
    op.drop_table("vendor_subscriptions")

    op.drop_index(op.f("ix_plans_is_active"), table_name="plans")
    op.drop_index(op.f("ix_plans_slug"), table_name="plans")
    op.drop_index(op.f("ix_plans_name"), table_name="plans")
    op.drop_index(op.f("ix_plans_id"), table_name="plans")
    op.drop_table("plans")
