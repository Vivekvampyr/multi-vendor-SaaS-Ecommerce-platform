from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.coupon import Coupon
from app.models.coupon_usage import CouponUsage
from app.schemas.coupon import CouponCreate


class CouponRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, coupon_id: int) -> Optional[Coupon]:
        """Fetch coupon by primary key ID."""
        stmt = select(Coupon).where(Coupon.id == coupon_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> Optional[Coupon]:
        """Fetch coupon by uppercase code."""
        stmt = select(Coupon).where(func.upper(Coupon.code) == code.strip().upper())
        return self.db.execute(stmt).scalar_one_or_none()

    def exists_by_code(self, code: str, exclude_id: Optional[int] = None) -> bool:
        """Check if coupon code is already taken."""
        stmt = select(Coupon.id).where(func.upper(Coupon.code) == code.strip().upper())
        if exclude_id is not None:
            stmt = stmt.where(Coupon.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def create(self, coupon_in: CouponCreate, vendor_id: Optional[int] = None) -> Coupon:
        """Create and persist a new coupon."""
        db_coupon = Coupon(
            code=coupon_in.code.strip().upper(),
            description=coupon_in.description,
            discount_type=coupon_in.discount_type,
            discount_value=coupon_in.discount_value,
            max_discount_amount=coupon_in.max_discount_amount,
            min_order_amount=coupon_in.min_order_amount,
            start_date=coupon_in.start_date,
            end_date=coupon_in.end_date,
            usage_limit=coupon_in.usage_limit,
            used_count=0,
            user_limit=coupon_in.user_limit,
            vendor_id=vendor_id if vendor_id is not None else coupon_in.vendor_id,
            is_active=coupon_in.is_active,
        )
        self.db.add(db_coupon)
        self.db.commit()
        self.db.refresh(db_coupon)
        return db_coupon

    def update(self, coupon: Coupon, update_data: dict) -> Coupon:
        """Update fields on an existing coupon."""
        for field, value in update_data.items():
            if hasattr(coupon, field) and value is not None:
                if field == "code" and isinstance(value, str):
                    value = value.strip().upper()
                setattr(coupon, field, value)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def delete(self, coupon: Coupon) -> bool:
        """Delete coupon from database."""
        self.db.delete(coupon)
        self.db.commit()
        return True

    def list(
        self,
        vendor_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Coupon]:
        """List coupons with optional vendor and active filters."""
        stmt = select(Coupon)
        if vendor_id is not None:
            stmt = stmt.where(Coupon.vendor_id == vendor_id)
        if is_active is not None:
            stmt = stmt.where(Coupon.is_active == is_active)

        stmt = stmt.offset(skip).limit(limit).order_by(Coupon.id.desc())
        return list(self.db.execute(stmt).scalars().all())

    def count(
        self,
        vendor_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count total coupons."""
        stmt = select(func.count(Coupon.id))
        if vendor_id is not None:
            stmt = stmt.where(Coupon.vendor_id == vendor_id)
        if is_active is not None:
            stmt = stmt.where(Coupon.is_active == is_active)
        return self.db.execute(stmt).scalar() or 0

    def increment_used_count(self, coupon: Coupon) -> None:
        """Increment redemption count."""
        coupon.used_count += 1
        self.db.commit()
        self.db.refresh(coupon)

    def record_usage(
        self,
        coupon_id: int,
        user_id: int,
        discount_amount: float,
        order_id: Optional[int] = None,
    ) -> CouponUsage:
        """Log a coupon redemption record."""
        usage = CouponUsage(
            coupon_id=coupon_id,
            user_id=user_id,
            order_id=order_id,
            discount_amount=discount_amount,
        )
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage

    def get_user_usage_count(self, coupon_id: int, user_id: int) -> int:
        """Count times a specific customer has redeemed a coupon."""
        stmt = select(func.count(CouponUsage.id)).where(
            CouponUsage.coupon_id == coupon_id,
            CouponUsage.user_id == user_id,
        )
        return self.db.execute(stmt).scalar() or 0
