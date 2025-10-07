"""
WebSocket router for Kinexus AI real-time updates.

Handles WebSocket connections for real-time notifications about
review queue changes, assignments, and system events.
"""

import asyncio
import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from api.dependencies import get_db
from database.models import User
from core.config import settings
from core.websocket_manager import websocket_manager, notification_service

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_user_from_token(token: str, db: Session) -> User:
    """
    Authenticate user from WebSocket token.

    Args:
        token: JWT token
        db: Database session

    Returns:
        User: Authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Decode JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        # Get user from database
        from uuid import UUID
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return user

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications.

    Clients connect with: ws://localhost:8000/api/ws/notifications?token=JWT_TOKEN

    Message types sent to client:
    - connection_established: Confirmation of successful connection
    - review_created: New review added to queue
    - review_assigned: Review assigned to user
    - review_completed: Review approved/rejected
    - queue_update: Queue statistics update
    - system_alert: System-wide notifications
    - user_mentioned: User mentioned in feedback
    - room_subscribed/unsubscribed: Room subscription confirmations
    - pong: Response to ping messages

    Message types received from client:
    - ping: Keep-alive message
    - subscribe: Subscribe to additional rooms
    - unsubscribe: Unsubscribe from rooms
    """
    try:
        # Authenticate user
        user = await get_user_from_token(token, db)

        # Connect to WebSocket manager
        connected = await websocket_manager.connect(
            websocket=websocket,
            user_id=str(user.id),
            user_email=user.email,
            user_role=user.role.value
        )

        if not connected:
            logger.error(f"Failed to connect WebSocket for user {user.email}")
            return

        try:
            # Handle incoming messages
            while True:
                # Wait for message from client
                data = await websocket.receive_text()

                try:
                    message = json.loads(data)
                    message_type = message.get("type")

                    if message_type == "ping":
                        await websocket_manager.handle_ping(websocket)

                    elif message_type == "subscribe":
                        room = message.get("room")
                        if room:
                            await websocket_manager.subscribe_to_room(websocket, room)

                    elif message_type == "unsubscribe":
                        room = message.get("room")
                        if room:
                            await websocket_manager.unsubscribe_from_room(websocket, room)

                    elif message_type == "get_stats":
                        # Send connection statistics
                        stats = await websocket_manager.get_connection_stats()
                        await websocket_manager.send_personal_message(websocket, {
                            "type": "connection_stats",
                            "data": stats,
                            "timestamp": message.get("timestamp", "")
                        })

                    else:
                        logger.warning(f"Unknown message type: {message_type}")

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received from {user.email}")
                except Exception as e:
                    logger.error(f"Error processing message from {user.email}: {e}")

        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {user.email}")
        except Exception as e:
            logger.error(f"WebSocket error for {user.email}: {e}")
        finally:
            await websocket_manager.disconnect(websocket)

    except HTTPException:
        # Authentication failed
        await websocket.close(code=4001, reason="Authentication failed")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=4000, reason="Connection error")


@router.get("/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns connection counts and active rooms for monitoring.
    """
    return await websocket_manager.get_connection_stats()


@router.post("/broadcast")
async def broadcast_message(
    message_data: Dict[str, Any],
    current_user: User = Depends(lambda: None)  # TODO: Add admin dependency
):
    """
    Broadcast a message to all connected users (admin only).

    This is useful for system announcements and maintenance notifications.
    """
    # TODO: Add proper admin authentication
    # For now, just return the message structure for testing

    message = {
        "type": "admin_broadcast",
        "data": message_data,
        "timestamp": "2025-09-27T12:00:00Z"
    }

    # await websocket_manager.broadcast_to_all(message)

    return {"status": "broadcasted", "message": message}


@router.post("/test-notification")
async def test_notification(
    notification_type: str,
    user_id: str = None
):
    """
    Test endpoint for triggering notifications during development.

    This will be removed in production.
    """
    test_data = {
        "id": "test-123",
        "title": "Test Notification",
        "message": f"This is a test {notification_type} notification"
    }

    if notification_type == "review_created":
        await notification_service.notify_review_created(test_data)
    elif notification_type == "review_assigned" and user_id:
        await notification_service.notify_review_assigned(test_data, user_id)
    elif notification_type == "review_completed":
        await notification_service.notify_review_completed(test_data)
    elif notification_type == "system_alert":
        await notification_service.notify_system_alert(test_data)
    elif notification_type == "queue_update":
        await notification_service.notify_queue_update({
            "pending": 5,
            "in_review": 3,
            "completed_today": 12
        })
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification type"
        )

    return {"status": "sent", "type": notification_type, "data": test_data}