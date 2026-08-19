from typing import Optional
from fastapi import APIRouter, Cookie, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartOut
from app.schemas.common import APIResponse, MessageResponse
from app.services.cart import CartService

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


def resolve_session_token(
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
    cookie_session_token: Optional[str] = Cookie(default=None, alias="guest_session_token"),
) -> Optional[str]:
    return x_session_token or cookie_session_token


@router.get(
    "",
    response_model=APIResponse[CartOut],
    status_code=status.HTTP_200_OK,
    summary="Get shopping cart (Customer or Guest)",
)
def get_cart(
    session_token: Optional[str] = Depends(resolve_session_token),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> APIResponse[CartOut]:
    cart_service = CartService(db)
    cart_data = cart_service.get_cart(user=current_user, session_token=session_token)
    return APIResponse(
        success=True,
        message="Shopping cart retrieved",
        data=cart_data,
    )


@router.post(
    "/items",
    response_model=APIResponse[CartOut],
    status_code=status.HTTP_200_OK,
    summary="Add product to cart (Customer or Guest)",
)
def add_item_to_cart(
    item_in: CartItemAdd,
    session_token: Optional[str] = Depends(resolve_session_token),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> APIResponse[CartOut]:
    cart_service = CartService(db)
    updated_cart = cart_service.add_item(user=current_user, session_token=session_token, item_in=item_in)
    return APIResponse(
        success=True,
        message="Item added to cart",
        data=updated_cart,
    )


@router.put(
    "/items/{item_id}",
    response_model=APIResponse[CartOut],
    status_code=status.HTTP_200_OK,
    summary="Update cart item quantity",
)
def update_cart_item(
    item_id: int,
    update_in: CartItemUpdate,
    session_token: Optional[str] = Depends(resolve_session_token),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> APIResponse[CartOut]:
    cart_service = CartService(db)
    updated_cart = cart_service.update_item_quantity(
        user=current_user,
        session_token=session_token,
        item_id=item_id,
        update_in=update_in,
    )
    return APIResponse(
        success=True,
        message="Cart item updated",
        data=updated_cart,
    )


@router.delete(
    "/items/{item_id}",
    response_model=APIResponse[CartOut],
    status_code=status.HTTP_200_OK,
    summary="Remove item from cart",
)
def remove_cart_item(
    item_id: int,
    session_token: Optional[str] = Depends(resolve_session_token),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> APIResponse[CartOut]:
    cart_service = CartService(db)
    updated_cart = cart_service.remove_item(
        user=current_user,
        session_token=session_token,
        item_id=item_id,
    )
    return APIResponse(
        success=True,
        message="Item removed from cart",
        data=updated_cart,
    )


@router.delete(
    "",
    response_model=APIResponse[CartOut],
    status_code=status.HTTP_200_OK,
    summary="Clear all items from shopping cart",
)
def clear_cart(
    session_token: Optional[str] = Depends(resolve_session_token),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> APIResponse[CartOut]:
    cart_service = CartService(db)
    empty_cart = cart_service.clear_cart(user=current_user, session_token=session_token)
    return APIResponse(
        success=True,
        message="Cart cleared successfully",
        data=empty_cart,
    )

