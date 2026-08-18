import enum
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class AddressType(str, enum.Enum):
    HOME = "HOME"
    WORK = "WORK"
    OTHER = "OTHER"


class Address(BaseModel):
    """
    Saved Customer Shipping & Billing Address entity.
    """
    __tablename__ = "addresses"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), default="USA", nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    address_type = Column(
        Enum(
            AddressType,
            name="address_type_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=AddressType.HOME,
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="addresses")

    def __repr__(self) -> str:
        return f"<Address(id={self.id}, user_id={self.user_id}, city='{self.city}', default={self.is_default})>"
