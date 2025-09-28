import gradio as gr

from .webui_manager import WebuiManager
from .pages.document_editor_page import create_document_editor_page
from .pages.settings_page import create_settings_page
from .pages.agents_page import create_agents_page

theme_map = {
    "Default": gr.themes.Default(),
    "Soft": gr.themes.Soft(),
    "Monochrome": gr.themes.Monochrome(),
    "Glass": gr.themes.Glass(),
    "Origin": gr.themes.Origin(),
    "Citrus": gr.themes.Citrus(),
    "Ocean": gr.themes.Ocean(),
    "Base": gr.themes.Base()
}


def create_ui(theme_name="Ocean"):
    css = """
    .gradio-container {
        width: 70vw !important;
        max-width: 70% !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 10px !important;
    }
    .header-text {
        text-align: center;
        margin-bottom: 20px;
    }
    .tab-header-text {
        text-align: center;
    }
    .theme-section {
        margin-bottom: 10px;
        padding: 15px;
        border-radius: 10px;
    }
    """

    # dark mode in default
    js_func = """
    function refresh() {
        const url = new URL(window.location);

        if (url.searchParams.get('__theme') !== 'dark') {
            url.searchParams.set('__theme', 'dark');
            window.location.href = url.href;
        }
    }
    """

    ui_manager = WebuiManager()

    with gr.Blocks(
            title="AI Document Editor & Browser WebUI", theme=theme_map[theme_name], css=css, js=js_func,
    ) as demo:
        with gr.Row():
            gr.Markdown(
                """
                # 📝 AI Document Editor & Browser WebUI
                ### Edit documents with AI assistance and control your browser
                """,
                elem_classes=["header-text"],
            )

        with gr.Tabs() as tabs:
            with gr.TabItem("📝 Document Editor & Chat"):
                create_document_editor_page(ui_manager)

            with gr.TabItem("🤖 AI Agents"):
                create_agents_page(ui_manager)

            with gr.TabItem("⚙️ Settings"):
                create_settings_page(ui_manager)

    return demo
