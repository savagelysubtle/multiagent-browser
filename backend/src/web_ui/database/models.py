"""Database models for ChromaDB integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DocumentModel(BaseModel):
    """Model for documents stored in ChromaDB."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = Field(..., description="Document content")
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str | None = Field(None, description="Source of the document")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CollectionConfig(BaseModel):
    """Configuration for a ChromaDB collection."""

    name: str = Field(..., description="Collection name")
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding_function: str | None = Field(
        None, description="Embedding function to use"
    )
    distance_threshold: float = Field(0.7, description="Similarity threshold")


class SearchResult(BaseModel):
    """Model for search results from ChromaDB."""

    id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    distance: float = Field(..., description="Distance score")
    relevance_score: float = Field(..., description="Relevance score (1 - distance)")

    @classmethod
    def from_chroma_result(
        cls, doc_id: str, content: str, metadata: dict[str, Any], distance: float
    ) -> SearchResult:
        """Create SearchResult from ChromaDB query result."""
        return cls(
            id=doc_id,
            content=content,
            metadata=metadata,
            distance=distance,
            relevance_score=1.0 - distance,
        )


class QueryRequest(BaseModel):
    """Model for search query requests."""

    query: str = Field(..., description="Search query text")
    collection_name: str = Field(..., description="Target collection name")
    limit: int = Field(
        default=10, description="Maximum number of results", ge=1, le=100
    )
    include_metadata: bool = Field(
        default=True, description="Include document metadata in results"
    )
    distance_threshold: float | None = Field(
        None, description="Maximum distance threshold", ge=0.0, le=2.0
    )
    metadata_filters: dict[str, Any] | None = Field(
        default_factory=dict, description="Metadata filters"
    )
