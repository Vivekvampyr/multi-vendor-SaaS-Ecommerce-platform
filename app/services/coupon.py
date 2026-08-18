from datetime import datetime, timezone
import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.models.coupon import Coupon, DiscountType
from app.models.user import User, UserRole
from app.repositories.coupon import CouponRepository
from app.schemas.coupon import (
    CouponCreate,
    CouponUpdate,
    CouponValidateRequest,
    CouponValidationResult,
)

logger = logging.getLogger(__name__)


class CouponService:
    def __init__(self, db: Session):
        self.db = db
        self.coupon_repo = CouponRepository(db)

    def create_coupon(self, user: User, coupon_in: CouponCreate) -> Coupon:
        """
        Creates a promotional coupon.
        - Admins can create platform-wide coupons or assign to any vendor.
        - Vendors can create coupons scoped strictly to their own storefront.
        """
        if user.role not in (UserRole.ADMIN, UserRole.VENDOR):
            raise ForbiddenException("Only administrators and vendors can create promotional coupons")

        vendor_id = None
        if user.role == UserRole.VENDOR:
            vendor_id = user.id
        elif user.role == UserRole.ADMIN:
            vendor_id = coupon_in.vendor_id

        code = coupon_in.code.strip().upper()
        if self.coupon_repo.exists_by_code(code):
            raise ConflictException(
                message=f"Coupon code '{code}' already exists",
                details={"code": code},
            )

        if coupon_in.discount_type == DiscountType.PERCENTAGE and coupon_in.discount_value > 100:
            raise BadRequestException("Percentage discount cannot exceed 100%")

        if coupon_in.start_date and coupon_in.end_date and coupon_in.end_date < coupon_in.start_date:
            raise BadRequestException("Promotion expiration date cannot be before start date")

        coupon = self.coupon_repo.create(coupon_in, vendor_id=vendor_id)
        logger.info(
            "Created %s coupon '%s' (Type: %s, Value: %s) by User ID %d",
            "Platform" if vendor_id is None else f"Vendor-{vendor_id}",
            coupon.code,
            coupon.discount_type.value,
            str(coupon.discount_value),
            user.id,
        )
        return coupon

    def update_coupon(self, user: User, coupon_id: int, update_in: CouponUpdate) -> Coupon:
        """Update coupon ensuring vendor ownership or admin privileges."""
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundException(message=f"Coupon with ID {coupon_id} not found")

        if user.role != UserRole.ADMIN and coupon.vendor_id != user.id:
            raise ForbiddenException(message="You do not have permission to modify this coupon")

        update_data = update_in.model_dump(exclude_unset=True)
        if not update_data:
            return coupon

        discount_type = update_data.get("discount_type", coupon.discount_type)
        discount_value = update_data.get("discount_value", float(coupon.discount_value))
        if discount_type == DiscountType.PERCENTAGE and discount_value > 100:
            raise BadRequestException("Percentage discount cannot exceed 100%")

        start_date = update_data.get("start_date", coupon.start_date)
        end_date = update_data.get("end_date", coupon.end_date)
        if start_date and end_date and end_date < start_date:
            raise BadRequestException("Promotion expiration date cannot be before start date")

        return self.coupon_repo.update(coupon, update_data)

    def delete_coupon(self, user: User, coupon_id: int) -> bool:
        """Delete coupon from database."""
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundException(message=f"Coupon with ID {coupon_id} not found")

        if user.role != UserRole.ADMIN and coupon.vendor_id != user.id:
            raise ForbiddenException(message="You do not have permission to delete this coupon")

        return self.coupon_repo.delete(coupon)

    def get_coupon_by_id(self, user: User, coupon_id: int) -> Coupon:
        """Fetch single coupon with authorization checks."""
        coupon = self.coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise NotFoundException(message=f"Coupon with ID {coupon_id} not found")

        if user.role != UserRole.ADMIN and coupon.vendor_id != user.id:
            raise ForbiddenException(message="You do not have permission to view this coupon")

        return coupon

    def list_coupons(self, user: User, skip: int = 0, limit: int = 50) -> Tuple[List[Coupon], int]:
        """List coupons scoped to current user role."""
        if user.role == UserRole.ADMIN:
            coupons = self.coupon_repo.list(skip=skip, limit=limit)
            total = self.coupon_repo.count()
        elif user.role == UserRole.VENDOR:
            coupons = self.coupon_repo.list(vendor_id=user.id, skip=skip, limit=limit)
            total = self.coupon_repo.count(vendor_id=user.id)
        else:
            raise ForbiddenException("Customers cannot view internal promotional coupon catalogs")

        return coupons, total

    def validate_coupon(
        self,
        request: CouponValidateRequest,
        user: Optional[User] = None,
    ) -> CouponValidationResult:
        """
        Validates coupon rules and computes real-time discount amounts.
        Never throws unhandled exceptions — returns clear, actionable validation results.
        """
        code = request.code.strip().upper()
        coupon = self.coupon_repo.get_by_code(code)

        if not coupon:
            return CouponValidationResult(
                valid=False,
                code=code,
                discount_type=DiscountType.PERCENTAGE,
                discount_value=0.0,
                discount_amount=0.0,
                subtotal=request.subtotal,
                final_total=request.subtotal,
                message=f"Coupon code '{code}' does not exist",
            )

        if not coupon.is_active:
            return CouponValidationResult(
                valid=False,
                code=code,
                discount_type=coupon.discount_type,
                discount_value=float(coupon.discount_value),
                discount_amount=0.0,
                subtotal=request.subtotal,
                final_total=request.subtotal,
                message="This coupon is no longer active",
            )

        now = datetime.now(timezone.utc)
        start_date_utc = coupon.start_date.replace(tzinfo=timezone.utc) if (coupon.start_date and coupon.start_date.tzinfo is None) else coupon.start_date
        end_date_utc = coupon.end_date.replace(tzinfo=timezone.utc) if (coupon.end_date and coupon.end_date.tzinfo is None) else coupon.end_date

        if start_date_utc and now < start_date_utc:
            return CouponValidationResult(
                valid=False,
                code=code,
                discount_type=coupon.discount_type,
                discount_value=float(coupon.discount_value),
                discount_amount=0.0,
                subtotal=request.subtotal,
                final_total=request.subtotal,
                message="This promotion has not started yet",
            )

        if end_date_utc and now > end_date_utc:
            return CouponValidationResult(
                valid=False,
                code=code,
                discount_type=coupon.discount_type,
                discount_value=float(coupon.discount_value),
                discount_amount=0.0,
                subtotal=request.subtotal,
                final_total=request.subtotal,
                message="This coupon has expired",
            )

        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
            return CouponValidationResult(
                valid=False,
                code=code,
                discount_type=coupon.discount_type,
                discount_value=float(coupon.discount_value),
                discount_amount=0.0,
                subtotal=request.subtotal,
                final_total=request.subtotal,
                message="This coupon has reached its maximum total redemptions",
            )

        if user is not None:
            user_used = self.coupon_repo.get_user_usage_count(coupon.id, user.id)
            if user_used >= coupon.user_limit:
                return CouponValidationResult(
                    valid=False,
                    code=code,
                    discount_type=coupon.discount_type,
                    discount_value=float(coupon.discount_value),
                    discount_amount=0.0,
                    subtotal=request.subtotal,
                    final_total=request.subtotal,
                    message=f"You have already redeemed this coupon the maximum allowed {coupon.user_limit} time(s)",
                )

        if coupon.vendor_id is not None and request.vendor_id and request.vendor_id != coupon.vendor_id:
            return CouponValidationResult(
                valid=False,
                code=code,
                discount_type=coupon.discount_type,
                discount_value=float(coupon.discount_value),
                discount_amount=0.0,
                subtotal=request.subtotal,
                final_total=request.subtotal,
                message="This coupon is valid only for products from a specific vendor store",
            )

        min_required = float(coupon.min_order_amount)
        if request.subtotal < min_required:
            return CouponValidationResult(
                valid=False,
                code=code,
                discount_type=coupon.discount_type,
                discount_value=float(coupon.discount_value),
                discount_amount=0.0,
                subtotal=request.subtotal,
                final_total=request.subtotal,
                message=f"Minimum order subtotal of ${min_required:.2f} required to apply this coupon",
            )

        # Calculate discount amount
        discount_val = float(coupon.discount_value)
        if coupon.discount_type == DiscountType.PERCENTAGE:
            calc_discount = round((request.subtotal * discount_val) / 100.0, 2)
            if coupon.max_discount_amount is not None:
                calc_discount = min(calc_discount, float(coupon.max_discount_amount))
        else:
            calc_discount = min(request.subtotal, discount_val)

        final_total = round(max(0.0, request.subtotal - calc_discount), 2)

        return CouponValidationResult(
            valid=True,
            code=code,
            discount_type=coupon.discount_type,
            discount_value=discount_val,
            discount_amount=calc_discount,
            subtotal=request.subtotal,
            final_total=final_total,
            message="Coupon applied successfully",
        )
