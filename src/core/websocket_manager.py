"""
WebSocket connection manager for Kinexus AI real-time updates.

Manages WebSocket connections for real-time notifications about:
- Review queue updates
- Assignment changes
- Approval/rejection events
- System-wide notifications
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from core.services.metrics_service import metrics_service

logger = logging.getLogger(__name__)


class NotificationMessage(BaseModel):
    """Structure for WebSocket notification messages."""

    type: str  # 'review_created', 'review_assigned', 'review_approved', etc.
    data: Dict[str, Any]
    timestamp: str
    user_id: Optional[str] = None  # Target user ID (None = broadcast)


class ConnectionInfo(BaseModel):
    """Information about a WebSocket connection."""

    user_id: str
    user_email: str
    user_role: str
    connected_at: datetime
    last_ping: datetime


class WebSocketManager:
    """Manages WebSocket connections and real-time notifications."""

    def __init__(self):
        # Active connections: websocket -> connection info
        self.active_connections: Dict[WebSocket, ConnectionInfo] = {}

        # User connections: user_id -> set of websockets
        self.user_connections: Dict[str, Set[WebSocket]] = {}

        # Room subscriptions: room_name -> set of websockets
        self.room_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(
        self, websocket: WebSocket, user_id: str, user_email: str, user_role: str
    ) -> bool:
        """
        Accept a WebSocket connection and register the user.

        Args:
            websocket: WebSocket connection
            user_id: ID of the authenticated user
            user_email: Email of the user
            user_role: Role of the user

        Returns:
            bool: True if connection successful
        """
        try:
            await websocket.accept()

            # Create connection info
            connection_info = ConnectionInfo(
                user_id=user_id,
                user_email=user_email,
                user_role=user_role,
                connected_at=datetime.utcnow(),
                last_ping=datetime.utcnow(),
            )

            # Register connection
            self.active_connections[websocket] = connection_info

            # Add to user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)

            # Update metrics for active connections
            try:
                metrics_service.websocket_connections.labels(user_role=user_role).inc()
            except Exception:  # pragma: no cover
                logger.exception("Failed to record websocket connection count")

            # Subscribe to default rooms based on user role
            await self._subscribe_to_default_rooms(websocket, user_role)

            # Send welcome message
            await self.send_personal_message(
                websocket,
                {
                    "type": "connection_established",
                    "data": {
                        "user_id": user_id,
                        "connected_at": connection_info.connected_at.isoformat(),
                        "active_connections": len(self.active_connections),
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.info(f"WebSocket connected: {user_email} ({user_role})")
            return True

        except Exception as e:
            logger.error(f"Failed to connect WebSocket for {user_email}: {e}")
            return False

    async def disconnect(self, websocket: WebSocket):
        """
        Handle WebSocket disconnection and cleanup.

        Args:
            websocket: WebSocket connection to disconnect
        """
        if websocket not in self.active_connections:
            return

        connection_info = self.active_connections[websocket]
        user_id = connection_info.user_id

        # Remove from active connections
        del self.active_connections[websocket]

        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # Remove from all room subscriptions
        for room_websockets in self.room_subscriptions.values():
            room_websockets.discard(websocket)

        logger.info(f"WebSocket disconnected: {connection_info.user_email}")

        # Update metrics
        try:
            metrics_service.websocket_connections.labels(
                user_role=connection_info.user_role
            ).dec()
        except Exception:  # pragma: no cover
            logger.exception(
                "Failed to update websocket connection metric on disconnect"
            )

    async def send_personal_message(
        self, websocket: WebSocket, message: Dict[str, Any]
    ):
        """
        Send a message to a specific WebSocket connection.

        Args:
            websocket: Target WebSocket connection
            message: Message to send
        """
        try:
            await websocket.send_text(json.dumps(message))
            self._record_message_metric(message.get("type", "unknown"), "outbound")
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """
        Send a message to all connections of a specific user.

        Args:
            user_id: Target user ID
            message: Message to send
        """
        if user_id not in self.user_connections:
            return

        # Send to all user's connections
        disconnected_websockets = []
        for websocket in self.user_connections[user_id].copy():
            try:
                await websocket.send_text(json.dumps(message))
                self._record_message_metric(message.get("type", "unknown"), "outbound")
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                disconnected_websockets.append(websocket)

        # Clean up disconnected websockets
        for websocket in disconnected_websockets:
            await self.disconnect(websocket)

    async def broadcast_to_room(self, room: str, message: Dict[str, Any]):
        """
        Broadcast a message to all subscribers of a room.

        Args:
            room: Room name
            message: Message to broadcast
        """
        if room not in self.room_subscriptions:
            return

        disconnected_websockets = []
        for websocket in self.room_subscriptions[room].copy():
            try:
                await websocket.send_text(json.dumps(message))
                self._record_message_metric(message.get("type", "unknown"), "outbound")
            except Exception as e:
                logger.error(f"Failed to broadcast to room {room}: {e}")
                disconnected_websockets.append(websocket)

        # Clean up disconnected websockets
        for websocket in disconnected_websockets:
            await self.disconnect(websocket)

    async def broadcast_to_all(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected users.

        Args:
            message: Message to broadcast
        """
        disconnected_websockets = []
        for websocket in list(self.active_connections.keys()):
            try:
                await websocket.send_text(json.dumps(message))
                self._record_message_metric(message.get("type", "unknown"), "outbound")
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")
                disconnected_websockets.append(websocket)

        # Clean up disconnected websockets
        for websocket in disconnected_websockets:
            await self.disconnect(websocket)

    def _record_message_metric(self, message_type: str, direction: str) -> None:
        """Increment Prometheus counters for WebSocket traffic."""
        try:
            metrics_service.websocket_messages.labels(
                message_type=message_type, direction=direction
            ).inc()
        except Exception:  # pragma: no cover
            logger.exception("Failed to record websocket message metric")

    async def subscribe_to_room(self, websocket: WebSocket, room: str):
        """
        Subscribe a WebSocket to a specific room.

        Args:
            websocket: WebSocket connection
            room: Room name to subscribe to
        """
        if room not in self.room_subscriptions:
            self.room_subscriptions[room] = set()

        self.room_subscriptions[room].add(websocket)

        # Send confirmation
        await self.send_personal_message(
            websocket,
            {
                "type": "room_subscribed",
                "data": {"room": room},
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def unsubscribe_from_room(self, websocket: WebSocket, room: str):
        """
        Unsubscribe a WebSocket from a specific room.

        Args:
            websocket: WebSocket connection
            room: Room name to unsubscribe from
        """
        if room in self.room_subscriptions:
            self.room_subscriptions[room].discard(websocket)

        # Send confirmation
        await self.send_personal_message(
            websocket,
            {
                "type": "room_unsubscribed",
                "data": {"room": room},
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def handle_ping(self, websocket: WebSocket):
        """
        Handle ping message to keep connection alive.

        Args:
            websocket: WebSocket connection
        """
        if websocket in self.active_connections:
            self.active_connections[websocket].last_ping = datetime.utcnow()

        await self.send_personal_message(
            websocket,
            {"type": "pong", "data": {}, "timestamp": datetime.utcnow().isoformat()},
        )

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active connections.

        Returns:
            Dict: Connection statistics
        """
        role_counts = {}
        for connection_info in self.active_connections.values():
            role = connection_info.user_role
            role_counts[role] = role_counts.get(role, 0) + 1

        return {
            "total_connections": len(self.active_connections),
            "unique_users": len(self.user_connections),
            "rooms": len(self.room_subscriptions),
            "connections_by_role": role_counts,
        }

    async def _subscribe_to_default_rooms(self, websocket: WebSocket, user_role: str):
        """
        Subscribe user to default rooms based on their role.

        Args:
            websocket: WebSocket connection
            user_role: User's role
        """
        # All users get general notifications
        await self.subscribe_to_room(websocket, "general")

        # Reviewers and above get review notifications
        if user_role in ["reviewer", "lead_reviewer", "admin"]:
            await self.subscribe_to_room(websocket, "reviews")

        # Admins get system notifications
        if user_role == "admin":
            await self.subscribe_to_room(websocket, "admin")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


class NotificationService:
    """Service for sending structured notifications via WebSocket."""

    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager

    async def notify_review_created(self, review_data: Dict[str, Any]):
        """Notify about a new review being created."""
        message = {
            "type": "review_created",
            "data": review_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.ws_manager.broadcast_to_room("reviews", message)

    async def notify_review_assigned(
        self, review_data: Dict[str, Any], assignee_id: str
    ):
        """Notify about a review being assigned."""
        message = {
            "type": "review_assigned",
            "data": review_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Notify the assignee personally
        await self.ws_manager.send_to_user(assignee_id, message)

        # Broadcast to reviews room
        await self.ws_manager.broadcast_to_room("reviews", message)

    async def notify_review_completed(self, review_data: Dict[str, Any]):
        """Notify about a review being completed (approved/rejected)."""
        message = {
            "type": "review_completed",
            "data": review_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.ws_manager.broadcast_to_room("reviews", message)

    async def notify_queue_update(self, queue_stats: Dict[str, Any]):
        """Notify about review queue statistics update."""
        message = {
            "type": "queue_update",
            "data": queue_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.ws_manager.broadcast_to_room("reviews", message)

    async def notify_system_alert(self, alert_data: Dict[str, Any]):
        """Send system-wide alert to all users."""
        message = {
            "type": "system_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.ws_manager.broadcast_to_all(message)

    async def notify_user_mention(self, user_id: str, mention_data: Dict[str, Any]):
        """Notify a specific user about being mentioned."""
        message = {
            "type": "user_mentioned",
            "data": mention_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.ws_manager.send_to_user(user_id, message)


# Global notification service instance
notification_service = NotificationService(websocket_manager)
