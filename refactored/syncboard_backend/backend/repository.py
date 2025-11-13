"""
Repository pattern for Knowledge Bank data access.

Encapsulates all data access logic with thread-safe operations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple

from .models import DocumentMetadata, Cluster, Concept
from .vector_store import VectorStore
from .storage import load_storage, save_storage

logger = logging.getLogger(__name__)


class KnowledgeBankRepository:
    """
    Repository for managing documents, metadata, clusters, and users.

    Provides thread-safe access to all data with async locking.
    Handles persistence to disk through storage module.
    """

    def __init__(self, storage_path: str, vector_dim: int = 256):
        """
        Initialize repository.

        Args:
            storage_path: Path to JSON storage file
            vector_dim: Dimension for vector store
        """
        self.storage_path = storage_path
        self.vector_dim = vector_dim

        # Data stores
        self.documents: Dict[int, str] = {}
        self.metadata: Dict[int, DocumentMetadata] = {}
        self.clusters: Dict[int, Cluster] = {}
        self.users: Dict[str, str] = {}

        # Vector store for semantic search
        self.vector_store = VectorStore(dim=vector_dim)

        # Async lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Load existing data
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load data from disk storage."""
        try:
            docs, meta, clusters, users = load_storage(self.storage_path)
            self.documents = docs
            self.metadata = meta
            self.clusters = clusters
            self.users = users

            # Rebuild vector store from loaded documents
            if self.documents:
                texts = [self.documents[doc_id] for doc_id in sorted(self.documents.keys())]
                self.vector_store.add_documents_batch(texts)

            logger.info(f"Loaded {len(self.documents)} documents, {len(self.clusters)} clusters")
        except FileNotFoundError:
            logger.info(f"No existing storage found at {self.storage_path}, starting fresh")

    async def _save_to_disk(self) -> None:
        """Persist data to disk atomically."""
        save_storage(
            self.storage_path,
            self.documents,
            self.metadata,
            self.clusters,
            self.users
        )
        logger.debug(f"Saved {len(self.documents)} documents to disk")

    # =============================================================================
    # DOCUMENT OPERATIONS
    # =============================================================================

    async def add_document(
        self,
        content: str,
        metadata: DocumentMetadata
    ) -> int:
        """
        Add a document to the repository.

        Args:
            content: Full document text
            metadata: Document metadata

        Returns:
            Document ID
        """
        async with self._lock:
            # Get next document ID
            doc_id = len(self.documents)

            # Store document and metadata
            self.documents[doc_id] = content
            self.metadata[doc_id] = metadata

            # Add to vector store for search
            self.vector_store.add_document(content)

            # Persist to disk
            await self._save_to_disk()

            logger.info(f"Added document {doc_id}: {metadata.source_type}")
            return doc_id

    async def get_document(self, doc_id: int) -> Optional[str]:
        """Get document content by ID."""
        async with self._lock:
            return self.documents.get(doc_id)

    async def get_document_metadata(self, doc_id: int) -> Optional[DocumentMetadata]:
        """Get document metadata by ID."""
        async with self._lock:
            return self.metadata.get(doc_id)

    async def get_all_documents(self) -> Dict[int, str]:
        """Get all documents (copy)."""
        async with self._lock:
            return dict(self.documents)

    async def get_all_metadata(self) -> Dict[int, DocumentMetadata]:
        """Get all metadata (copy)."""
        async with self._lock:
            return dict(self.metadata)

    async def delete_document(self, doc_id: int) -> bool:
        """
        Delete a document from repository.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if doc_id not in self.documents:
                return False

            # Remove from stores
            del self.documents[doc_id]
            del self.metadata[doc_id]

            # Remove from vector store
            self.vector_store.remove_document(doc_id)

            # Remove from clusters
            for cluster in self.clusters.values():
                if doc_id in cluster.doc_ids:
                    cluster.doc_ids.remove(doc_id)

            # Persist to disk
            await self._save_to_disk()

            logger.info(f"Deleted document {doc_id}")
            return True

    # =============================================================================
    # CLUSTER OPERATIONS
    # =============================================================================

    async def add_cluster(self, cluster: Cluster) -> int:
        """
        Add a cluster to the repository.

        Args:
            cluster: Cluster object

        Returns:
            Cluster ID
        """
        async with self._lock:
            cluster_id = len(self.clusters)
            cluster.id = cluster_id
            self.clusters[cluster_id] = cluster

            await self._save_to_disk()

            logger.info(f"Added cluster {cluster_id}: {cluster.name}")
            return cluster_id

    async def get_cluster(self, cluster_id: int) -> Optional[Cluster]:
        """Get cluster by ID."""
        async with self._lock:
            return self.clusters.get(cluster_id)

    async def get_all_clusters(self) -> Dict[int, Cluster]:
        """Get all clusters (copy)."""
        async with self._lock:
            return dict(self.clusters)

    async def update_cluster(self, cluster: Cluster) -> bool:
        """
        Update an existing cluster.

        Args:
            cluster: Updated cluster object

        Returns:
            True if updated, False if not found
        """
        async with self._lock:
            if cluster.id not in self.clusters:
                return False

            self.clusters[cluster.id] = cluster
            await self._save_to_disk()

            logger.info(f"Updated cluster {cluster.id}")
            return True

    async def add_document_to_cluster(self, doc_id: int, cluster_id: int) -> bool:
        """
        Add a document to a cluster.

        Args:
            doc_id: Document ID
            cluster_id: Cluster ID

        Returns:
            True if added, False if cluster not found
        """
        async with self._lock:
            cluster = self.clusters.get(cluster_id)
            if not cluster:
                return False

            if doc_id not in cluster.doc_ids:
                cluster.doc_ids.append(doc_id)
                await self._save_to_disk()
                logger.debug(f"Added doc {doc_id} to cluster {cluster_id}")

            return True

    # =============================================================================
    # USER OPERATIONS
    # =============================================================================

    async def add_user(self, username: str, hashed_password: str) -> None:
        """
        Add a user to the repository.

        Args:
            username: Username
            hashed_password: Hashed password
        """
        async with self._lock:
            self.users[username] = hashed_password
            await self._save_to_disk()
            logger.info(f"Added user: {username}")

    async def get_user(self, username: str) -> Optional[str]:
        """Get user's hashed password by username."""
        async with self._lock:
            return self.users.get(username)

    # =============================================================================
    # SEARCH OPERATIONS
    # =============================================================================

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        cluster_id: Optional[int] = None
    ) -> List[Tuple[int, float, str]]:
        """
        Search documents using vector similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            cluster_id: Optional cluster ID to filter by

        Returns:
            List of (doc_id, score, snippet) tuples
        """
        async with self._lock:
            # Get allowed doc IDs if filtering by cluster
            allowed_doc_ids = None
            if cluster_id is not None:
                cluster = self.clusters.get(cluster_id)
                if cluster:
                    allowed_doc_ids = cluster.doc_ids

            # Search vector store
            results = self.vector_store.search(
                query=query,
                top_k=top_k,
                allowed_doc_ids=allowed_doc_ids
            )

            return results
