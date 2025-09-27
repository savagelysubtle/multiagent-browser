"""Data models for the database layer."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentModel(BaseModel):
    """Model for document storage in ChromaDB."""
    
    id: str = Field(..., description="Unique identifier for the document")
    content: str = Field(..., description="Text content of the document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    source: Optional[str] = Field(None, description="Source of the document")
    timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CollectionConfig(BaseModel):
    """Configuration for ChromaDB collections."""
    
    name: str = Field(..., description="Collection name")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Collection metadata")
    embedding_function: Optional[str] = Field(None, description="Embedding function identifier")
    distance_metric: str = Field(default="cosine", description="Distance metric for similarity search")


class SearchResult(BaseModel):
    """Model for search results from ChromaDB."""
    
    id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    distance: float = Field(..., description="Distance score")
    relevance_score: float = Field(..., description="Relevance score (1 - distance)")
    
    @classmethod
    def from_chroma_result(cls, doc_id: str, content: str, metadata: Dict[str, Any], distance: float) -> "SearchResult":
        """Create SearchResult from ChromaDB query result."""
        return cls(
            id=doc_id,
            content=content,
            metadata=metadata,
            distance=distance,
            relevance_score=1.0 - distance
        )


class QueryRequest(BaseModel):
    """Model for search query requests."""
    
    query: str = Field(..., description="Search query text")
    collection_name: str = Field(..., description="Target collection name")
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=100)
    include_metadata: bool = Field(default=True, description="Include document metadata in results")
    distance_threshold: Optional[float] = Field(None, description="Maximum distance threshold", ge=0.0, le=2.0)
    metadata_filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata filters")