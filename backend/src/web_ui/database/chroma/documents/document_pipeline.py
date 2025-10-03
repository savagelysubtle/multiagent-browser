"""Document pipeline for integrating document editor with ChromaDB."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from web_ui.utils.logging_config import get_logger
from .chroma_manager import ChromaManager
from .models import DocumentModel, QueryRequest, SearchResult
from ...utils.utils import DatabaseUtils

logger = get_logger(__name__)


class DocumentPipeline:
    """Pipeline for processing documents from editor to database."""

    def __init__(self):
        """Initialize the document pipeline."""
        self.manager = ChromaManager()
        self.utils = DatabaseUtils()

        # Initialize specialized collections
        self._setup_document_collections()

    def _setup_document_collections(self):
        """Setup specialized collections for document management."""
        from .models import CollectionConfig

        collections = [
            # Main document storage
            CollectionConfig(
                name="documents",
                metadata={
                    "description": "Main document storage with full content",
                    "type": "documents",
                    "searchable": True,
                },
            ),
            # Vector search optimized for semantic search
            CollectionConfig(
                name="document_vectors",
                metadata={
                    "description": "Document chunks optimized for vector search",
                    "type": "vectors",
                    "chunk_size": 512,
                    "overlap": 50,
                },
            ),
            # Document relationships and references
            CollectionConfig(
                name="document_relations",
                metadata={
                    "description": "Relationships between documents, policies, and references",
                    "type": "relations",
                },
            ),
            # Policy manuals and templates
            CollectionConfig(
                name="policy_manuals",
                metadata={
                    "description": "Policy documents, templates, and guidelines",
                    "type": "policies",
                    "authority_level": "high",
                },
            ),
            # Document versions and history
            CollectionConfig(
                name="document_versions",
                metadata={
                    "description": "Document version history and changes",
                    "type": "versions",
                },
            ),
        ]

        for config in collections:
            try:
                self.manager.create_collection(config)
                logger.info(f"Initialized collection: {config.name}")
            except Exception as e:
                logger.error(f"Failed to initialize collection {config.name}: {e}")

    def process_document_from_editor(
        self,
        content: str,
        file_path: str,
        document_type: str = "document",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str, DocumentModel | None]:
        """Process a document from the editor and store in database."""
        try:
            # Extract document information
            filename = Path(file_path).name
            file_extension = Path(file_path).suffix.lower()

            # Generate document ID based on content hash
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            doc_id = f"{filename}_{content_hash}"

            # Prepare metadata
            doc_metadata = {
                "filename": filename,
                "file_extension": file_extension,
                "file_path": file_path,
                "document_type": document_type,
                "content_hash": content_hash,
                "word_count": len(content.split()),
                "character_count": len(content),
                "language": self._detect_language_from_extension(file_extension),
                "processed_at": datetime.now().isoformat(),
                **(metadata or {}),
            }

            # Create document model
            document = DocumentModel(
                id=doc_id,
                content=content,
                metadata=doc_metadata,
                source=f"document_editor:{file_path}",
                timestamp=datetime.now(),
            )

            # Store in main documents collection
            success = self.manager.add_document("documents", document)
            if not success:
                return False, "Failed to store document in main collection", None

            # Process for vector search if content is substantial
            if len(content) > 100:  # Only chunk substantial content
                self._process_for_vector_search(document)

            # Store version history
            self._store_document_version(document)

            logger.info(f"Successfully processed document: {doc_id}")
            return True, f"Document stored successfully: {filename}", document

        except Exception as e:
            logger.error(f"Error processing document from editor: {e}")
            return False, f"Error processing document: {str(e)}", None

    def _detect_language_from_extension(self, extension: str) -> str:
        """Detect programming/markup language from file extension."""
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".html": "html",
            ".css": "css",
            ".md": "markdown",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".sql": "sql",
            ".sh": "shell",
            ".bat": "batch",
            ".ps1": "powershell",
            ".txt": "text",
        }
        return language_map.get(extension, "text")

    def _process_for_vector_search(self, document: DocumentModel):
        """Process document for optimized vector search."""
        try:
            # Chunk the document content for better search
            chunks = self._chunk_content(document.content)

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document.id}_chunk_{i}"
                chunk_metadata = {
                    **document.metadata,
                    "parent_document_id": document.id,
                    "chunk_index": i,
                    "chunk_type": "content",
                    "total_chunks": len(chunks),
                }

                chunk_doc = DocumentModel(
                    id=chunk_id,
                    content=chunk,
                    metadata=chunk_metadata,
                    source=document.source,
                    timestamp=document.timestamp,
                )

                self.manager.add_document("document_vectors", chunk_doc)

            logger.debug(f"Created {len(chunks)} chunks for document {document.id}")

        except Exception as e:
            logger.error(f"Error processing document for vector search: {e}")

    def _chunk_content(
        self, content: str, chunk_size: int = 512, overlap: int = 50
    ) -> list[str]:
        """Chunk content into overlapping segments for better search."""
        if len(content) <= chunk_size:
            return [content]

        chunks = []
        words = content.split()

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i : i + chunk_size]
            chunk = " ".join(chunk_words)
            chunks.append(chunk)

            # Break if we've processed all words
            if i + chunk_size >= len(words):
                break

        return chunks

    def _store_document_version(self, document: DocumentModel):
        """Store document version for history tracking."""
        try:
            version_id = f"{document.id}_v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            version_metadata = {
                **document.metadata,
                "parent_document_id": document.id,
                "version_type": "save",
                "is_latest": True,
            }

            version_doc = DocumentModel(
                id=version_id,
                content=document.content,
                metadata=version_metadata,
                source=f"version:{document.source}",
                timestamp=document.timestamp,
            )

            self.manager.add_document("document_versions", version_doc)

        except Exception as e:
            logger.error(f"Error storing document version: {e}")

    def store_policy_manual(
        self,
        title: str,
        content: str,
        policy_type: str = "manual",
        authority_level: str = "medium",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Store a policy manual or template."""
        try:
            # Generate policy ID
            policy_id = f"policy_{hashlib.sha256(title.encode()).hexdigest()[:12]}"

            policy_metadata = {
                "title": title,
                "policy_type": policy_type,
                "authority_level": authority_level,
                "word_count": len(content.split()),
                "tags": self._extract_policy_tags(content),
                **(metadata or {}),
            }

            policy_doc = DocumentModel(
                id=policy_id,
                content=content,
                metadata=policy_metadata,
                source="policy_system",
                timestamp=datetime.now(),
            )

            success = self.manager.add_document("policy_manuals", policy_doc)
            if success:
                # Also process for vector search
                self._process_for_vector_search(policy_doc)
                return True, f"Policy manual stored: {title}"
            else:
                return False, "Failed to store policy manual"

        except Exception as e:
            logger.error(f"Error storing policy manual: {e}")
            return False, f"Error storing policy: {str(e)}"

    def _extract_policy_tags(self, content: str) -> str:
        """Extract relevant tags from policy content as a comma-separated string."""
        # Simple keyword-based tag extraction
        policy_keywords = [
            "procedure",
            "guideline",
            "standard",
            "requirement",
            "compliance",
            "security",
            "privacy",
            "approval",
            "workflow",
            "template",
            "format",
            "style",
        ]

        content_lower = content.lower()
        tags = [keyword for keyword in policy_keywords if keyword in content_lower]
        return ", ".join(tags)  # Return as comma-separated string for ChromaDB

    def create_document_relation(
        self,
        source_doc_id: str,
        target_doc_id: str,
        relation_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Create a relationship between two documents."""
        try:
            relation_id = f"rel_{source_doc_id}_{target_doc_id}_{relation_type}"

            relation_content = (
                f"Relationship: {source_doc_id} --{relation_type}--> {target_doc_id}"
            )
            relation_metadata = {
                "source_document": source_doc_id,
                "target_document": target_doc_id,
                "relation_type": relation_type,
                "relationship_strength": metadata.get("strength", 0.5)
                if metadata
                else 0.5,
                **(metadata or {}),
            }

            relation_doc = DocumentModel(
                id=relation_id,
                content=relation_content,
                metadata=relation_metadata,
                source="relation_system",
                timestamp=datetime.now(),
            )

            return self.manager.add_document("document_relations", relation_doc)

        except Exception as e:
            logger.error(f"Error creating document relation: {e}")
            return False

    def search_documents(
        self,
        query: str,
        collection_type: str = "documents",
        include_relations: bool = False,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search documents with optional relation inclusion."""
        try:
            # Map collection types
            collection_map = {
                "documents": "documents",
                "vectors": "document_vectors",
                "policies": "policy_manuals",
                "relations": "document_relations",
            }

            collection_name = collection_map.get(collection_type, "documents")

            query_request = QueryRequest(
                query=query,
                collection_name=collection_name,
                limit=limit,
                include_metadata=True,
            )

            results = self.manager.search(query_request)

            # If requested, include related documents
            if include_relations and results:
                results = self._enhance_with_relations(results)

            return results

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []

    def _enhance_with_relations(
        self, results: list[SearchResult]
    ) -> list[SearchResult]:
        """Enhance search results with related documents."""
        try:
            enhanced_results = []

            for result in results:
                # Find relations for this document
                relations_query = QueryRequest(
                    query=result.id,
                    collection_name="document_relations",
                    limit=5,
                    metadata_filters={"source_document": result.id},
                )

                relations = self.manager.search(relations_query)

                # Add relation information to metadata
                if relations:
                    result.metadata["related_documents"] = [
                        {
                            "target_id": rel.metadata.get("target_document"),
                            "relation_type": rel.metadata.get("relation_type"),
                            "strength": rel.metadata.get("relationship_strength", 0.5),
                        }
                        for rel in relations
                    ]

                enhanced_results.append(result)

            return enhanced_results

        except Exception as e:
            logger.error(f"Error enhancing results with relations: {e}")
            return results

    def get_document_suggestions(
        self, content: str, document_type: str = "document"
    ) -> dict[str, list[SearchResult]]:
        """Get suggestions for related policies and documents based on content."""
        try:
            suggestions = {}

            # Search for related policies
            policy_results = self.search_documents(
                query=content[:500],  # Use first 500 chars for search
                collection_type="policies",
                limit=5,
            )
            suggestions["related_policies"] = policy_results

            # Search for similar documents
            similar_docs = self.search_documents(
                query=content[:500], collection_type="vectors", limit=5
            )
            suggestions["similar_documents"] = similar_docs

            # Search for relevant templates
            template_query = f"template {document_type}"
            template_results = self.search_documents(
                query=template_query, collection_type="policies", limit=3
            )
            suggestions["templates"] = template_results

            return suggestions

        except Exception as e:
            logger.error(f"Error getting document suggestions: {e}")
            return {}

    def get_collection_stats(self) -> dict[str, Any]:
        """Get statistics about all document collections."""
        try:
            collections = [
                "documents",
                "document_vectors",
                "document_relations",
                "policy_manuals",
                "document_versions",
            ]

            stats = {}
            for collection in collections:
                collection_stats = self.manager.get_collection_stats(collection)
                stats[collection] = collection_stats

            # Calculate summary stats
            stats["summary"] = {
                "total_documents": sum(
                    s.get("document_count", 0) for s in stats.values()
                ),
                "collections_active": len(
                    [s for s in stats.values() if s.get("document_count", 0) > 0]
                ),
                "last_updated": datetime.now().isoformat(),
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
