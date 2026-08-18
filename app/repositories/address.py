from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.address import Address
from app.schemas.address import AddressCreate


class AddressRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, address_id: int) -> Optional[Address]:
        """Fetch address by ID."""
        stmt = select(Address).where(Address.id == address_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def unset_all_defaults(self, user_id: int) -> None:
        """Unset default address flag across all user addresses."""
        stmt = select(Address).where(Address.user_id == user_id, Address.is_default.is_(True))
        addresses = self.db.execute(stmt).scalars().all()
        for addr in addresses:
            addr.is_default = False
        self.db.commit()

    def create(self, user_id: int, address_in: AddressCreate) -> Address:
        """Create a new address for a user."""
        if address_in.is_default:
            self.unset_all_defaults(user_id)
        else:
            # If this is user's first address, make it default automatically
            existing_count = len(self.list_by_user(user_id))
            if existing_count == 0:
                address_in.is_default = True

        db_addr = Address(
            user_id=user_id,
            full_name=address_in.full_name.strip(),
            phone_number=address_in.phone_number.strip(),
            address_line1=address_in.address_line1.strip(),
            address_line2=address_in.address_line2.strip() if address_in.address_line2 else None,
            city=address_in.city.strip(),
            state=address_in.state.strip(),
            postal_code=address_in.postal_code.strip(),
            country=address_in.country.strip(),
            is_default=address_in.is_default,
            address_type=address_in.address_type,
        )
        self.db.add(db_addr)
        self.db.commit()
        self.db.refresh(db_addr)
        return db_addr

    def update(self, address: Address, update_data: dict) -> Address:
        """Update address fields."""
        if update_data.get("is_default"):
            self.unset_all_defaults(address.user_id)

        for field, value in update_data.items():
            if hasattr(address, field) and value is not None:
                setattr(address, field, value)
        self.db.commit()
        self.db.refresh(address)
        return address

    def set_default(self, user_id: int, address_id: int) -> Optional[Address]:
        """Make a specific address the default."""
        self.unset_all_defaults(user_id)
        addr = self.get_by_id(address_id)
        if addr and addr.user_id == user_id:
            addr.is_default = True
            self.db.commit()
            self.db.refresh(addr)
            return addr
        return None

    def delete(self, address: Address) -> bool:
        """Delete an address."""
        was_default = address.is_default
        user_id = address.user_id
        self.db.delete(address)
        self.db.commit()

        # If deleted address was default, set first remaining address as default
        if was_default:
            remaining = self.list_by_user(user_id)
            if remaining:
                remaining[0].is_default = True
                self.db.commit()

        return True

    def list_by_user(self, user_id: int) -> List[Address]:
        """List all saved addresses for a user."""
        stmt = (
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.id.desc())
        )
        return list(self.db.execute(stmt).scalars().all())
