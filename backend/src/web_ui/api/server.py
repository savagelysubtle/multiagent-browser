"""
FastAPI server configuration and startup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from ..utils.logging_config import get_logger

    logger = get_logger(__name__)
except ImportError:
    # Fallback if logging config is not available
    import logging

    logger = logging.getLogger(__name__)
    logger.warning("Could not import centralized logging, using fallback")

# Create FastAPI application
app = FastAPI(
    title="Web-UI API", description="Unified AI Research Platform API", version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],  # Allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
try:
    from .auth.router import router as auth_router

    app.include_router(auth_router, prefix="/api", tags=["authentication"])
    logger.info("Authentication router loaded successfully")
except ImportError as e:
    logger.error(f"Could not load auth router: {e}")
    logger.error("Authentication functionality will not be available")
except Exception as e:
    logger.error(f"Error loading auth router: {e}")
    logger.error("Authentication functionality will not be available")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "web-ui-api"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Web-UI API",
        "version": "1.0.0",
        "description": "Unified AI Research Platform API",
        "docs": "/docs",
        "health": "/health",
    }


# The app instance is created above and can be imported by main.py
# No need for a run_api_server function anymore since main.py handles uvicorn directly
