"""ChromaDB manager for document storage and retrieval."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
import chromadb
from chromadb.api.models.Collection import Collection

from .connection import get_chroma_client, get_db_config
from .models import DocumentModel, CollectionConfig, SearchResult, QueryRequest

logger = logging.getLogger(__name__)


class ChromaManager:
    """Main interface for ChromaDB operations."""
    
    def __init__(self):
        """Initialize the ChromaDB manager."""
        self.client = get_chroma_client()
        self.config = get_db_config()
        self._collections_cache: Dict[str, Collection] = {}
        
    def create_collection(self, config: CollectionConfig) -> Collection:
        """Create a new collection in ChromaDB."""
        try:
            collection_name = f"{self.config['collection_prefix']}{config.name}"
            
            # Check if collection already exists
            try:
                collection = self.client.get_collection(name=collection_name)
                logger.info(f"Collection '{collection_name}' already exists")
                return collection
            except Exception:
                # Collection doesn't exist, create it
                pass
            
            collection = self.client.create_collection(
                name=collection_name,
                metadata=config.metadata or {}
            )
            
            self._collections_cache[collection_name] = collection
            logger.info(f"Created collection: {collection_name}")
            return collection
            
        except Exception as e:
            logger.error(f"Failed to create collection '{config.name}': {e}")
            raise
    
    def get_collection(self, name: str) -> Optional[Collection]:
        """Get an existing collection."""
        try:
            collection_name = f"{self.config['collection_prefix']}{name}"
            
            # Check cache first
            if collection_name in self._collections_cache:
                return self._collections_cache[collection_name]
            
            collection = self.client.get_collection(name=collection_name)
            self._collections_cache[collection_name] = collection
            return collection
            
        except Exception as e:
            logger.warning(f"Collection '{name}' not found: {e}")
            return None
    
    def list_collections(self) -> List[str]:
        """List all collections."""
        try:
            collections = self.client.list_collections()
            prefix = self.config['collection_prefix']
            
            # Remove prefix from collection names
            return [
                col.name[len(prefix):] if col.name.startswith(prefix) else col.name
                for col in collections
            ]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        try:
            collection_name = f"{self.config['collection_prefix']}{name}"
            self.client.delete_collection(name=collection_name)
            
            # Remove from cache
            if collection_name in self._collections_cache:
                del self._collections_cache[collection_name]
            
            logger.info(f"Deleted collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete collection '{name}': {e}")
            return False
    
    def add_document(self, collection_name: str, document: DocumentModel) -> bool:
        """Add a document to a collection."""
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                # Create collection if it doesn't exist
                config = CollectionConfig(name=collection_name)
                collection = self.create_collection(config)
            
            # Prepare metadata
            metadata = {
                **document.metadata,
                'source': document.source,
                'timestamp': document.timestamp.isoformat()
            }
            
            collection.add(
                documents=[document.content],
                metadatas=[metadata],
                ids=[document.id]
            )
            
            logger.debug(f"Added document {document.id} to collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document to collection '{collection_name}': {e}")
            return False
    
    def add_documents(self, collection_name: str, documents: List[DocumentModel]) -> Tuple[int, int]:
        """Add multiple documents to a collection."""
        success_count = 0
        failed_count = 0
        
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                config = CollectionConfig(name=collection_name)
                collection = self.create_collection(config)
            
            # Prepare batch data
            document_texts = []
            metadata_list = []
            ids = []
            
            for doc in documents:
                document_texts.append(doc.content)
                metadata = {
                    **doc.metadata,
                    'source': doc.source,
                    'timestamp': doc.timestamp.isoformat()
                }
                metadata_list.append(metadata)
                ids.append(doc.id)
            
            collection.add(
                documents=document_texts,
                metadatas=metadata_list,
                ids=ids
            )
            
            success_count = len(documents)
            logger.info(f"Added {success_count} documents to collection {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to add documents to collection '{collection_name}': {e}")
            failed_count = len(documents)
        
        return success_count, failed_count
    
    def search(self, query_request: QueryRequest) -> List[SearchResult]:
        """Search for documents in a collection."""
        try:
            collection = self.get_collection(query_request.collection_name)
            if collection is None:
                logger.warning(f"Collection '{query_request.collection_name}' not found")
                return []
            
            # Prepare where clause for metadata filtering
            where_clause = query_request.metadata_filters if query_request.metadata_filters else None
            
            # Perform the search
            results = collection.query(
                query_texts=[query_request.query],
                n_results=query_request.limit,
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Process results
            search_results = []
            if results['documents'] and results['documents'][0]:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(documents)
                distances = results['distances'][0] if results['distances'] else [0.0] * len(documents)
                ids = results['ids'][0] if results['ids'] else [str(uuid4()) for _ in documents]
                
                for i, (doc_id, content, metadata, distance) in enumerate(zip(ids, documents, metadatas, distances)):
                    # Apply distance threshold if specified
                    if query_request.distance_threshold is not None and distance > query_request.distance_threshold:
                        continue
                    
                    result = SearchResult.from_chroma_result(
                        doc_id=doc_id,
                        content=content,
                        metadata=metadata if query_request.include_metadata else {},
                        distance=distance
                    )
                    search_results.append(result)
            
            logger.debug(f"Found {len(search_results)} results for query in collection {query_request.collection_name}")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed in collection '{query_request.collection_name}': {e}")
            return []
    
    def get_document(self, collection_name: str, document_id: str) -> Optional[DocumentModel]:
        """Get a specific document by ID."""
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None
            
            results = collection.get(
                ids=[document_id],
                include=['documents', 'metadatas']
            )
            
            if results['documents'] and results['documents'][0]:
                content = results['documents'][0]
                metadata = results['metadatas'][0] if results['metadatas'] else {}
                
                # Extract timestamp and source from metadata
                timestamp_str = metadata.pop('timestamp', None)
                source = metadata.pop('source', None)
                
                # Parse timestamp
                from datetime import datetime
                timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()
                
                return DocumentModel(
                    id=document_id,
                    content=content,
                    metadata=metadata,
                    source=source,
                    timestamp=timestamp
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document '{document_id}' from collection '{collection_name}': {e}")
            return None
    
    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """Delete a document from a collection."""
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return False
            
            collection.delete(ids=[document_id])
            logger.debug(f"Deleted document {document_id} from collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document '{document_id}' from collection '{collection_name}': {e}")
            return False
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a collection."""
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return {}
            
            count = collection.count()
            
            return {
                'name': collection_name,
                'document_count': count,
                'metadata': collection.metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for collection '{collection_name}': {e}")
            return {}
    
    def clear_cache(self) -> None:
        """Clear the collections cache."""
        self._collections_cache.clear()
        logger.debug("Cleared collections cache")