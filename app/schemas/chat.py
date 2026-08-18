from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ChatMessageCreate(BaseModel):
    receiver_id: int = Field(description="Target recipient User ID")
    vendor_id: int = Field(description="Vendor User ID for this chat context")
    message: str = Field(min_length=1, max_length=2000, description="Message text content")


class ChatMessageOut(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    receiver_id: int
    receiver_name: str
    vendor_id: int
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatConversationOut(BaseModel):
    other_user_id: int
    other_user_name: str
    other_user_role: str
    vendor_id: int
    store_name: Optional[str] = None
    last_message: str
    last_message_at: datetime
    unread_count: int

    model_config = ConfigDict(from_attributes=True)


class ChatUnreadCountOut(BaseModel):
    total_unread: int
