"""create vendor profiles table

Revision ID: 2026_08_18_0003
Revises: 2026_08_18_0002
Create Date: 2026-08-18 11:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2026_08_18_0003"
down_revision: Union[str, None] = "2026_08_18_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vendor_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("store_description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("banner_url", sa.String(length=500), nullable=True),
        sa.Column("support_email", sa.String(length=255), nullable=True),
        sa.Column("support_phone", sa.String(length=50), nullable=True),
        sa.Column("business_address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("tax_id", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "SUSPENDED", name="vendor_status_enum", native_enum=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("is_store_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_profiles_id"), "vendor_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_vendor_profiles_user_id"), "vendor_profiles", ["user_id"], unique=True)
    op.create_index(op.f("ix_vendor_profiles_store_name"), "vendor_profiles", ["store_name"], unique=True)
    op.create_index(op.f("ix_vendor_profiles_slug"), "vendor_profiles", ["slug"], unique=True)
    op.create_index(op.f("ix_vendor_profiles_status"), "vendor_profiles", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_vendor_profiles_status"), table_name="vendor_profiles")
    op.drop_index(op.f("ix_vendor_profiles_slug"), table_name="vendor_profiles")
    op.drop_index(op.f("ix_vendor_profiles_store_name"), table_name="vendor_profiles")
    op.drop_index(op.f("ix_vendor_profiles_user_id"), table_name="vendor_profiles")
    op.drop_index(op.f("ix_vendor_profiles_id"), table_name="vendor_profiles")
    op.drop_table("vendor_profiles")
