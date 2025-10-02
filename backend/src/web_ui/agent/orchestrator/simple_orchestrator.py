"""
Simple Agent Orchestrator for per-user task management with A2A protocol support.

This orchestrator manages agent tasks with real-time WebSocket updates,
user isolation, A2A (Agent2Agent) protocol support, and comprehensive error handling.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ...utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class A2AMessage:
    """Represents an A2A protocol message between agents, following Google A2A specification."""

    message_id: str  # Changed from 'id' to match spec
    sender_id: str   # Changed from 'sender_agent' to match spec
    receiver_id: str # Changed from 'recipient_agent' to match spec
    message_type: str  # 'request', 'response', 'notification', etc.
    payload: dict[str, Any]
    conversation_id: str | None = None  # Optional conversation grouping
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary format matching A2A spec."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "conversation_id": self.conversation_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "A2AMessage":
        """Create message from dictionary."""
        message = cls(
            message_id=data.get("message_id", ""),
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            message_type=data["message_type"],
            payload=data["payload"],
            conversation_id=data.get("conversation_id"),
            metadata=data.get("metadata"),
        )
        if "timestamp" in data:
            message.timestamp = datetime.fromisoformat(data["timestamp"])
        return message


@dataclass
class AgentTask:
    """Represents a task submitted to an agent with A2A support."""

    id: str
    user_id: str
    agent_type: str
    action: str
    payload: dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed, cancelled
    result: Any | None = None
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: dict[str, Any] | None = None
    # A2A specific fields
    conversation_id: str | None = None
    parent_task_id: str | None = None
    a2a_messages: list[A2AMessage] | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.progress is None:
            self.progress = {"percentage": 0, "message": "Waiting to start"}
        if self.a2a_messages is None:
            self.a2a_messages = []


class SimpleAgentOrchestrator:
    """
    Simplified agent orchestration for per-user tasks with A2A protocol support.

    Features:
    - User-isolated task management
    - Real-time WebSocket notifications
    - Agent registration and discovery
    - Task lifecycle management
    - A2A (Agent2Agent) protocol support
    - LangChain integration compatibility
    - Error handling and recovery
    """

    def __init__(self, ws_manager=None):
        self.agents = {}  # agent_type -> agent_instance
        self.user_tasks: dict[str, list[str]] = {}  # user_id -> task_ids
        self.task_store: dict[str, AgentTask] = {}  # task_id -> task
        self.running_tasks: dict[str, asyncio.Task] = {}  # task_id -> asyncio.Task
        self.ws_manager = ws_manager
        self.max_concurrent_tasks = 5
        self.task_timeout = 300  # 5 minutes default timeout

        # A2A protocol support
        self.a2a_conversations: dict[
            str, list[A2AMessage]
        ] = {}  # conversation_id -> messages
        self.agent_capabilities: dict[str, dict] = {}  # agent_type -> capabilities
        self.a2a_endpoints: dict[str, str] = {}  # agent_type -> endpoint_url

    def register_agent(
        self,
        agent_type: str,
        agent_instance,
        capabilities: dict | None = None,
        a2a_endpoint: str | None = None,
    ):
        """Register an agent for task execution with optional A2A capabilities."""
        self.agents[agent_type] = agent_instance

        # Auto-detect A2A capabilities from adapter if not provided
        if capabilities is None and hasattr(agent_instance, "get_capabilities"):
            capabilities = agent_instance.get_capabilities()

        # Check if agent supports A2A protocol
        if hasattr(agent_instance, "a2a_enabled"):
            capabilities = capabilities or {}
            capabilities["a2a_enabled"] = agent_instance.a2a_enabled
            capabilities["agent_id"] = getattr(agent_instance, "agent_id", agent_type)

        # Store A2A capabilities
        if capabilities:
            self.agent_capabilities[agent_type] = capabilities

        if a2a_endpoint:
            self.a2a_endpoints[agent_type] = a2a_endpoint

        a2a_enabled = capabilities.get("a2a_enabled", False) if capabilities else False
        logger.info(
            f"Registered agent: {agent_type} | A2A: {a2a_enabled} | Endpoint: {a2a_endpoint or 'local'}"
        )

    def get_available_agents(self) -> list[dict[str, Any]]:
        """Get list of available agents and their capabilities with A2A support."""
        return [
            {
                "type": "document_editor",
                "name": "Document Editor",
                "description": "Create and edit documents with AI assistance",
                "agent_id": "document_editor_agent",
                "a2a_compatible": True,
                "a2a_enabled": True,
                "langchain_integration": True,
                "a2a_features": {
                    "message_types": [
                        "task_request",
                        "capability_query",
                        "status_query",
                        "document_query",
                        "collaboration_request",
                    ],
                    "collaboration_types": ["document_assistance", "save_research"],
                    "can_receive_a2a": True,
                    "can_send_a2a": True,
                },
                "actions": [
                    {
                        "name": "create_document",
                        "description": "Create a new document",
                        "parameters": ["filename", "content", "document_type"],
                        "a2a_supported": True,
                        "a2a_action": "task_request",
                    },
                    {
                        "name": "edit_document",
                        "description": "Edit an existing document",
                        "parameters": ["document_id", "instruction"],
                        "a2a_supported": True,
                        "a2a_action": "task_request",
                    },
                    {
                        "name": "search_documents",
                        "description": "Search through documents",
                        "parameters": ["query", "limit"],
                        "a2a_supported": True,
                        "a2a_action": "task_request",
                    },
                    {
                        "name": "chat",
                        "description": "Chat with the document editor agent",
                        "parameters": ["message", "session_id", "context_document_id"],
                        "a2a_supported": True,
                        "a2a_action": "task_request",
                    },
                ],
                "collaboration_capabilities": [
                    "Can save research results from other agents",
                    "Provides document templates and suggestions",
                    "Searches knowledge base on behalf of other agents",
                ],
            },
            {
                "type": "browser_use",
                "name": "Browser Agent",
                "description": "Browse the web and extract information",
                "agent_id": "browser_use_agent",
                "a2a_compatible": True,
                "a2a_enabled": True,
                "langchain_integration": True,
                "a2a_features": {
                    "message_types": [
                        "task_request",
                        "capability_query",
                        "status_query",
                    ],
                    "collaboration_types": [],
                    "can_receive_a2a": True,
                    "can_send_a2a": True,
                },
                "actions": [
                    {
                        "name": "browse",
                        "description": "Navigate to a URL and interact with it",
                        "parameters": ["url", "instruction"],
                        "a2a_supported": True,
                        "a2a_action": "task_request",
                    },
                    {
                        "name": "extract",
                        "description": "Extract specific information from a webpage",
                        "parameters": ["url", "selectors"],
                        "a2a_supported": True,
                        "a2a_action": "task_request",
                    },
                    {
                        "name": "screenshot",
                        "description": "Capture webpage screenshots",
                        "parameters": ["url"],
                        "a2a_supported": True,
                        "a2a_action": "task_request",
                    },
                ],
                "collaboration_capabilities": [
                    "Can gather web data for other agents",
                    "Provides web scraping and extraction services",
                    "Can verify URLs and web content",
                ],
            },
            {
                "type": "deep_research",
                "name": "Research Agent",
                "description": "Conduct in-depth research on topics",
                "agent_id": "deep_research_agent",
                "a2a_compatible": True,
                "a2a_enabled": True,
                "langchain_integration": True,
                "a2a_features": {
                    "message_types": [
                        "task_request",
                        "capability_query",
                        "status_query",
                        "collaboration_request",
                    ],
                    "collaboration_types": ["research_assistance"],
                    "can_receive_a2a": True,
                    "can_send_a2a": True,
                },
                "actions": [
                    {
                        "name": "research",
                        "description": "Research a topic comprehensively",
                        "parameters": ["topic", "depth", "sources"],
                        "a2a_supported": True,
                        "a2a_action": "task_request",
                    },
                    {
                        "name": "analyze_sources",
                        "description": "Analyze and evaluate source credibility",
                        "parameters": ["sources"],
                        "a2a_supported": True,
                        "a2a_action": "task_request",
                    },
                ],
                "collaboration_capabilities": [
                    "Provides research assistance to other agents",
                    "Can analyze sources on behalf of other agents",
                    "Synthesizes information from multiple sources",
                ],
            },
            {
                "type": "langchain_agent",
                "name": "LangChain Agent",
                "description": "LangChain-powered agent with tool access",
                "agent_id": "langchain_agent",
                "a2a_compatible": True,
                "a2a_enabled": False,  # Not yet implemented
                "langchain_integration": True,
                "a2a_features": {
                    "message_types": [],
                    "collaboration_types": [],
                    "can_receive_a2a": False,
                    "can_send_a2a": False,
                },
                "actions": [
                    {
                        "name": "execute_chain",
                        "description": "Execute a LangChain chain or workflow",
                        "parameters": ["chain_config", "input_data"],
                        "a2a_supported": False,
                    },
                    {
                        "name": "tool_call",
                        "description": "Call a specific LangChain tool",
                        "parameters": ["tool_name", "tool_args"],
                        "a2a_supported": False,
                    },
                ],
                "collaboration_capabilities": [],
            },
        ]

    async def send_a2a_message(
        self,
        sender_agent: str,
        recipient_agent: str,
        message_type: str,
        payload: dict[str, Any],
        conversation_id: str | None = None,
    ) -> A2AMessage:
        """Send an A2A protocol message between agents."""
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_agent,
            receiver_id=recipient_agent,
            message_type=message_type,
            payload=payload,
            conversation_id=conversation_id,
            timestamp=datetime.utcnow(),
        )

        # Store message in conversation
        if conversation_id not in self.a2a_conversations:
            self.a2a_conversations[conversation_id] = []
        self.a2a_conversations[conversation_id].append(message)

        logger.info(
            f"A2A message sent: {sender_agent} -> {recipient_agent} (type: {message_type})"
        )

        # If recipient is registered locally, deliver directly
        if recipient_agent in self.agents:
            await self._deliver_a2a_message(message)
        else:
            # Handle external A2A endpoint delivery
            await self._send_external_a2a_message(message)

        return message

    async def _deliver_a2a_message(self, message: A2AMessage):
        """Deliver A2A message to a local agent."""
        agent = self.agents.get(message.receiver_id)
        if not agent:
            logger.error(
                f"Cannot deliver A2A message: agent {message.receiver_id} not found"
            )
            return

        # Check if agent supports A2A protocol
        if hasattr(agent, "handle_a2a_message"):
            try:
                await agent.handle_a2a_message(message)
                logger.debug(f"A2A message delivered to {message.receiver_id}")
            except Exception as e:
                logger.error(
                    f"Error delivering A2A message to {message.receiver_id}: {e}"
                )
        else:
            logger.warning(
                f"Agent {message.receiver_id} does not support A2A protocol"
            )

    async def _send_external_a2a_message(self, message: A2AMessage):
        """Send A2A message to external agent endpoint."""
        endpoint = self.a2a_endpoints.get(message.receiver_id)
        if not endpoint:
            logger.error(f"No A2A endpoint found for agent {message.receiver_id}")
            return

        # Implementation would depend on the specific A2A transport mechanism
        # This could be HTTP, WebSocket, gRPC, etc.
        logger.info(f"Would send A2A message to external endpoint: {endpoint}")

    async def request_agent_collaboration(
        self,
        requesting_agent: str,
        target_agent: str,
        collaboration_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Request collaboration between agents via A2A protocol.

        Args:
            requesting_agent: Agent requesting collaboration
            target_agent: Agent being requested to collaborate
            collaboration_type: Type of collaboration needed
            payload: Collaboration details

        Returns:
            Collaboration response from target agent
        """
        try:
            message = await self.send_a2a_message(
                sender_agent=requesting_agent,
                recipient_agent=target_agent,
                message_type="collaboration_request",
                payload={"type": collaboration_type, **payload},
            )

            logger.info(
                f"Collaboration requested: {requesting_agent} -> {target_agent} ({collaboration_type})"
            )
            return {"success": True, "message_id": message.message_id}

        except Exception as e:
            logger.error(f"Collaboration request failed: {e}")
            return {"success": False, "error": str(e)}

    async def query_agent_capabilities(self, agent_type: str) -> dict[str, Any]:
        """
        Query an agent's capabilities via A2A protocol.

        Args:
            agent_type: Type of agent to query

        Returns:
            Agent capabilities
        """
        try:
            # First check local cache
            if agent_type in self.agent_capabilities:
                return {
                    "success": True,
                    "capabilities": self.agent_capabilities[agent_type],
                    "source": "cache",
                }

            # Query via A2A if not in cache
            message = await self.send_a2a_message(
                sender_agent="orchestrator",
                recipient_agent=agent_type,
                message_type="capability_query",
                payload={"query": "full_capabilities"},
            )

            return {"success": True, "message_id": message.message_id, "source": "a2a_query"}

        except Exception as e:
            logger.error(f"Failed to query agent capabilities: {e}")
            return {"success": False, "error": str(e)}

    async def broadcast_message(
        self,
        sender_agent: str,
        message_type: str,
        payload: dict[str, Any],
        target_agents: list[str] | None = None,
    ) -> dict[str, list[str]]:
        """
        Broadcast an A2A message to multiple agents.

        Args:
            sender_agent: Agent sending the broadcast
            message_type: Type of message
            payload: Message payload
            target_agents: Specific agents to target (None = all agents)

        Returns:
            Dict with successful and failed message IDs
        """
        targets = target_agents or list(self.agents.keys())
        successful = []
        failed = []

        for target in targets:
            if target == sender_agent:
                continue  # Don't send to self

            try:
                message = await self.send_a2a_message(
                    sender_agent=sender_agent,
                    recipient_agent=target,
                    message_type=message_type,
                    payload=payload,
                )
                successful.append(message.message_id)
            except Exception as e:
                logger.error(f"Failed to broadcast to {target}: {e}")
                failed.append(target)

        logger.info(
            f"Broadcast from {sender_agent}: {len(successful)} successful, {len(failed)} failed"
        )
        return {"successful": successful, "failed": failed}

    def get_a2a_conversation(self, conversation_id: str) -> list[Any]:
        """
        Get A2A conversation history.

        Args:
            conversation_id: Conversation identifier

        Returns:
            List of A2A messages in conversation
        """
        return self.a2a_conversations.get(conversation_id, [])

    def get_agent_status(self, agent_type: str) -> dict[str, Any]:
        """
        Get current status of a registered agent.

        Args:
            agent_type: Type of agent

        Returns:
            Agent status information
        """
        if agent_type not in self.agents:
            return {
                "registered": False,
                "error": f"Agent type '{agent_type}' not registered",
            }

        agent = self.agents[agent_type]
        return {
            "registered": True,
            "agent_type": agent_type,
            "a2a_enabled": hasattr(agent, "a2a_enabled") and agent.a2a_enabled,
            "has_handle_a2a": hasattr(agent, "handle_a2a_message"),
            "capabilities": self.agent_capabilities.get(agent_type, {}),
            "a2a_endpoint": self.a2a_endpoints.get(agent_type, "local"),
        }


# Global orchestrator instance - will be initialized with WebSocket manager
orchestrator: SimpleAgentOrchestrator | None = None


def initialize_orchestrator(ws_manager):
    """Initialize the global orchestrator with WebSocket manager."""
    global orchestrator
    orchestrator = SimpleAgentOrchestrator(ws_manager)
    logger.info("Agent orchestrator initialized")
    return orchestrator
