"""
Shared dependencies for API routes.

Provides common dependencies like orchestrator instance, database connections, etc.
"""

from ..agent.orchestrator.simple_orchestrator import SimpleAgentOrchestrator

# Global reference to orchestrator instance
_orchestrator: SimpleAgentOrchestrator | None = None


def set_orchestrator(orchestrator: SimpleAgentOrchestrator) -> None:
    """Set the global orchestrator instance."""
    global _orchestrator
    _orchestrator = orchestrator


def get_orchestrator() -> SimpleAgentOrchestrator:
    """Get the current orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError(
            "Orchestrator not initialized. Server may still be starting up."
        )
    return _orchestrator


# Optional dependency that returns None if orchestrator not ready
def get_orchestrator_optional() -> SimpleAgentOrchestrator | None:
    """Get orchestrator instance or None if not initialized."""
    return _orchestrator
