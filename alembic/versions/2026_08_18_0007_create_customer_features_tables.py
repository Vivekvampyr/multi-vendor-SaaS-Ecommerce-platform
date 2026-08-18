"""create wishlist, addresses, and reviews tables

Revision ID: 2026_08_18_0007
Revises: 2026_08_18_0006
Create Date: 2026-08-18 12:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2026_08_18_0007"
down_revision: Union[str, None] = "2026_08_18_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create wishlist_items table
    op.create_table(
        "wishlist_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_user_product_wishlist"),
    )
    op.create_index(op.f("ix_wishlist_items_id"), "wishlist_items", ["id"], unique=False)
    op.create_index(op.f("ix_wishlist_items_user_id"), "wishlist_items", ["user_id"], unique=False)
    op.create_index(op.f("ix_wishlist_items_product_id"), "wishlist_items", ["product_id"], unique=False)

    # 2. Create addresses table
    op.create_table(
        "addresses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=50), nullable=False),
        sa.Column("address_line1", sa.String(length=255), nullable=False),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False, server_default="USA"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "address_type",
            sa.Enum("HOME", "WORK", "OTHER", name="address_type_enum", native_enum=False),
            nullable=False,
            server_default="HOME",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_addresses_id"), "addresses", ["id"], unique=False)
    op.create_index(op.f("ix_addresses_user_id"), "addresses", ["user_id"], unique=False)

    # 3. Create reviews table
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_verified_purchase", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reviews_id"), "reviews", ["id"], unique=False)
    op.create_index(op.f("ix_reviews_user_id"), "reviews", ["user_id"], unique=False)
    op.create_index(op.f("ix_reviews_product_id"), "reviews", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reviews_product_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_user_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_id"), table_name="reviews")
    op.drop_table("reviews")

    op.drop_index(op.f("ix_addresses_user_id"), table_name="addresses")
    op.drop_index(op.f("ix_addresses_id"), table_name="addresses")
    op.drop_table("addresses")

    op.drop_index(op.f("ix_wishlist_items_product_id"), table_name="wishlist_items")
    op.drop_index(op.f("ix_wishlist_items_user_id"), table_name="wishlist_items")
    op.drop_index(op.f("ix_wishlist_items_id"), table_name="wishlist_items")
    op.drop_table("wishlist_items")
