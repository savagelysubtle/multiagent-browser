"""
Google Agent-to-Agent (A2A) Interface.

Prepares the infrastructure for Google A2A integration while maintaining
compatibility with the existing agent orchestrator.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class A2AMessageType(Enum):
    """Types of A2A messages."""

    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    ERROR = "error"


class A2AMessage:
    """
    Represents a message in the Google A2A protocol.

    This is a preparation structure that can be extended when
    Google A2A specification is finalized.
    """

    def __init__(
        self,
        message_type: A2AMessageType,
        sender_id: str,
        receiver_id: str,
        payload: dict[str, Any],
        conversation_id: str | None = None,
        message_id: str | None = None,
    ):
        self.message_type = message_type
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.payload = payload
        self.conversation_id = conversation_id
        self.message_id = message_id or f"msg_{datetime.utcnow().timestamp()}"
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "conversation_id": self.conversation_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "A2AMessage":
        """Create message from dictionary."""
        message = cls(
            message_type=A2AMessageType(data["message_type"]),
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            payload=data["payload"],
            conversation_id=data.get("conversation_id"),
            message_id=data.get("message_id"),
        )
        if "timestamp" in data:
            message.timestamp = datetime.fromisoformat(data["timestamp"])
        return message


class GoogleA2AInterface:
    """
    Interface for Google Agent-to-Agent communication.

    This is a preparation implementation that provides the structure
    for future Google A2A integration while working with the current
    orchestrator system.
    """

    def __init__(self, orchestrator=None):
        """
        Initialize the A2A interface.

        Args:
            orchestrator: The agent orchestrator instance
        """
        self.orchestrator = orchestrator
        self.agent_id = "web-ui-orchestrator"
        self.registered_agents: dict[str, dict[str, Any]] = {}
        self.conversation_history: dict[str, list[A2AMessage]] = {}
        self.enabled = False  # Disabled by default until Google A2A is available

    def register_local_agent(self, agent_id: str, capabilities: dict[str, Any]):
        """
        Register a local agent for A2A communication.

        Args:
            agent_id: Unique identifier for the agent
            capabilities: Agent capabilities and metadata
        """
        self.registered_agents[agent_id] = {
            "id": agent_id,
            "capabilities": capabilities,
            "registered_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        logger.info(f"Registered local agent for A2A: {agent_id}")

    async def send_message(self, message: A2AMessage) -> bool:
        """
        Send an A2A message.

        Args:
            message: The A2A message to send

        Returns:
            bool: True if message was sent successfully
        """
        try:
            if not self.enabled:
                logger.debug(f"A2A not enabled, message queued: {message.message_id}")
                return self._queue_message(message)

            # Future implementation will use Google A2A protocol
            logger.info(f"A2A message sent: {message.message_id}")

            # Store in conversation history
            if message.conversation_id:
                if message.conversation_id not in self.conversation_history:
                    self.conversation_history[message.conversation_id] = []
                self.conversation_history[message.conversation_id].append(message)

            return True

        except Exception as e:
            logger.error(f"Failed to send A2A message: {e}")
            return False

    async def receive_message(self, message_data: dict[str, Any]) -> A2AMessage | None:
        """
        Receive and process an A2A message.

        Args:
            message_data: Raw message data from A2A protocol

        Returns:
            Processed A2A message or None if invalid
        """
        try:
            message = A2AMessage.from_dict(message_data)

            # Store in conversation history
            if message.conversation_id:
                if message.conversation_id not in self.conversation_history:
                    self.conversation_history[message.conversation_id] = []
                self.conversation_history[message.conversation_id].append(message)

            # Route message based on type
            await self._route_message(message)

            return message

        except Exception as e:
            logger.error(f"Failed to process A2A message: {e}")
            return None

    async def _route_message(self, message: A2AMessage):
        """
        Route A2A message to appropriate handler.

        Args:
            message: The A2A message to route
        """
        try:
            if message.message_type == A2AMessageType.TASK_REQUEST:
                await self._handle_task_request(message)
            elif message.message_type == A2AMessageType.CAPABILITY_QUERY:
                await self._handle_capability_query(message)
            elif message.message_type == A2AMessageType.STATUS_UPDATE:
                await self._handle_status_update(message)
            else:
                logger.warning(f"Unhandled A2A message type: {message.message_type}")

        except Exception as e:
            logger.error(f"Failed to route A2A message: {e}")

    async def _handle_task_request(self, message: A2AMessage):
        """
        Handle incoming task request from another agent.

        Args:
            message: Task request message
        """
        try:
            if not self.orchestrator:
                logger.error("No orchestrator available for task request")
                return

            # Extract task details from message payload
            task_details = message.payload
            agent_type = task_details.get("agent_type")
            action = task_details.get("action")
            payload = task_details.get("payload", {})

            # Submit to local orchestrator
            # This would need proper user context in real implementation
            task_id = await self.orchestrator.submit_task(
                user_id="a2a_user",  # Special user for A2A requests
                agent_type=agent_type,
                action=action,
                payload=payload,
            )

            # Send response
            response = A2AMessage(
                message_type=A2AMessageType.TASK_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                conversation_id=message.conversation_id,
                payload={
                    "task_id": task_id,
                    "status": "accepted",
                    "original_message_id": message.message_id,
                },
            )

            await self.send_message(response)

        except Exception as e:
            logger.error(f"Failed to handle task request: {e}")

    async def _handle_capability_query(self, message: A2AMessage):
        """
        Handle capability query from another agent.

        Args:
            message: Capability query message
        """
        try:
            capabilities = {
                "agent_id": self.agent_id,
                "agent_type": "orchestrator",
                "available_agents": [],
                "supported_actions": [],
            }

            if self.orchestrator:
                capabilities["available_agents"] = (
                    self.orchestrator.get_available_agents()
                )

            # Send response
            response = A2AMessage(
                message_type=A2AMessageType.CAPABILITY_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                conversation_id=message.conversation_id,
                payload=capabilities,
            )

            await self.send_message(response)

        except Exception as e:
            logger.error(f"Failed to handle capability query: {e}")

    async def _handle_status_update(self, message: A2AMessage):
        """
        Handle status update from another agent.

        Args:
            message: Status update message
        """
        try:
            status_info = message.payload
            logger.info(
                f"Received status update from {message.sender_id}: {status_info}"
            )

            # Future implementation could update local task status
            # or forward to appropriate components

        except Exception as e:
            logger.error(f"Failed to handle status update: {e}")

    def _queue_message(self, message: A2AMessage) -> bool:
        """
        Queue message for later sending when A2A is enabled.

        Args:
            message: Message to queue

        Returns:
            bool: True if queued successfully
        """
        # In a real implementation, this would store messages
        # for later transmission when A2A becomes available
        logger.debug(
            f"Message queued for future A2A transmission: {message.message_id}"
        )
        return True

    def get_conversation_history(self, conversation_id: str) -> list[A2AMessage]:
        """
        Get conversation history for a specific conversation.

        Args:
            conversation_id: ID of the conversation

        Returns:
            List of messages in the conversation
        """
        return self.conversation_history.get(conversation_id, [])

    def get_agent_capabilities(self) -> dict[str, Any]:
        """
        Get capabilities of this A2A interface.

        Returns:
            Dict describing interface capabilities
        """
        return {
            "interface_version": "0.1.0",
            "protocol": "google_a2a_preparation",
            "agent_id": self.agent_id,
            "supported_message_types": [msg_type.value for msg_type in A2AMessageType],
            "features": [
                "Task routing",
                "Capability discovery",
                "Status updates",
                "Conversation history",
            ],
            "status": "enabled" if self.enabled else "preparation_mode",
        }

    def enable_a2a(self):
        """Enable A2A communication (when Google A2A becomes available)."""
        self.enabled = True
        logger.info("Google A2A interface enabled")

    def disable_a2a(self):
        """Disable A2A communication."""
        self.enabled = False
        logger.info("Google A2A interface disabled")


# Global A2A interface instance
a2a_interface: GoogleA2AInterface | None = None


def initialize_a2a_interface(orchestrator):
    """
    Initialize the global A2A interface.

    Args:
        orchestrator: The agent orchestrator instance
    """
    global a2a_interface
    a2a_interface = GoogleA2AInterface(orchestrator)

    # Register local agents with A2A interface
    if orchestrator:
        available_agents = orchestrator.get_available_agents()
        for agent in available_agents:
            a2a_interface.register_local_agent(
                agent_id=f"local_{agent['type']}", capabilities=agent
            )

    logger.info("Google A2A interface initialized")
    return a2a_interface
