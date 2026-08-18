import logging
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.websocket import ws_manager
from app.models.chat import ChatMessage
from app.models.user import User
from app.repositories.chat import ChatRepository
from app.repositories.user import UserRepository
from app.schemas.chat import (
    ChatConversationOut,
    ChatMessageCreate,
    ChatMessageOut,
)

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.user_repo = UserRepository(db)

    def _map_to_out(self, msg: ChatMessage) -> ChatMessageOut:
        sender_name = msg.sender.full_name if msg.sender else f"User {msg.sender_id}"
        receiver_name = msg.receiver.full_name if msg.receiver else f"User {msg.receiver_id}"
        return ChatMessageOut(
            id=msg.id,
            sender_id=msg.sender_id,
            sender_name=sender_name,
            receiver_id=msg.receiver_id,
            receiver_name=receiver_name,
            vendor_id=msg.vendor_id,
            message=msg.message,
            is_read=msg.is_read,
            created_at=msg.created_at,
        )

    async def send_message(self, sender: User, msg_in: ChatMessageCreate) -> Tuple[ChatMessageOut, bool]:
        """
        Persists message and dispatches real-time WebSocket event to receiver if online.
        """
        if sender.id == msg_in.receiver_id:
            raise BadRequestException("You cannot send a message to yourself")

        receiver = self.user_repo.get_by_id(msg_in.receiver_id)
        if not receiver:
            raise NotFoundException(message=f"Recipient user ID {msg_in.receiver_id} not found")

        msg = self.chat_repo.create(
            sender_id=sender.id,
            receiver_id=msg_in.receiver_id,
            vendor_id=msg_in.vendor_id,
            message=msg_in.message,
        )
        msg_out = self._map_to_out(msg)

        # Dispatch real-time WebSocket packet to receiver if online
        payload = {
            "type": "new_message",
            "message": msg_out.model_dump(mode="json"),
        }
        sent = await ws_manager.send_to_user(user_id=msg_in.receiver_id, data=payload)

        return msg_out, sent

    def get_history(
        self,
        user: User,
        other_user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ChatMessageOut]:
        """Fetch chat conversation history with another user."""
        other_user = self.user_repo.get_by_id(other_user_id)
        if not other_user:
            raise NotFoundException(message=f"User with ID {other_user_id} not found")

        messages = self.chat_repo.get_history(
            user1_id=user.id,
            user2_id=other_user_id,
            skip=skip,
            limit=limit,
        )
        return [self._map_to_out(m) for m in messages]

    async def mark_messages_as_read(self, user: User, sender_id: int) -> int:
        """Mark unread messages from sender as read and notify sender if online."""
        count = self.chat_repo.mark_as_read(receiver_id=user.id, sender_id=sender_id)
        if count > 0:
            read_event = {
                "type": "messages_read",
                "reader_id": user.id,
                "count": count,
            }
            await ws_manager.send_to_user(user_id=sender_id, data=read_event)
        return count

    def get_unread_count(self, user: User) -> int:
        """Get total unread messages count for user."""
        return self.chat_repo.get_total_unread_count(user_id=user.id)

    def list_conversations(self, user: User) -> List[ChatConversationOut]:
        """List active conversation threads with last message & unread badge."""
        convs = self.chat_repo.list_conversations(user_id=user.id)
        return [ChatConversationOut(**c) for c in convs]
