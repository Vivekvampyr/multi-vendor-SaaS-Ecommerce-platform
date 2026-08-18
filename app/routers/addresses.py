from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.address import AddressCreate, AddressOut, AddressUpdate
from app.schemas.common import APIResponse, MessageResponse
from app.services.address import AddressService

router = APIRouter(prefix="/addresses", tags=["Customer Addresses"])


@router.get(
    "",
    response_model=APIResponse[List[AddressOut]],
    status_code=status.HTTP_200_OK,
    summary="List saved customer addresses",
)
def list_addresses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[AddressOut]]:
    address_service = AddressService(db)
    addresses = address_service.list_addresses(user=current_user)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(addresses)} saved addresses",
        data=[AddressOut.model_validate(a) for a in addresses],
    )


@router.post(
    "",
    response_model=APIResponse[AddressOut],
    status_code=status.HTTP_201_CREATED,
    summary="Add a new saved address",
)
def create_address(
    address_in: AddressCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[AddressOut]:
    address_service = AddressService(db)
    created = address_service.create_address(user=current_user, address_in=address_in)
    return APIResponse(
        success=True,
        message="Address saved successfully",
        data=AddressOut.model_validate(created),
    )


@router.put(
    "/{address_id}",
    response_model=APIResponse[AddressOut],
    status_code=status.HTTP_200_OK,
    summary="Update saved address",
)
def update_address(
    address_id: int,
    update_in: AddressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[AddressOut]:
    address_service = AddressService(db)
    updated = address_service.update_address(user=current_user, address_id=address_id, update_in=update_in)
    return APIResponse(
        success=True,
        message="Address updated successfully",
        data=AddressOut.model_validate(updated),
    )


@router.put(
    "/{address_id}/default",
    response_model=APIResponse[AddressOut],
    status_code=status.HTTP_200_OK,
    summary="Set address as default",
)
def set_default_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[AddressOut]:
    address_service = AddressService(db)
    updated = address_service.set_default_address(user=current_user, address_id=address_id)
    return APIResponse(
        success=True,
        message="Default address set successfully",
        data=AddressOut.model_validate(updated),
    )


@router.delete(
    "/{address_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete saved address",
)
def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    address_service = AddressService(db)
    address_service.delete_address(user=current_user, address_id=address_id)
    return MessageResponse(
        success=True,
        message="Address deleted successfully",
    )
