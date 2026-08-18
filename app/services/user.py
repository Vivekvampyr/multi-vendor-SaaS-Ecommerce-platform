import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.user import UserPasswordUpdate, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_user_by_id(self, user_id: int) -> User:
        """Fetch user by id or raise NotFoundException."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                message=f"User with ID {user_id} not found",
                details={"user_id": user_id},
            )
        return user

    def update_profile(self, user_id: int, update_in: UserUpdate) -> User:
        """Update full name or phone number for user."""
        user = self.get_user_by_id(user_id)
        update_data = update_in.model_dump(exclude_unset=True)
        if not update_data:
            return user
        return self.user_repo.update(user, update_data)

    def change_password(self, user_id: int, password_in: UserPasswordUpdate) -> User:
        """Verify current password and update to new hashed password."""
        user = self.get_user_by_id(user_id)
        if not verify_password(password_in.current_password, user.hashed_password):
            raise BadRequestException(
                message="Current password does not match",
                details={"field": "current_password"},
            )

        if password_in.current_password == password_in.new_password:
            raise BadRequestException(
                message="New password cannot be the same as the current password",
                details={"field": "new_password"},
            )

        hashed = hash_password(password_in.new_password)
        return self.user_repo.update_password(user, hashed)

    def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
    ) -> Tuple[List[User], int]:
        """List users and total count with optional role filter."""
        users = self.user_repo.list(skip=skip, limit=limit, role=role)
        total = self.user_repo.count(role=role)
        return users, total
