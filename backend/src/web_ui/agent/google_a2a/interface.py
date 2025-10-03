"""
Google Agent-to-Agent (A2A) Interface.

Implements the Google A2A protocol specification for inter-agent communication
while maintaining compatibility with the existing agent orchestrator.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class A2AMessageType(Enum):
    """Types of A2A messages following Google A2A specification."""

    # Core message types from Google A2A spec
    MESSAGE_SEND = "message/send"
    MESSAGE_STREAM = "message/stream"
    TASKS_GET = "tasks/get"
    TASKS_CANCEL = "tasks/cancel"
    TASKS_RESUBSCRIBE = "tasks/resubscribe"
    PUSH_NOTIFICATION_CONFIG_SET = "tasks/pushNotificationConfig/set"
    PUSH_NOTIFICATION_CONFIG_GET = "tasks/pushNotificationConfig/get"

    # Legacy types for backward compatibility
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    ERROR = "error"


class A2AMessage:
    """
    Represents a message in the Google A2A protocol.

    Follows the Google A2A specification for agent-to-agent communication.
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
        self.message_id = message_id or f"msg_{uuid.uuid4()}"
        self.timestamp = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary format following A2A spec."""
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
        """Create message from dictionary following A2A spec."""
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

    Implements the Google A2A protocol specification for standardized
    agent communication while working with the current orchestrator system.
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
        self.enabled = True  # Enable by default for development

    def register_local_agent(self, agent_id: str, capabilities: dict[str, Any]):
        """
        Register a local agent for A2A communication.

        Args:
            agent_id: Unique identifier for the agent
            capabilities: Agent capabilities and metadata per A2A spec
        """
        # Enhance capabilities with A2A-specific metadata
        enhanced_capabilities = {
            **capabilities,
            "a2a_registration_time": datetime.now(UTC).isoformat(),
            "a2a_interface_version": "0.2.1",  # Google A2A spec version
            "a2a_features": {
                "message_types": [
                    A2AMessageType.MESSAGE_SEND.value,
                    A2AMessageType.TASKS_GET.value,
                    A2AMessageType.CAPABILITY_QUERY.value,
                ],
                "collaboration_types": capabilities.get("collaboration_types", []),
                "can_receive_a2a": True,
                "can_send_a2a": True,
            },
        }

        self.registered_agents[agent_id] = {
            "id": agent_id,
            "capabilities": enhanced_capabilities,
            "registered_at": datetime.now(UTC).isoformat(),
            "status": "active",
        }
        logger.info(f"Registered local agent for A2A: {agent_id}")

    async def send_message(self, message: A2AMessage) -> bool:
        """
        Send an A2A message following Google specification.

        Args:
            message: The A2A message to send

        Returns:
            bool: True if message was sent successfully
        """
        try:
            if not self.enabled:
                logger.debug(f"A2A not enabled, message queued: {message.message_id}")
                return self._queue_message(message)

            # Log the message using Google A2A format
            logger.info(
                f"A2A message sent: {message.sender_id} -> {message.receiver_id} "
                f"(type: {message.message_type.value})"
            )

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
        Receive and process an A2A message following Google specification.

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
        Route A2A message to appropriate handler based on Google spec.

        Args:
            message: The A2A message to route
        """
        try:
            if message.message_type == A2AMessageType.MESSAGE_SEND:
                await self._handle_message_send(message)
            elif message.message_type == A2AMessageType.TASKS_GET:
                await self._handle_tasks_get(message)
            elif message.message_type == A2AMessageType.CAPABILITY_QUERY:
                await self._handle_capability_query(message)
            elif message.message_type == A2AMessageType.STATUS_UPDATE:
                await self._handle_status_update(message)
            # Legacy handlers for backward compatibility
            elif message.message_type == A2AMessageType.TASK_REQUEST:
                await self._handle_task_request(message)
            else:
                logger.warning(f"Unhandled A2A message type: {message.message_type}")

        except Exception as e:
            logger.error(f"Failed to route A2A message: {e}")

    async def _handle_message_send(self, message: A2AMessage):
        """Handle message/send requests per Google A2A spec."""
        try:
            if not self.orchestrator:
                logger.error("No orchestrator available for message/send")
                return

            # Extract message details from payload
            payload = message.payload
            user_message = payload.get("message", {})
            parts = user_message.get("parts", [])

            if not parts:
                logger.error("No message parts found in message/send request")
                return

            # Convert to orchestrator format
            text_content = ""
            for part in parts:
                if part.get("kind") == "text":
                    text_content += part.get("text", "")

            if text_content:
                # Submit to local orchestrator
                task_id = await self.orchestrator.submit_task(
                    user_id="a2a_user",  # Special user for A2A requests
                    agent_type=payload.get("agent_type", "document_editor"),
                    action="chat",
                    payload={"message": text_content},
                )

                # Send response per A2A spec
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
            logger.error(f"Failed to handle message/send: {e}")

    async def _handle_tasks_get(self, message: A2AMessage):
        """Handle tasks/get requests per Google A2A spec."""
        try:
            task_id = message.payload.get("id")
            if not task_id:
                logger.error("No task ID provided in tasks/get request")
                return

            # Get task from orchestrator
            if self.orchestrator:
                task = self.orchestrator.get_task(task_id)
                if task:
                    response = A2AMessage(
                        message_type=A2AMessageType.TASK_RESPONSE,
                        sender_id=self.agent_id,
                        receiver_id=message.sender_id,
                        conversation_id=message.conversation_id,
                        payload={
                            "task": {
                                "id": task.id,
                                "status": {"state": task.status},
                                "result": task.result,
                                "error": task.error,
                            }
                        },
                    )
                    await self.send_message(response)

        except Exception as e:
            logger.error(f"Failed to handle tasks/get: {e}")

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

    def get_registered_agents(self) -> dict[str, Any]:
        """
        Get information about all registered A2A agents.

        Returns:
            Dict with registered agent details
        """
        agents_info = {}

        for agent_id, agent_data in self.registered_agents.items():
            capabilities = agent_data.get("capabilities", {})
            a2a_features = capabilities.get("a2a_features", {})

            agents_info[agent_id] = {
                "agent_id": agent_id,
                "type": capabilities.get("type", "unknown"),
                "name": capabilities.get("name", "Unknown Agent"),
                "a2a_enabled": capabilities.get("a2a_enabled", False),
                "message_types": a2a_features.get("message_types", []),
                "collaboration_types": a2a_features.get("collaboration_types", []),
                "can_receive_a2a": a2a_features.get("can_receive_a2a", False),
                "can_send_a2a": a2a_features.get("can_send_a2a", False),
                "actions_count": len(capabilities.get("actions", [])),
                "registered_at": agent_data.get("registered_at"),
                "status": agent_data.get("status", "unknown"),
            }

        return {
            "total_agents": len(agents_info),
            "a2a_enabled_agents": sum(
                1 for a in agents_info.values() if a["a2a_enabled"]
            ),
            "agents": agents_info,
        }

    def get_agent_info(self, agent_id: str) -> dict[str, Any] | None:
        """
        Get detailed information about a specific registered agent.

        Args:
            agent_id: ID of the agent to query

        Returns:
            Agent information dict or None if not found
        """
        if agent_id not in self.registered_agents:
            return None

        agent_data = self.registered_agents[agent_id]
        capabilities = agent_data.get("capabilities", {})
        a2a_features = capabilities.get("a2a_features", {})

        return {
            "agent_id": agent_id,
            "type": capabilities.get("type"),
            "name": capabilities.get("name"),
            "description": capabilities.get("description"),
            "a2a_enabled": capabilities.get("a2a_enabled", False),
            "a2a_features": {
                "message_types": a2a_features.get("message_types", []),
                "collaboration_types": a2a_features.get("collaboration_types", []),
                "can_receive_a2a": a2a_features.get("can_receive_a2a", False),
                "can_send_a2a": a2a_features.get("can_send_a2a", False),
            },
            "actions": capabilities.get("actions", []),
            "collaboration_capabilities": capabilities.get(
                "collaboration_capabilities", []
            ),
            "registered_at": agent_data.get("registered_at"),
            "status": agent_data.get("status"),
            "a2a_registration_time": capabilities.get("a2a_registration_time"),
            "a2a_interface_version": capabilities.get("a2a_interface_version"),
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
        a2a_enabled_count = 0

        for agent in available_agents:
            # Only register A2A-enabled agents
            if agent.get("a2a_enabled", False):
                agent_id = agent.get("agent_id", f"local_{agent['type']}")
                a2a_interface.register_local_agent(
                    agent_id=agent_id,
                    capabilities={
                        **agent,
                        "a2a_registration_time": datetime.now(UTC).isoformat(),
                        "a2a_interface_version": "0.1.0",
                    },
                )
                a2a_enabled_count += 1
                logger.info(
                    f"Registered A2A agent: {agent_id} | "
                    f"Type: {agent['type']} | "
                    f"Message Types: {len(agent.get('a2a_features', {}).get('message_types', []))}"
                )
            else:
                logger.debug(f"Skipping non-A2A agent: {agent['type']}")

        logger.info(
            f"Google A2A interface initialized with {a2a_enabled_count} A2A-enabled agents "
            f"({len(available_agents) - a2a_enabled_count} non-A2A agents skipped)"
        )
    else:
        logger.warning("A2A interface initialized without orchestrator")

    return a2a_interface
