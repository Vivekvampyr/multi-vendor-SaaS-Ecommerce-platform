from typing import Dict, List, Optional
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.chat import ChatMessage
from app.models.user import User
from app.models.vendor import VendorProfile


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, message_id: int) -> Optional[ChatMessage]:
        """Fetch chat message by ID with sender and receiver eager-loaded."""
        stmt = (
            select(ChatMessage)
            .options(joinedload(ChatMessage.sender), joinedload(ChatMessage.receiver))
            .where(ChatMessage.id == message_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        sender_id: int,
        receiver_id: int,
        vendor_id: int,
        message: str,
    ) -> ChatMessage:
        """Persist a new chat message."""
        msg = ChatMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            vendor_id=vendor_id,
            message=message.strip(),
            is_read=False,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return self.get_by_id(msg.id) or msg

    def get_history(
        self,
        user1_id: int,
        user2_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ChatMessage]:
        """Fetch chat history between two users in chronological order."""
        stmt = (
            select(ChatMessage)
            .options(joinedload(ChatMessage.sender), joinedload(ChatMessage.receiver))
            .where(
                or_(
                    (ChatMessage.sender_id == user1_id) & (ChatMessage.receiver_id == user2_id),
                    (ChatMessage.sender_id == user2_id) & (ChatMessage.receiver_id == user1_id),
                )
            )
            .order_by(ChatMessage.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def mark_as_read(self, receiver_id: int, sender_id: int) -> int:
        """Mark all unread messages from sender to receiver as read."""
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.receiver_id == receiver_id,
                ChatMessage.sender_id == sender_id,
                ChatMessage.is_read.is_(False),
            )
        )
        unread_msgs = self.db.execute(stmt).scalars().all()
        count = len(unread_msgs)
        for msg in unread_msgs:
            msg.is_read = True
        if count > 0:
            self.db.commit()
        return count

    def get_total_unread_count(self, user_id: int) -> int:
        """Get count of all unread messages sent to user."""
        stmt = (
            select(func.count(ChatMessage.id))
            .where(ChatMessage.receiver_id == user_id, ChatMessage.is_read.is_(False))
        )
        return self.db.execute(stmt).scalar() or 0

    def list_conversations(self, user_id: int) -> List[Dict]:
        """
        List distinct conversations for user, including last message and unread count.
        """
        # 1. Find all distinct conversational peers
        stmt = (
            select(
                case(
                    (ChatMessage.sender_id == user_id, ChatMessage.receiver_id),
                    else_=ChatMessage.sender_id,
                ).label("other_user_id"),
                func.max(ChatMessage.id).label("last_msg_id"),
            )
            .where(or_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == user_id))
            .group_by("other_user_id")
        )
        rows = self.db.execute(stmt).all()
        conversations = []

        for other_user_id, last_msg_id in rows:
            last_msg = self.get_by_id(last_msg_id)
            if not last_msg:
                continue

            other_user = self.db.execute(select(User).where(User.id == other_user_id)).scalar_one_or_none()
            if not other_user:
                continue

            # Unread messages from this specific peer
            unread_stmt = select(func.count(ChatMessage.id)).where(
                ChatMessage.receiver_id == user_id,
                ChatMessage.sender_id == other_user_id,
                ChatMessage.is_read.is_(False),
            )
            unread_count = self.db.execute(unread_stmt).scalar() or 0

            # Store name if peer is a vendor
            store_name = None
            vendor_profile = self.db.execute(
                select(VendorProfile).where(VendorProfile.user_id == last_msg.vendor_id)
            ).scalar_one_or_none()
            if vendor_profile:
                store_name = vendor_profile.store_name

            conversations.append({
                "other_user_id": other_user.id,
                "other_user_name": other_user.full_name,
                "other_user_role": other_user.role.value,
                "vendor_id": last_msg.vendor_id,
                "store_name": store_name,
                "last_message": last_msg.message,
                "last_message_at": last_msg.created_at,
                "unread_count": unread_count,
            })

        # Sort conversations by last message timestamp descending
        conversations.sort(key=lambda c: c["last_message_at"], reverse=True)
        return conversations
