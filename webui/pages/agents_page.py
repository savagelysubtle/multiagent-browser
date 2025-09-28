import gradio as gr

from ..tabs.browser_use_agent_tab import create_browser_use_agent_tab
from ..tabs.deep_research_agent_tab import create_deep_research_agent_tab
from ..webui_manager import WebuiManager


def create_agents_page(webui_manager: WebuiManager):
    """
    Creates a unified agents page containing both Browser Use Agent and Deep Research Agent tabs.
    """
    with gr.Column():
        gr.Markdown(
            """
            # 🤖 AI Agents
            ### Choose your agent type and run automated tasks
            """,
            elem_classes=["header-text"],
        )

        with gr.Tabs():
            with gr.TabItem("🌐 Browser Use Agent"):
                gr.Markdown(
                    """
                    ### Browser Use Agent
                    Automate web browsing tasks with AI-powered browser automation
                    """,
                    elem_classes=["tab-header-text"],
                )
                create_browser_use_agent_tab(webui_manager)

            with gr.TabItem("🔍 Deep Research Agent"):
                gr.Markdown(
                    """
                    ### Deep Research Agent
                    Conduct comprehensive research across multiple sources
                    """,
                    elem_classes=["tab-header-text"],
                )
                create_deep_research_agent_tab(webui_manager)
