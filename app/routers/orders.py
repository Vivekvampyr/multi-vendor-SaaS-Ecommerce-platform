from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_active_user,
    require_admin,
    require_customer,
    require_vendor,
)
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.order import (
    OrderCheckoutRequest,
    OrderItemOut,
    OrderItemStatusUpdate,
    OrderOut,
    OrderPayRequest,
)
from app.services.order import OrderService

router = APIRouter(prefix="/orders", tags=["Orders & Checkout"])


@router.post(
    "/checkout",
    response_model=APIResponse[OrderOut],
    status_code=status.HTTP_201_CREATED,
    summary="Checkout cart into multi-vendor order (Customer only)",
)
def checkout(
    checkout_in: OrderCheckoutRequest,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> APIResponse[OrderOut]:
    order_service = OrderService(db)
    order = order_service.checkout(customer=customer, request=checkout_in)
    return APIResponse(
        success=True,
        message=f"Order {order.order_number} placed successfully",
        data=OrderOut.model_validate(order),
    )


@router.post(
    "/{order_id}/pay",
    response_model=APIResponse[OrderOut],
    status_code=status.HTTP_200_OK,
    summary="Process / Simulate order payment (Customer only)",
)
@router.post(
    "/{order_id}/simulate-payment",
    response_model=APIResponse[OrderOut],
    status_code=status.HTTP_200_OK,
    summary="Process / Simulate order payment alias (Customer only)",
    include_in_schema=False,
)
def pay_order(
    order_id: int,
    pay_in: Optional[OrderPayRequest] = None,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> APIResponse[OrderOut]:
    if pay_in is None:
        pay_in = OrderPayRequest(simulate_status=PaymentStatus.SUCCESS)
    order_service = OrderService(db)
    paid_order = order_service.process_payment(user=customer, order_id=order_id, request=pay_in)
    return APIResponse(
        success=True,
        message=f"Order payment status: {paid_order.payment_status.value}",
        data=OrderOut.model_validate(paid_order),
    )


@router.get(
    "/my-orders",
    response_model=APIResponse[List[OrderOut]],
    status_code=status.HTTP_200_OK,
    summary="List customer order history (Customer only)",
)
def list_my_orders(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> APIResponse[List[OrderOut]]:
    order_service = OrderService(db)
    orders, total = order_service.list_my_orders(customer_id=customer.id, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(orders)} orders (total: {total})",
        data=[OrderOut.model_validate(o) for o in orders],
    )


@router.get(
    "/vendor/my-orders",
    response_model=APIResponse[List[OrderItemOut]],
    status_code=status.HTTP_200_OK,
    summary="List vendor order items & earnings (Vendor only)",
)
def list_vendor_order_items(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    vendor: User = Depends(require_vendor),
    db: Session = Depends(get_db),
) -> APIResponse[List[OrderItemOut]]:
    order_service = OrderService(db)
    items, total = order_service.list_vendor_order_items(vendor_id=vendor.id, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} vendor order items (total: {total})",
        data=[OrderItemOut.model_validate(i) for i in items],
    )


@router.get(
    "/{order_id}",
    response_model=APIResponse[OrderOut],
    status_code=status.HTTP_200_OK,
    summary="Get order details",
)
def get_order_details(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[OrderOut]:
    order_service = OrderService(db)
    order = order_service.get_order_by_id(user=current_user, order_id=order_id)
    return APIResponse(
        success=True,
        message="Order details retrieved",
        data=OrderOut.model_validate(order),
    )


@router.put(
    "/items/{item_id}/status",
    response_model=APIResponse[OrderItemOut],
    status_code=status.HTTP_200_OK,
    summary="Update item fulfillment status (Vendor owner or Admin)",
)
def update_order_item_status(
    item_id: int,
    status_in: OrderItemStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[OrderItemOut]:
    order_service = OrderService(db)
    updated_item = order_service.update_order_item_status(
        user=current_user,
        item_id=item_id,
        update_in=status_in,
    )
    return APIResponse(
        success=True,
        message=f"Order item status updated to {updated_item.status.value}",
        data=OrderItemOut.model_validate(updated_item),
    )


@router.get(
    "/admin/all",
    response_model=APIResponse[List[OrderOut]],
    status_code=status.HTTP_200_OK,
    summary="List all platform orders (Admin only)",
)
def admin_list_all_orders(
    status_filter: Optional[OrderStatus] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[List[OrderOut]]:
    order_service = OrderService(db)
    orders, total = order_service.admin_list_orders(status=status_filter, skip=skip, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(orders)} platform orders (total: {total})",
        data=[OrderOut.model_validate(o) for o in orders],
    )
