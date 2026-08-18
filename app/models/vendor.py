import enum
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class VendorStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class VendorProfile(BaseModel):
    """
    Vendor Business Profile & Storefront Configuration.
    """
    __tablename__ = "vendor_profiles"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    store_name = Column(String(150), unique=True, index=True, nullable=False)
    slug = Column(String(150), unique=True, index=True, nullable=False)
    store_description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    support_email = Column(String(255), nullable=True)
    support_phone = Column(String(50), nullable=True)
    business_address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    tax_id = Column(String(100), nullable=True)
    status = Column(
        Enum(
            VendorStatus,
            name="vendor_status_enum",
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=VendorStatus.PENDING,
        nullable=False,
        index=True,
    )
    rejection_reason = Column(Text, nullable=True)
    is_store_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="vendor_profile")

    def __repr__(self) -> str:
        return f"<VendorProfile(id={self.id}, store_name='{self.store_name}', status='{self.status}')>"
