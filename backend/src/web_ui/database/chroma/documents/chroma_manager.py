"""
ChromaDB Manager for Document Storage and Retrieval.

This class provides a high-level interface for interacting with a specific
ChromaDB collection, handling document addition, querying, and management.
"""

from typing import Any, Dict, List, Optional
import chromadb
from web_ui.utils.logging_config import get_logger
from ..connection import get_chroma_client

logger = get_logger(__name__)

class ChromaManager:
    """Manages operations for a specific ChromaDB collection."""

    def __init__(self, collection_name: str, embedding_function: Optional[Any] = None):
        """Initialize the ChromaManager for a specific collection."""
        logger.info(f"Initializing ChromaManager for collection: '{collection_name}'")
        self.client = get_chroma_client()
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self) -> chromadb.Collection:
        """Get or create the ChromaDB collection."""
        logger.debug(f"Getting or creating collection: '{self.collection_name}'")
        try:
            collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}  # Use cosine distance for embeddings
            )
            logger.info(f"Successfully accessed collection '{self.collection_name}'.")
            return collection
        except Exception as e:
            logger.exception(f"Failed to get or create collection '{self.collection_name}': {e}")
            raise

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        """Add documents to the collection."""
        if not documents:
            logger.warning("add_documents called with no documents to add.")
            return
        
        logger.info(f"Adding {len(documents)} documents to collection '{self.collection_name}'.")
        try:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(f"Successfully added {len(documents)} documents.")
        except Exception as e:
            logger.exception(f"Failed to add documents to collection '{self.collection_name}': {e}")
            raise

    def query(self, query_texts: List[str], n_results: int = 5, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query the collection for similar documents."""
        logger.debug(f"Querying collection '{self.collection_name}' with {len(query_texts)} queries.")
        try:
            results = self.collection.query(query_texts=query_texts, n_results=n_results, where=where)
            logger.info(f"Query returned {len(results.get('ids', [[]])[0])} results for the first query.")
            return results
        except Exception as e:
            logger.exception(f"Failed to query collection '{self.collection_name}': {e}")
            raise

    def delete_documents(self, ids: List[str]) -> None:
        """Delete documents from the collection by their IDs."""
        if not ids:
            logger.warning("delete_documents called with no IDs.")
            return

        logger.info(f"Deleting {len(ids)} documents from collection '{self.collection_name}'.")
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Successfully deleted documents with IDs: {ids}")
        except Exception as e:
            logger.exception(f"Failed to delete documents from collection '{self.collection_name}': {e}")
            raise

    def get_collection_status(self) -> Dict[str, Any]:
        """Get the status of the collection, including the number of documents."""
        logger.debug(f"Getting status for collection '{self.collection_name}'.")
        try:
            count = self.collection.count()
            status = {"name": self.collection_name, "document_count": count}
            logger.info(f"Collection '{self.collection_name}' contains {count} documents.")
            return status
        except Exception as e:
            logger.exception(f"Failed to get status for collection '{self.collection_name}': {e}")
            raise