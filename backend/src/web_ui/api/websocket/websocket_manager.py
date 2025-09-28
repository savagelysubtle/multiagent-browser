"""
WebSocket Connection Manager for real-time communication.

Provides connection management, message queueing, heartbeat monitoring,
and automatic reconnection support for the React frontend.
"""

import asyncio
import logging
from datetime import datetime

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections with advanced features for production use."""

    def __init__(self):
        # Map user_id to WebSocket connection
        self.active_connections: dict[str, WebSocket] = {}
        # Track connection health
        self.connection_health: dict[str, dict] = {}
        # Message queue for offline users
        self.message_queue: dict[str, list[dict]] = {}
        # Background tasks for heartbeat monitoring
        self.heartbeat_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a user with automatic reconnection support."""
        await websocket.accept()

        # Close existing connection if any
        if user_id in self.active_connections:
            await self.disconnect(user_id)

        self.active_connections[user_id] = websocket
        self.connection_health[user_id] = {
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow(),
            "reconnect_count": self.connection_health.get(user_id, {}).get(
                "reconnect_count", 0
            ),
        }

        # Send queued messages
        await self._send_queued_messages(user_id)

        # Start heartbeat monitoring
        heartbeat_task = asyncio.create_task(self._heartbeat_monitor(user_id))
        self.heartbeat_tasks[user_id] = heartbeat_task

        logger.info(f"User {user_id} connected via WebSocket")

        # Send connection acknowledgment
        await self.send_message(
            user_id,
            {
                "type": "connection_established",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "WebSocket connection established",
            },
        )

    async def disconnect(self, user_id: str):
        """Gracefully disconnect a user."""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket for {user_id}: {e}")
            finally:
                del self.active_connections[user_id]

        # Clean up connection health tracking
        if user_id in self.connection_health:
            del self.connection_health[user_id]

        # Cancel heartbeat task
        if user_id in self.heartbeat_tasks:
            self.heartbeat_tasks[user_id].cancel()
            del self.heartbeat_tasks[user_id]

        logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_message(self, user_id: str, message: dict) -> bool:
        """
        Send message to specific user with queueing for offline users.

        Returns:
            bool: True if message was sent immediately, False if queued
        """
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
                # Connection failed, disconnect and queue message
                await self.disconnect(user_id)

        # Queue message for offline user
        await self._queue_message(user_id, message)
        return False

    async def broadcast_message(
        self, message: dict, exclude_users: list[str] | None = None
    ):
        """Broadcast message to all connected users."""
        exclude_users = exclude_users or []

        disconnected_users = []
        for user_id, websocket in self.active_connections.items():
            if user_id in exclude_users:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {user_id}: {e}")
                disconnected_users.append(user_id)

        # Clean up failed connections
        for user_id in disconnected_users:
            await self.disconnect(user_id)

    async def send_user_notification(
        self,
        user_id: str,
        notification_type: str,
        content: str,
        priority: str = "normal",
    ):
        """Send a structured notification to a specific user."""
        message = {
            "type": "notification",
            "notification_type": notification_type,
            "content": content,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.send_message(user_id, message)

    async def handle_user_message(self, user_id: str, message: dict):
        """Handle incoming message from user."""
        message_type = message.get("type", "unknown")

        if message_type == "pong":
            # Update heartbeat tracking
            if user_id in self.connection_health:
                self.connection_health[user_id]["last_ping"] = datetime.utcnow()
        elif message_type == "ping":
            # Respond to user ping
            await self.send_message(
                user_id, {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
            )
        else:
            # Handle other message types
            logger.info(f"Received message from {user_id}: {message_type}")

    async def _queue_message(self, user_id: str, message: dict):
        """Queue message for offline user."""
        if user_id not in self.message_queue:
            self.message_queue[user_id] = []

        self.message_queue[user_id].append(
            {
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "attempts": 0,
            }
        )

        # Keep only last 100 messages per user
        self.message_queue[user_id] = self.message_queue[user_id][-100:]
        logger.debug(f"Queued message for offline user {user_id}")

    async def _send_queued_messages(self, user_id: str):
        """Send queued messages to reconnected user."""
        if user_id not in self.message_queue:
            return

        messages = self.message_queue.get(user_id, [])
        sent_count = 0

        for msg_data in messages:
            try:
                if user_id in self.active_connections:
                    await self.active_connections[user_id].send_json(
                        {
                            "type": "queued_message",
                            "data": msg_data["message"],
                            "queued_at": msg_data["timestamp"],
                        }
                    )
                    sent_count += 1
                else:
                    break
            except Exception as e:
                logger.error(f"Failed to send queued message: {e}")
                break

        if sent_count == len(messages):
            # All messages sent successfully
            del self.message_queue[user_id]
            logger.info(f"Sent {sent_count} queued messages to {user_id}")
        else:
            # Keep unsent messages
            self.message_queue[user_id] = messages[sent_count:]
            logger.warning(
                f"Only sent {sent_count}/{len(messages)} queued messages to {user_id}"
            )

    async def _heartbeat_monitor(self, user_id: str):
        """Monitor connection health with periodic pings."""
        try:
            while user_id in self.active_connections:
                await asyncio.sleep(30)  # Ping every 30 seconds

                if user_id in self.active_connections:
                    try:
                        await self.send_message(
                            user_id,
                            {
                                "type": "ping",
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )

                        # Check if connection is still healthy
                        if user_id in self.connection_health:
                            last_ping = self.connection_health[user_id]["last_ping"]
                            time_since_ping = (
                                datetime.utcnow() - last_ping
                            ).total_seconds()

                            # If no response in 2 minutes, consider connection dead
                            if time_since_ping > 120:
                                logger.warning(
                                    f"No heartbeat response from {user_id} for {time_since_ping}s"
                                )
                                await self.disconnect(user_id)
                                break

                    except Exception as e:
                        logger.error(f"Heartbeat failed for {user_id}: {e}")
                        await self.disconnect(user_id)
                        break

        except asyncio.CancelledError:
            logger.debug(f"Heartbeat monitor cancelled for {user_id}")
        except Exception as e:
            logger.error(f"Heartbeat monitor error for {user_id}: {e}")

    def get_connection_stats(self) -> dict:
        """Get connection statistics for monitoring."""
        active_count = len(self.active_connections)
        queued_messages = sum(len(queue) for queue in self.message_queue.values())

        return {
            "active_connections": active_count,
            "queued_messages": queued_messages,
            "users_with_queued_messages": len(self.message_queue),
            "connection_health": {
                user_id: {
                    "connected_duration": (
                        datetime.utcnow() - health["connected_at"]
                    ).total_seconds(),
                    "last_ping_age": (
                        datetime.utcnow() - health["last_ping"]
                    ).total_seconds(),
                    "reconnect_count": health.get("reconnect_count", 0),
                }
                for user_id, health in self.connection_health.items()
            },
        }

    async def cleanup_stale_connections(self):
        """Clean up stale connections and old queued messages."""
        # Remove old queued messages (older than 24 hours)
        cutoff_time = datetime.utcnow().timestamp() - (24 * 60 * 60)

        for user_id in list(self.message_queue.keys()):
            if user_id in self.message_queue:
                # Filter out old messages
                fresh_messages = [
                    msg
                    for msg in self.message_queue[user_id]
                    if datetime.fromisoformat(msg["timestamp"]).timestamp()
                    > cutoff_time
                ]

                if fresh_messages:
                    self.message_queue[user_id] = fresh_messages
                else:
                    del self.message_queue[user_id]

        logger.info("Completed WebSocket cleanup")


# Global connection manager instance
ws_manager = ConnectionManager()
