import enum
from sqlalchemy import Boolean, Column, Enum, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    VENDOR = "VENDOR"
    CUSTOMER = "CUSTOMER"


class User(BaseModel):
    """
    User entity supporting ADMIN, VENDOR, and CUSTOMER roles.
    """
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(
        Enum(
            UserRole,
            name="user_role_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=UserRole.CUSTOMER,
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    phone_number = Column(String(50), nullable=True)

    # Relationships
    subscription = relationship(
        "VendorSubscription",
        back_populates="vendor",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
