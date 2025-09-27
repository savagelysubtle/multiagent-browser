import json
import logging
from collections.abc import Generator
from typing import TYPE_CHECKING
import os
import gradio as gr
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import uuid
import asyncio
import time

logger = logging.getLogger(__name__)

from gradio.components import Component
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext
from browser_use.agent.service import Agent
from ..browser.custom_browser import CustomBrowser
from ..browser.custom_context import CustomBrowserContext
from ..controller.custom_controller import CustomController
from ..agent.deep_research.deep_research_agent import DeepResearchAgent
from ..services.mcp_service import MCPService
from ..database.document_pipeline import DocumentPipeline


class WebuiManager:
    def __init__(self, settings_save_dir: str = "./tmp/webui_settings"):
        self.id_to_component: dict[str, Component] = {}
        self.component_to_id: dict[Component, str] = {}

        self.settings_save_dir = settings_save_dir
        os.makedirs(self.settings_save_dir, exist_ok=True)

        # Initialize database and MCP service
        self.document_pipeline: Optional[DocumentPipeline] = None
        self.mcp_service: Optional[MCPService] = None
        self._initialize_database_and_services()

    def init_browser_use_agent(self) -> None:
        """
        init browser use agent
        """
        self.bu_agent: Optional[Agent] = None
        self.bu_browser: Optional[CustomBrowser] = None
        self.bu_browser_context: Optional[CustomBrowserContext] = None
        self.bu_controller: Optional[CustomController] = None
        self.bu_chat_history: List[Dict[str, Optional[str]]] = []
        self.bu_response_event: Optional[asyncio.Event] = None
        self.bu_user_help_response: Optional[str] = None
        self.bu_current_task: Optional[asyncio.Task] = None
        self.bu_agent_task_id: Optional[str] = None

    def init_deep_research_agent(self) -> None:
        """
        init deep research agent
        """
        self.dr_agent: Optional[DeepResearchAgent] = None
        self.dr_current_task = None
        self.dr_agent_task_id: Optional[str] = None
        self.dr_save_dir: Optional[str] = None

    def init_document_editor(self) -> None:
        """
        init document editor
        """
        from .tabs.document_editor_tab import DocumentEditorManager
        self.de_manager: Optional[DocumentEditorManager] = DocumentEditorManager()
        self.de_current_file: Optional[str] = None
        self.de_recent_files: List[str] = []

    def add_components(self, tab_name: str, components_dict: dict[str, "Component"]) -> None:
        """
        Add tab components
        """
        for comp_name, component in components_dict.items():
            comp_id = f"{tab_name}.{comp_name}"
            self.id_to_component[comp_id] = component
            self.component_to_id[component] = comp_id

    def get_components(self) -> list["Component"]:
        """
        Get all components
        """
        return list(self.id_to_component.values())

    def get_component_by_id(self, comp_id: str) -> "Component":
        """
        Get component by id
        """
        return self.id_to_component[comp_id]

    def get_id_by_component(self, comp: "Component") -> str:
        """
        Get id by component
        """
        return self.component_to_id[comp]

    def save_config(self, components: Dict["Component", str]) -> None:
        """
        Save config
        """
        cur_settings = {}
        for comp in components:
            if not isinstance(comp, gr.Button) and not isinstance(comp, gr.File) and str(
                    getattr(comp, "interactive", True)).lower() != "false":
                comp_id = self.get_id_by_component(comp)
                cur_settings[comp_id] = components[comp]

        config_name = datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(os.path.join(self.settings_save_dir, f"{config_name}.json"), "w") as fw:
            json.dump(cur_settings, fw, indent=4)

        return os.path.join(self.settings_save_dir, f"{config_name}.json")

    def load_config(self, config_path: str):
        """
        Load config
        """
        with open(config_path, "r") as fr:
            ui_settings = json.load(fr)

        update_components = {}
        for comp_id, comp_val in ui_settings.items():
            if comp_id in self.id_to_component:
                comp = self.id_to_component[comp_id]
                if comp.__class__.__name__ == "Chatbot":
                    update_components[comp] = comp.__class__(value=comp_val, type="messages")
                else:
                    update_components[comp] = comp.__class__(value=comp_val)
                    if comp_id == "agent_settings.planner_llm_provider":
                        yield update_components  # yield provider, let callback run
                        time.sleep(0.1)  # wait for Gradio UI callback

        config_status = self.id_to_component["load_save_config.config_status"]
        update_components.update(
            {
                config_status: config_status.__class__(value=f"Successfully loaded config: {config_path}")
            }
        )
        yield update_components

    def _initialize_database_and_services(self) -> None:
        """Initialize document pipeline and MCP service."""
        try:
            # Initialize document pipeline
            self.document_pipeline = DocumentPipeline()
            logger.info("Document pipeline initialized successfully")

            # Initialize MCP service
            self.mcp_service = MCPService(self)
            logger.info("MCP service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database and services: {e}")

    async def initialize_mcp_from_database(self) -> bool:
        """
        Load and apply MCP configuration from ChromaDB at startup.

        Returns:
            True if configuration loaded successfully, False otherwise
        """
        try:
            if not self.mcp_service:
                logger.error("MCP service not available")
                return False

            # Start the MCP service which will load active configuration
            success = await self.mcp_service.start_service()

            if success:
                logger.info("MCP configuration loaded from database and applied")
                return True
            else:
                logger.info("MCP service started but no active configuration found")
                return False

        except Exception as e:
            logger.error(f"Failed to load MCP config from database: {e}")
            return False

    async def setup_mcp_client(self, mcp_server_config: Optional[Dict] = None) -> bool:
        """
        Setup MCP client with provided configuration or load from database.

        Args:
            mcp_server_config: Optional MCP configuration to apply

        Returns:
            True if setup successful, False otherwise
        """
        try:
            if not self.mcp_service:
                logger.error("MCP service not available")
                return False

            if mcp_server_config:
                # Apply provided configuration
                success = await self.mcp_service.apply_configuration(
                    config_data=mcp_server_config,
                    config_name="ui_provided_config"
                )
            else:
                # Load from database
                success = await self.mcp_service.load_active_configuration()

            if success:
                logger.info("MCP client setup completed")
                return True
            else:
                logger.warning("MCP client setup failed or no configuration available")
                return False

        except Exception as e:
            logger.error(f"Error setting up MCP client: {e}")
            return False

    async def get_mcp_service_status(self) -> Dict:
        """Get current MCP service status."""
        try:
            if not self.mcp_service:
                return {"error": "MCP service not available", "is_running": False}

            return await self.mcp_service.get_service_status()

        except Exception as e:
            logger.error(f"Error getting MCP service status: {e}")
            return {"error": str(e), "is_running": False}

    async def list_mcp_configurations(self) -> List[Dict]:
        """List all available MCP configurations."""
        try:
            if not self.mcp_service:
                return []

            return await self.mcp_service.list_available_configs()

        except Exception as e:
            logger.error(f"Error listing MCP configurations: {e}")
            return []

    async def switch_mcp_configuration(self, config_id: str) -> Tuple[bool, str]:
        """Switch to a different MCP configuration."""
        try:
            if not self.mcp_service:
                return False, "MCP service not available"

            return await self.mcp_service.switch_configuration(config_id)

        except Exception as e:
            logger.error(f"Error switching MCP configuration: {e}")
            return False, f"Error switching configuration: {str(e)}"


