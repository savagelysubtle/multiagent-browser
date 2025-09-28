"""
Shared dependencies for API routes.

Provides common dependencies like orchestrator instance, database connections, etc.
"""

from fastapi import HTTPException

from ..agent.document_editor import DocumentEditingAgent
from ..agent.orchestrator.simple_orchestrator import SimpleAgentOrchestrator

# Global references to singleton instances, managed by the server's lifespan
_orchestrator: SimpleAgentOrchestrator | None = None
_document_agent: DocumentEditingAgent | None = None


def set_orchestrator(orchestrator: SimpleAgentOrchestrator) -> None:
    """Set the global orchestrator instance (called at startup)."""
    global _orchestrator
    _orchestrator = orchestrator


def set_document_agent(agent: DocumentEditingAgent) -> None:
    """Set the global document agent instance (called at startup)."""
    global _document_agent
    _document_agent = agent


def get_orchestrator() -> SimpleAgentOrchestrator:
    """Dependency to get the current orchestrator instance."""
    if _orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator is not available or still initializing.",
        )
    return _orchestrator


def get_document_agent() -> DocumentEditingAgent:
    """Dependency to get the current document agent instance."""
    if _document_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Document agent is not available or still initializing.",
        )
    return _document_agent
