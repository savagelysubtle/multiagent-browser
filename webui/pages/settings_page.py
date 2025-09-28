import gradio as gr

from ..tabs.settings_tab import create_settings_tab
from ..webui_manager import WebuiManager


def create_settings_page(webui_manager: WebuiManager):
    """
    Creates a settings page containing all configuration options.
    """
    with gr.Column():
        gr.Markdown(
            """
            # ⚙️ Settings & Configuration
            ### Configure agents, browser settings, and system options
            """,
            elem_classes=["header-text"],
        )

        create_settings_tab(webui_manager)
