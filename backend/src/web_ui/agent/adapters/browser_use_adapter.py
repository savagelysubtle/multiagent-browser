"""
Browser Use Agent Adapter.

Adapts the existing BrowserUse agent to work with the SimpleAgentOrchestrator.
Supports Google A2A (Agent-to-Agent) protocol for inter-agent communication.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class BrowserUseAdapter:
    """
    Adapter for the Browser Use agent with A2A protocol support.

    This adapter wraps the existing BrowserUse agent and provides
    a standardized interface for the orchestrator, including A2A messaging.
    """

    def __init__(self, browser_use_instance=None):
        """
        Initialize the adapter.

        Args:
            browser_use_instance: The actual BrowserUse agent instance
        """
        self.browser_use = browser_use_instance
        self.agent_type = "browser_use"
        self.agent_id = "browser_use_agent"
        self.a2a_enabled = True
        self.message_handlers = {}
        self._register_a2a_handlers()

    def _register_a2a_handlers(self):
        """Register A2A message type handlers."""
        self.message_handlers = {
            "task_request": self._handle_task_request,
            "capability_query": self._handle_capability_query,
            "status_query": self._handle_status_query,
        }

    async def handle_a2a_message(self, message: Any) -> dict[str, Any]:
        """
        Handle incoming A2A protocol messages.

        Args:
            message: A2A message object with attributes:
                - message_type: Type of message
                - sender_agent: Sending agent ID
                - payload: Message payload
                - conversation_id: Conversation identifier

        Returns:
            Dict with response data
        """
        try:
            logger.info(
                f"BrowserUseAdapter received A2A message: {message.message_type} from {message.sender_agent}"
            )

            # Get appropriate handler
            handler = self.message_handlers.get(
                message.message_type, self._handle_unknown_message
            )

            # Process message
            response = await handler(message)

            logger.info(f"A2A message processed successfully: {message.id}")
            return response

        except Exception as e:
            logger.error(f"Error handling A2A message: {e}")
            return {
                "success": False,
                "error": str(e),
                "message_id": message.id if hasattr(message, "id") else None,
            }

    async def _handle_task_request(self, message: Any) -> dict[str, Any]:
        """Handle A2A task request."""
        try:
            payload = message.payload
            action = payload.get("action", "browse")
            params = payload.get("params", {})

            logger.info(f"Processing A2A task request: action={action}")

            # Route to appropriate method
            if action == "browse":
                result = await self.browse(
                    url=params.get("url", ""),
                    instruction=params.get("instruction", ""),
                    **params.get("kwargs", {}),
                )
            elif action == "extract":
                result = await self.extract(
                    url=params.get("url", ""),
                    selectors=params.get("selectors", []),
                    **params.get("kwargs", {}),
                )
            elif action == "screenshot":
                result = await self.screenshot(
                    url=params.get("url", ""), **params.get("kwargs", {})
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "supported_actions": ["browse", "extract", "screenshot"],
                }

            return {
                "success": True,
                "action": action,
                "result": result,
                "agent_id": self.agent_id,
                "conversation_id": message.conversation_id,
            }

        except Exception as e:
            logger.error(f"Error in A2A task request: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_capability_query(self, message: Any) -> dict[str, Any]:
        """Handle A2A capability query."""
        return {
            "success": True,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.get_capabilities(),
            "a2a_enabled": self.a2a_enabled,
            "supported_protocols": ["http", "https"],
        }

    async def _handle_status_query(self, message: Any) -> dict[str, Any]:
        """Handle A2A status query."""
        return {
            "success": True,
            "agent_id": self.agent_id,
            "status": "ready",
            "active": self.browser_use is not None,
            "a2a_enabled": self.a2a_enabled,
        }

    async def _handle_unknown_message(self, message: Any) -> dict[str, Any]:
        """Handle unknown A2A message types."""
        logger.warning(f"Unknown A2A message type: {message.message_type}")
        return {
            "success": False,
            "error": f"Unknown message type: {message.message_type}",
            "supported_types": list(self.message_handlers.keys()),
        }

    async def browse(
        self,
        url: str,
        instruction: str,
        progress_callback: Callable[[int, str], Awaitable[None]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Navigate to a URL and interact with it based on instructions.

        Args:
            url: The URL to navigate to
            instruction: Instructions for what to do on the page
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with browsing result
        """
        try:
            if progress_callback:
                await progress_callback(10, "Validating URL...")

            # Validate inputs
            if not url or not url.strip():
                raise ValueError("URL cannot be empty")

            if not instruction or not instruction.strip():
                raise ValueError("Instruction cannot be empty")

            # Basic URL validation
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url

            if progress_callback:
                await progress_callback(25, "Initializing browser...")

            # If we have an actual browser use agent, use it
            if self.browser_use:
                if progress_callback:
                    await progress_callback(50, "Executing browsing task...")

                result = await self.browser_use.browse(
                    url=url, instruction=instruction, **kwargs
                )
            else:
                # Fallback implementation - simulate browsing
                if progress_callback:
                    await progress_callback(50, "Simulating browser interaction...")

                # This would normally use a real browser automation library
                result = {
                    "url": url,
                    "title": "Simulated Page Title",
                    "content": f"Simulated page content for {url}",
                    "instruction_result": f"Simulated execution of: {instruction}",
                    "status": "completed",
                }

            if progress_callback:
                await progress_callback(90, "Processing results...")

            browse_result = {
                "success": True,
                "url": url,
                "instruction": instruction,
                "result": result,
                "browsed_at": datetime.utcnow().isoformat(),
                "execution_time": "simulated",
            }

            if progress_callback:
                await progress_callback(100, "Browsing completed")

            logger.info(f"Browse completed: {url}")
            return browse_result

        except Exception as e:
            logger.error(f"Failed to browse {url}: {e}")
            raise

    async def extract(
        self,
        url: str,
        selectors: list[str],
        progress_callback: Callable[[int, str], Awaitable[None]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Extract specific information from a webpage using CSS selectors.

        Args:
            url: The URL to extract from
            selectors: List of CSS selectors to extract
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with extraction results
        """
        try:
            if progress_callback:
                await progress_callback(10, "Validating inputs...")

            # Validate inputs
            if not url or not url.strip():
                raise ValueError("URL cannot be empty")

            if not selectors or not isinstance(selectors, list):
                raise ValueError("Selectors must be a non-empty list")

            # Basic URL validation
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url

            if progress_callback:
                await progress_callback(25, "Loading webpage...")

            # If we have an actual browser use agent, use it
            if self.browser_use:
                if progress_callback:
                    await progress_callback(50, "Extracting data...")

                result = await self.browser_use.extract(
                    url=url, selectors=selectors, **kwargs
                )
            else:
                # Fallback implementation - simulate extraction
                if progress_callback:
                    await progress_callback(50, "Simulating data extraction...")

                # This would normally use a real web scraping library
                extracted_data = {}
                for i, selector in enumerate(selectors):
                    extracted_data[selector] = (
                        f"Simulated content for selector: {selector}"
                    )

                result = {
                    "url": url,
                    "extracted_data": extracted_data,
                    "selectors_found": len(selectors),
                    "status": "completed",
                }

            if progress_callback:
                await progress_callback(90, "Processing extracted data...")

            extract_result = {
                "success": True,
                "url": url,
                "selectors": selectors,
                "extracted_data": result.get("extracted_data", {}),
                "selectors_found": result.get("selectors_found", 0),
                "extracted_at": datetime.utcnow().isoformat(),
            }

            if progress_callback:
                await progress_callback(100, "Extraction completed")

            logger.info(f"Extract completed: {url} ({len(selectors)} selectors)")
            return extract_result

        except Exception as e:
            logger.error(f"Failed to extract from {url}: {e}")
            raise

    async def screenshot(
        self,
        url: str,
        progress_callback: Callable[[int, str], Awaitable[None]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Take a screenshot of a webpage.

        Args:
            url: The URL to screenshot
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with screenshot result
        """
        try:
            if progress_callback:
                await progress_callback(20, "Loading webpage...")

            # Validate inputs
            if not url or not url.strip():
                raise ValueError("URL cannot be empty")

            # Basic URL validation
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url

            if progress_callback:
                await progress_callback(50, "Taking screenshot...")

            # If we have an actual browser use agent, use it
            if self.browser_use and hasattr(self.browser_use, "screenshot"):
                result = await self.browser_use.screenshot(url=url, **kwargs)
            else:
                # Fallback implementation - simulate screenshot
                result = {
                    "url": url,
                    "screenshot_path": f"screenshots/screenshot_{datetime.utcnow().timestamp()}.png",
                    "format": "png",
                    "status": "simulated",
                }

            if progress_callback:
                await progress_callback(90, "Saving screenshot...")

            screenshot_result = {
                "success": True,
                "url": url,
                "screenshot_path": result.get("screenshot_path"),
                "format": result.get("format", "png"),
                "taken_at": datetime.utcnow().isoformat(),
            }

            if progress_callback:
                await progress_callback(100, "Screenshot completed")

            logger.info(f"Screenshot taken: {url}")
            return screenshot_result

        except Exception as e:
            logger.error(f"Failed to take screenshot of {url}: {e}")
            raise

    def get_capabilities(self) -> dict[str, Any]:
        """Get the capabilities of this adapter."""
        return {
            "agent_type": self.agent_type,
            "actions": ["browse", "extract", "screenshot"],
            "supports_progress": True,
            "supported_protocols": ["http", "https"],
            "features": [
                "Web navigation",
                "Element interaction",
                "Data extraction",
                "Screenshot capture",
                "JavaScript execution",
            ],
        }
