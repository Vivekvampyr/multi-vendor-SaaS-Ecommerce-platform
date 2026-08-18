import logging
from typing import List
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.address import Address
from app.models.user import User, UserRole
from app.repositories.address import AddressRepository
from app.schemas.address import AddressCreate, AddressUpdate

logger = logging.getLogger(__name__)


class AddressService:
    def __init__(self, db: Session):
        self.db = db
        self.address_repo = AddressRepository(db)

    def create_address(self, user: User, address_in: AddressCreate) -> Address:
        """Create new saved address for user."""
        return self.address_repo.create(user_id=user.id, address_in=address_in)

    def update_address(self, user: User, address_id: int, update_in: AddressUpdate) -> Address:
        """Update address fields."""
        addr = self.address_repo.get_by_id(address_id)
        if not addr:
            raise NotFoundException(message=f"Address with ID {address_id} not found")

        if user.role != UserRole.ADMIN and addr.user_id != user.id:
            raise ForbiddenException(message="You do not have permission to modify this address")

        update_data = update_in.model_dump(exclude_unset=True)
        return self.address_repo.update(addr, update_data)

    def delete_address(self, user: User, address_id: int) -> bool:
        """Delete saved address."""
        addr = self.address_repo.get_by_id(address_id)
        if not addr:
            raise NotFoundException(message=f"Address with ID {address_id} not found")

        if user.role != UserRole.ADMIN and addr.user_id != user.id:
            raise ForbiddenException(message="You do not have permission to delete this address")

        return self.address_repo.delete(addr)

    def set_default_address(self, user: User, address_id: int) -> Address:
        """Set an address as the default."""
        addr = self.address_repo.get_by_id(address_id)
        if not addr or (user.role != UserRole.ADMIN and addr.user_id != user.id):
            raise NotFoundException(message="Address not found")

        updated = self.address_repo.set_default(user_id=user.id, address_id=address_id)
        if not updated:
            raise NotFoundException(message="Failed to set default address")
        return updated

    def list_addresses(self, user: User) -> List[Address]:
        """List all saved addresses for user."""
        return self.address_repo.list_by_user(user_id=user.id)
