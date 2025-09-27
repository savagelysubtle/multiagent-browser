import gradio as gr
from ..webui_manager import WebuiManager
from ..tabs.document_editor_tab import create_document_editor_tab


def create_document_editor_page(webui_manager: WebuiManager):
    """
    Creates a document editor page with AI-powered editing capabilities.
    """
    with gr.Column():


        create_document_editor_tab(webui_manager)