"""
Agent adapters package.

This package contains adapter classes that wrap existing agents
to work with the SimpleAgentOrchestrator.
"""

from .browser_use_adapter import BrowserUseAdapter
from .deep_research_adapter import DeepResearchAdapter
from .document_editor_adapter import DocumentEditorAdapter

__all__ = ["DocumentEditorAdapter", "BrowserUseAdapter", "DeepResearchAdapter"]
