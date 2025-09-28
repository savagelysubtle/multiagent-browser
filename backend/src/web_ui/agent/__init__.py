"""
Agent package for web-ui.

This package contains the agent orchestration system, adapters,
and Google A2A interface preparation.
"""

from .adapters import BrowserUseAdapter, DeepResearchAdapter, DocumentEditorAdapter
from .google_a2a.interface import (
    A2AMessage,
    A2AMessageType,
    GoogleA2AInterface,
    a2a_interface,
    initialize_a2a_interface,
)
from .orchestrator.simple_orchestrator import (
    AgentTask,
    SimpleAgentOrchestrator,
    initialize_orchestrator,
    orchestrator,
)

__all__ = [
    "SimpleAgentOrchestrator",
    "AgentTask",
    "orchestrator",
    "initialize_orchestrator",
    "DocumentEditorAdapter",
    "BrowserUseAdapter",
    "DeepResearchAdapter",
    "GoogleA2AInterface",
    "A2AMessage",
    "A2AMessageType",
    "a2a_interface",
    "initialize_a2a_interface",
]
