from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.schemas.user import UserCreate


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch a user by primary key ID."""
        stmt = select(User).where(User.id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by unique email address (case-insensitive)."""
        stmt = select(User).where(func.lower(User.email) == email.lower().strip())
        return self.db.execute(stmt).scalar_one_or_none()

    def exists_by_email(self, email: str) -> bool:
        """Check if an email is already registered."""
        stmt = select(User.id).where(func.lower(User.email) == email.lower().strip())
        return self.db.execute(stmt).first() is not None

    def create(self, user_in: UserCreate, hashed_password: str) -> User:
        """Create and persist a new user."""
        db_user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hashed_password,
            full_name=user_in.full_name.strip(),
            role=user_in.role,
            phone_number=user_in.phone_number.strip() if user_in.phone_number else None,
            is_active=True,
            is_verified=False,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update(self, user: User, update_data: dict) -> User:
        """Update fields on an existing user instance."""
        for field, value in update_data.items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password(self, user: User, hashed_password: str) -> User:
        """Update a user's hashed password."""
        user.hashed_password = hashed_password
        self.db.commit()
        self.db.refresh(user)
        return user

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
    ) -> List[User]:
        """List users with optional role filter and pagination."""
        stmt = select(User)
        if role is not None:
            stmt = stmt.where(User.role == role)
        stmt = stmt.offset(skip).limit(limit).order_by(User.id.asc())
        return list(self.db.execute(stmt).scalars().all())

    def count(self, role: Optional[UserRole] = None) -> int:
        """Count total users with optional role filter."""
        stmt = select(func.count(User.id))
        if role is not None:
            stmt = stmt.where(User.role == role)
        return self.db.execute(stmt).scalar() or 0

    def delete(self, user: User) -> bool:
        """Delete a user entity."""
        self.db.delete(user)
        self.db.commit()
        return True
