import json
import logging
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.dependencies import get_current_active_user
from app.core.security import decode_token
from app.core.websocket import ws_manager
from app.models.user import User
from app.schemas.chat import (
    ChatConversationOut,
    ChatMessageCreate,
    ChatMessageOut,
    ChatUnreadCountOut,
)
from app.schemas.common import APIResponse, MessageResponse
from app.services.chat import ChatService
from app.services.user import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Live Chat & Messaging"])


@router.get(
    "/conversations",
    response_model=APIResponse[List[ChatConversationOut]],
    status_code=status.HTTP_200_OK,
    summary="List active conversation threads",
)
def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[ChatConversationOut]]:
    chat_service = ChatService(db)
    conversations = chat_service.list_conversations(user=current_user)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(conversations)} conversations",
        data=conversations,
    )


@router.get(
    "/history/{other_user_id}",
    response_model=APIResponse[List[ChatMessageOut]],
    status_code=status.HTTP_200_OK,
    summary="Get chat history with another user",
)
def get_chat_history(
    other_user_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[List[ChatMessageOut]]:
    chat_service = ChatService(db)
    messages = chat_service.get_history(
        user=current_user,
        other_user_id=other_user_id,
        skip=skip,
        limit=limit,
    )
    return APIResponse(
        success=True,
        message=f"Retrieved {len(messages)} messages",
        data=messages,
    )


@router.post(
    "/messages",
    response_model=APIResponse[ChatMessageOut],
    status_code=status.HTTP_201_CREATED,
    summary="Send a chat message (REST fallback)",
)
async def send_message(
    msg_in: ChatMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[ChatMessageOut]:
    chat_service = ChatService(db)
    msg_out, _ = await chat_service.send_message(sender=current_user, msg_in=msg_in)
    return APIResponse(
        success=True,
        message="Message sent successfully",
        data=msg_out,
    )


@router.put(
    "/read/{sender_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark messages from sender as read",
)
async def mark_messages_read(
    sender_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    chat_service = ChatService(db)
    count = await chat_service.mark_messages_as_read(user=current_user, sender_id=sender_id)
    return MessageResponse(
        success=True,
        message=f"Marked {count} messages as read",
    )


@router.get(
    "/unread-count",
    response_model=APIResponse[ChatUnreadCountOut],
    status_code=status.HTTP_200_OK,
    summary="Get total unread messages count",
)
def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> APIResponse[ChatUnreadCountOut]:
    chat_service = ChatService(db)
    total = chat_service.get_unread_count(user=current_user)
    return APIResponse(
        success=True,
        message="Unread count retrieved",
        data=ChatUnreadCountOut(total_unread=total),
    )


@router.websocket("/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> None:
    """
    Live real-time WebSocket chat channel with JWT handshake.
    Receives JSON: `{"receiver_id": int, "vendor_id": int, "message": str}`
    Sends JSON events: `{"type": "new_message", ...}` & `{"type": "ack", ...}`
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not payload or payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id_val = payload.get("sub")
    if not user_id_val:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify user exists and is active
    user_service = UserService(db)
    user = user_service.get_user_by_id(int(user_id_val))
    if not user or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = user.id
    await ws_manager.connect(user_id=user_id, websocket=websocket)

    # Notify user connected
    await websocket.send_text(
        json.dumps({"type": "connected", "user_id": user_id, "full_name": user.full_name})
    )

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                # Heartbeat ping / pong
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue

                if "receiver_id" in data and "message" in data:
                    msg_in = ChatMessageCreate(
                        receiver_id=int(data["receiver_id"]),
                        vendor_id=int(data.get("vendor_id", data["receiver_id"])),
                        message=str(data["message"]),
                    )
                    chat_service = ChatService(db)
                    msg_out, is_online = await chat_service.send_message(sender=user, msg_in=msg_in)

                    # Send ACK back to sender
                    ack_packet = {
                        "type": "ack",
                        "status": "delivered" if is_online else "stored",
                        "message": msg_out.model_dump(mode="json"),
                    }
                    await websocket.send_text(json.dumps(ack_packet))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON format"}))
            except Exception as e:
                logger.warning("Error processing WS chat message from user %d: %s", user_id, str(e))
                await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))

    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id=user_id, websocket=websocket)
    except Exception as e:
        logger.error("Unexpected WebSocket error for user %d: %s", user_id, str(e))
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
