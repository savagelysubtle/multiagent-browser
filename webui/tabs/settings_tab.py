import json
import logging
import os

import gradio as gr

from ...utils import config
from ..webui_manager import WebuiManager

logger = logging.getLogger(__name__)


def strtobool(val):
    """Convert a string representation of truth to True or False."""
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"invalid truth value {val!r}")


def update_model_dropdown(llm_provider):
    """Update the model name dropdown with predefined models for the selected provider."""
    if llm_provider in config.model_names:
        return gr.Dropdown(
            choices=config.model_names[llm_provider],
            value=config.model_names[llm_provider][0],
            interactive=True,
        )
    else:
        return gr.Dropdown(
            choices=[], value="", interactive=True, allow_custom_value=True
        )


def load_default_mcp_config():
    """Load the default MCP configuration from data/mcp.json"""
    default_mcp_file = "./data/mcp.json"
    try:
        if os.path.exists(default_mcp_file):
            with open(default_mcp_file) as f:
                mcp_server = json.load(f)
            logger.info(f"Loaded default MCP configuration from {default_mcp_file}")
            return json.dumps(mcp_server, indent=2), default_mcp_file
        else:
            logger.warning(f"Default MCP file not found: {default_mcp_file}")
            return "", None
    except Exception as e:
        logger.error(f"Error loading default MCP configuration: {e}")
        return "", None


async def close_browser(webui_manager: WebuiManager):
    """Close browser"""
    if webui_manager.bu_current_task and not webui_manager.bu_current_task.done():
        webui_manager.bu_current_task.cancel()
        webui_manager.bu_current_task = None

    if webui_manager.bu_browser_context:
        logger.info("⚠️ Closing browser context when changing browser config.")
        await webui_manager.bu_browser_context.close()
        webui_manager.bu_browser_context = None

    if webui_manager.bu_browser:
        logger.info("⚠️ Closing browser when changing browser config.")
        await webui_manager.bu_browser.close()
        webui_manager.bu_browser = None


async def update_mcp_server(mcp_file: str, webui_manager: WebuiManager):
    """Update the MCP server."""
    if hasattr(webui_manager, "bu_controller") and webui_manager.bu_controller:
        logger.warning("Close controller because mcp file has changed!")
        await webui_manager.bu_controller.close_mcp_client()
        webui_manager.bu_controller = None

    if not mcp_file or not os.path.exists(mcp_file) or not mcp_file.endswith(".json"):
        logger.warning(f"{mcp_file} is not a valid MCP file.")
        return None, gr.update(visible=False)

    with open(mcp_file) as f:
        mcp_server = json.load(f)

    return json.dumps(mcp_server, indent=2), gr.update(visible=True)


def create_settings_tab(webui_manager: WebuiManager):
    """Creates a settings tab combining configuration, browser, and agent settings in a 3-column layout."""
    tab_components = {}
    default_mcp_content, default_mcp_file_path = load_default_mcp_config()

    with gr.Row(equal_height=False):
        # ==================== COLUMN 1: CONFIGURATION & SYSTEM ====================
        with gr.Column(scale=1):
            # Configuration Management
            with gr.Group():
                gr.Markdown("## ⚙️ Configuration Management")

                config_file = gr.File(
                    label="Load UI Settings from JSON",
                    file_types=[".json"],
                    interactive=True,
                )
                with gr.Row():
                    load_config_button = gr.Button("Load Config", variant="primary")
                    save_config_button = gr.Button(
                        "Save UI Settings", variant="primary"
                    )

                config_status = gr.Textbox(label="Status", lines=2, interactive=False)

            # System Prompts
            with gr.Group():
                gr.Markdown("## 📝 System Prompts")
                override_system_prompt = gr.Textbox(
                    label="Override System Prompt", lines=6, interactive=True
                )
                extend_system_prompt = gr.Textbox(
                    label="Extend System Prompt", lines=6, interactive=True
                )

            # Agent Parameters
            with gr.Group():
                gr.Markdown("## 🎯 Agent Parameters")
                with gr.Column():
                    max_steps = gr.Slider(
                        minimum=1,
                        maximum=1000,
                        value=100,
                        step=1,
                        label="Max Run Steps",
                        info="Maximum number of steps the agent will take",
                        interactive=True,
                    )
                    max_actions = gr.Slider(
                        minimum=1,
                        maximum=100,
                        value=10,
                        step=1,
                        label="Max Actions per Step",
                        info="Maximum number of actions per step",
                        interactive=True,
                    )
                    max_input_tokens = gr.Number(
                        label="Max Input Tokens",
                        value=128000,
                        precision=0,
                        interactive=True,
                    )
                    tool_calling_method = gr.Dropdown(
                        label="Tool Calling Method",
                        value="auto",
                        interactive=True,
                        allow_custom_value=True,
                        choices=[
                            "function_calling",
                            "json_mode",
                            "raw",
                            "auto",
                            "tools",
                            "None",
                        ],
                    )

        # ==================== COLUMN 2: BROWSER SETTINGS ====================
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("## 🌐 Browser Settings")

                # Browser Configuration
                gr.Markdown("### Browser Configuration")
                browser_binary_path = gr.Textbox(
                    label="Browser Binary Path",
                    lines=1,
                    interactive=True,
                    placeholder="e.g. '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome'",
                )
                browser_user_data_dir = gr.Textbox(
                    label="Browser User Data Dir",
                    lines=1,
                    interactive=True,
                    placeholder="Leave empty to use default user data",
                )

                # Browser Options
                gr.Markdown("### Browser Options")
                with gr.Column():
                    use_own_browser = gr.Checkbox(
                        label="Use Own Browser",
                        value=bool(strtobool(os.getenv("USE_OWN_BROWSER", "false"))),
                        info="Use your existing browser instance",
                        interactive=True,
                    )
                    keep_browser_open = gr.Checkbox(
                        label="Keep Browser Open",
                        value=bool(strtobool(os.getenv("KEEP_BROWSER_OPEN", "true"))),
                        info="Keep browser open between tasks",
                        interactive=True,
                    )
                    headless = gr.Checkbox(
                        label="Headless Mode",
                        value=False,
                        info="Run browser without GUI",
                        interactive=True,
                    )
                    disable_security = gr.Checkbox(
                        label="Disable Security",
                        value=False,
                        info="Disable browser security",
                        interactive=True,
                    )

                # Window & Connection Settings
                gr.Markdown("### Window & Connection Settings")
                with gr.Row():
                    window_w = gr.Number(
                        label="Window Width",
                        value=1280,
                        info="Browser window width",
                        interactive=True,
                    )
                    window_h = gr.Number(
                        label="Window Height",
                        value=1100,
                        info="Browser window height",
                        interactive=True,
                    )
                cdp_url = gr.Textbox(
                    label="CDP URL",
                    value=os.getenv("BROWSER_CDP", None),
                    info="CDP URL for browser remote debugging",
                    interactive=True,
                )
                wss_url = gr.Textbox(
                    label="WSS URL",
                    info="WSS URL for browser remote debugging",
                    interactive=True,
                )

                # File Paths
                gr.Markdown("### File Paths")
                save_recording_path = gr.Textbox(
                    label="Recording Path",
                    placeholder="e.g. ./tmp/record_videos",
                    info="Path to save browser recordings",
                    interactive=True,
                )
                save_trace_path = gr.Textbox(
                    label="Trace Path",
                    placeholder="e.g. ./tmp/traces",
                    info="Path to save agent traces",
                    interactive=True,
                )
                save_agent_history_path = gr.Textbox(
                    label="Agent History Save Path",
                    value="./tmp/agent_history",
                    info="Directory where agent history should be saved",
                    interactive=True,
                )
                save_download_path = gr.Textbox(
                    label="Save Directory for Browser Downloads",
                    value="./tmp/downloads",
                    info="Directory where downloaded files should be saved",
                    interactive=True,
                )

        # ==================== COLUMN 3: LLM & MCP SETTINGS ====================
        with gr.Column(scale=1):
            # MCP Server Configuration
            with gr.Group():
                gr.Markdown("## 🔧 MCP Server Configuration")
                gr.Markdown(
                    f"**Default MCP File**: `{default_mcp_file_path or 'Not found'}`"
                )

                mcp_json_file = gr.File(
                    label="MCP Server JSON",
                    interactive=True,
                    file_types=[".json"],
                    value=default_mcp_file_path if default_mcp_file_path else None,
                )
                mcp_server_config = gr.Textbox(
                    label="MCP Server Configuration",
                    lines=6,
                    interactive=True,
                    visible=True,
                    value=default_mcp_content,
                    info="Current MCP server configuration",
                )

            # Primary LLM Settings
            with gr.Group():
                gr.Markdown("## 🤖 Primary LLM Settings")
                llm_provider = gr.Dropdown(
                    choices=[
                        provider for provider, model in config.model_names.items()
                    ],
                    label="LLM Provider",
                    value=os.getenv("DEFAULT_LLM", "openai"),
                    info="Select LLM provider",
                    interactive=True,
                )
                llm_model_name = gr.Dropdown(
                    label="LLM Model Name",
                    choices=config.model_names[os.getenv("DEFAULT_LLM", "openai")],
                    value=config.model_names[os.getenv("DEFAULT_LLM", "openai")][0],
                    interactive=True,
                    allow_custom_value=True,
                    info="Select model or type custom model name",
                )
                with gr.Row():
                    llm_temperature = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=0.6,
                        step=0.1,
                        label="Temperature",
                        info="Controls randomness",
                        interactive=True,
                    )
                    use_vision = gr.Checkbox(
                        label="Use Vision",
                        value=True,
                        info="Enable vision capabilities",
                        interactive=True,
                    )
                llm_base_url = gr.Textbox(
                    label="Base URL", value="", info="API endpoint URL (if required)"
                )
                llm_api_key = gr.Textbox(
                    label="API Key",
                    type="password",
                    value="",
                    info="Your API key (leave blank to use .env)",
                )

                ollama_num_ctx = gr.Slider(
                    minimum=2**8,
                    maximum=2**16,
                    value=16000,
                    step=1,
                    label="Ollama Context Length",
                    info="Controls max context length",
                    visible=False,
                    interactive=True,
                )

            # Planner LLM Settings
            with gr.Group():
                gr.Markdown("## 🧠 Planner LLM Settings")
                planner_llm_provider = gr.Dropdown(
                    choices=[
                        provider for provider, model in config.model_names.items()
                    ],
                    label="Planner LLM Provider",
                    info="Select LLM provider for planner",
                    value=None,
                    interactive=True,
                )
                planner_llm_model_name = gr.Dropdown(
                    label="Planner LLM Model Name",
                    interactive=True,
                    allow_custom_value=True,
                    info="Select model or type custom model name",
                )
                with gr.Row():
                    planner_llm_temperature = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=0.6,
                        step=0.1,
                        label="Temperature",
                        info="Controls randomness",
                        interactive=True,
                    )
                    planner_use_vision = gr.Checkbox(
                        label="Use Vision",
                        value=False,
                        info="Enable vision for planner",
                        interactive=True,
                    )
                planner_llm_base_url = gr.Textbox(
                    label="Base URL", value="", info="API endpoint URL (if required)"
                )
                planner_llm_api_key = gr.Textbox(
                    label="API Key",
                    type="password",
                    value="",
                    info="Your API key (leave blank to use .env)",
                )

                planner_ollama_num_ctx = gr.Slider(
                    minimum=2**8,
                    maximum=2**16,
                    value=16000,
                    step=1,
                    label="Ollama Context Length",
                    info="Controls max context length",
                    visible=False,
                    interactive=True,
                )

    # Register all components
    tab_components.update(
        {
            # Configuration Management
            "load_config_button": load_config_button,
            "save_config_button": save_config_button,
            "config_status": config_status,
            "config_file": config_file,
            # Browser Settings
            "browser_binary_path": browser_binary_path,
            "browser_user_data_dir": browser_user_data_dir,
            "use_own_browser": use_own_browser,
            "keep_browser_open": keep_browser_open,
            "headless": headless,
            "disable_security": disable_security,
            "save_recording_path": save_recording_path,
            "save_trace_path": save_trace_path,
            "save_agent_history_path": save_agent_history_path,
            "save_download_path": save_download_path,
            "cdp_url": cdp_url,
            "wss_url": wss_url,
            "window_h": window_h,
            "window_w": window_w,
            # Agent Settings
            "override_system_prompt": override_system_prompt,
            "extend_system_prompt": extend_system_prompt,
            "llm_provider": llm_provider,
            "llm_model_name": llm_model_name,
            "llm_temperature": llm_temperature,
            "use_vision": use_vision,
            "ollama_num_ctx": ollama_num_ctx,
            "llm_base_url": llm_base_url,
            "llm_api_key": llm_api_key,
            "planner_llm_provider": planner_llm_provider,
            "planner_llm_model_name": planner_llm_model_name,
            "planner_llm_temperature": planner_llm_temperature,
            "planner_use_vision": planner_use_vision,
            "planner_ollama_num_ctx": planner_ollama_num_ctx,
            "planner_llm_base_url": planner_llm_base_url,
            "planner_llm_api_key": planner_llm_api_key,
            "max_steps": max_steps,
            "max_actions": max_actions,
            "max_input_tokens": max_input_tokens,
            "tool_calling_method": tool_calling_method,
            "mcp_json_file": mcp_json_file,
            "mcp_server_config": mcp_server_config,
        }
    )

    webui_manager.add_components("unified_settings", tab_components)

    # ==================== EVENT HANDLERS ====================

    # Configuration Management Events
    save_config_button.click(
        fn=webui_manager.save_config,
        inputs=set(webui_manager.get_components()),
        outputs=[config_status],
    )

    load_config_button.click(
        fn=webui_manager.load_config,
        inputs=[config_file],
        outputs=webui_manager.get_components(),
    )

    # Browser Settings Events - close browser when settings change
    async def close_wrapper():
        """Wrapper for browser close."""
        await close_browser(webui_manager)

    headless.change(close_wrapper)
    keep_browser_open.change(close_wrapper)
    disable_security.change(close_wrapper)
    use_own_browser.change(close_wrapper)

    # LLM Provider Events
    llm_provider.change(
        fn=lambda x: gr.update(visible=x == "ollama"),
        inputs=llm_provider,
        outputs=ollama_num_ctx,
    )
    llm_provider.change(
        lambda provider: update_model_dropdown(provider),
        inputs=[llm_provider],
        outputs=[llm_model_name],
    )

    # Planner LLM Provider Events
    planner_llm_provider.change(
        fn=lambda x: gr.update(visible=x == "ollama"),
        inputs=[planner_llm_provider],
        outputs=[planner_ollama_num_ctx],
    )
    planner_llm_provider.change(
        lambda provider: update_model_dropdown(provider),
        inputs=[planner_llm_provider],
        outputs=[planner_llm_model_name],
    )

    # MCP Server Events
    async def update_wrapper(mcp_file):
        """Wrapper for MCP server file update."""
        update_dict = await update_mcp_server(mcp_file, webui_manager)
        yield update_dict

    mcp_json_file.change(
        update_wrapper,
        inputs=[mcp_json_file],
        outputs=[mcp_server_config, mcp_server_config],
    )
