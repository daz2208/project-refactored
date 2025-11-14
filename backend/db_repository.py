"""
Database Repository for Knowledge Bank (Phase 6.5).

SQLAlchemy-based repository replacing file storage.
Implements same interface as KnowledgeBankRepository for drop-in replacement.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import DocumentMetadata, Cluster, Concept
from .db_models import DBUser, DBCluster, DBDocument, DBConcept, DBVectorDocument
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class DatabaseKnowledgeBankRepository:
    """
    Database-backed repository for managing documents, metadata, clusters, and users.

    Uses SQLAlchemy for persistence instead of file storage.
    Thread-safe with async locking.
    """

    def __init__(self, db_session: Session, vector_dim: int = 256):
        """
        Initialize database repository.

        Args:
            db_session: SQLAlchemy database session
            vector_dim: Dimension for vector store
        """
        self.db = db_session
        self.vector_dim = vector_dim

        # Vector store for semantic search
        self.vector_store = VectorStore(dim=vector_dim)

        # Async lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Load vector store from database
        self._load_vector_store()

    def _load_vector_store(self) -> None:
        """Load documents into vector store for semantic search."""
        try:
            vector_docs = self.db.query(DBVectorDocument).all()
            for vdoc in vector_docs:
                self.vector_store.add_document(vdoc.content)
            logger.info(f"Loaded {len(vector_docs)} documents into vector store")
        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")

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
            # Add to vector store first to get doc_id
            doc_id = self.vector_store.add_document(content)

            # Create database document
            db_doc = DBDocument(
                doc_id=doc_id,
                owner_username=metadata.owner,
                cluster_id=metadata.cluster_id,
                source_type=metadata.source_type,
                source_url=metadata.source_url,
                filename=metadata.filename,
                image_path=metadata.image_path,
                content_length=metadata.content_length,
                skill_level=metadata.skill_level,
                ingested_at=metadata.ingested_at
            )
            self.db.add(db_doc)
            self.db.flush()  # Get the database ID

            # Add concepts
            for concept in metadata.concepts:
                db_concept = DBConcept(
                    document_id=db_doc.id,
                    name=concept.name,
                    category=concept.category,
                    confidence=concept.confidence
                )
                self.db.add(db_concept)

            # Add vector document content
            db_vector_doc = DBVectorDocument(
                doc_id=doc_id,
                content=content
            )
            self.db.add(db_vector_doc)

            self.db.commit()
            logger.debug(f"Added document {doc_id}")
            return doc_id

    async def get_document(self, doc_id: int) -> Optional[str]:
        """Get document content by ID."""
        vdoc = self.db.query(DBVectorDocument).filter_by(doc_id=doc_id).first()
        return vdoc.content if vdoc else None

    async def get_document_metadata(self, doc_id: int) -> Optional[DocumentMetadata]:
        """Get document metadata by ID."""
        db_doc = self.db.query(DBDocument).filter_by(doc_id=doc_id).first()
        if not db_doc:
            return None

        # Convert to Pydantic model
        concepts = [
            Concept(
                name=c.name,
                category=c.category,
                confidence=c.confidence
            )
            for c in db_doc.concepts
        ]

        return DocumentMetadata(
            doc_id=db_doc.doc_id,
            owner=db_doc.owner_username,
            source_type=db_doc.source_type,
            source_url=db_doc.source_url,
            filename=db_doc.filename,
            image_path=db_doc.image_path,
            concepts=concepts,
            skill_level=db_doc.skill_level,
            cluster_id=db_doc.cluster_id,
            ingested_at=db_doc.ingested_at.isoformat() if db_doc.ingested_at else None,
            content_length=db_doc.content_length
        )

    async def get_all_documents(self) -> Dict[int, str]:
        """Get all document contents."""
        vdocs = self.db.query(DBVectorDocument).all()
        return {vdoc.doc_id: vdoc.content for vdoc in vdocs}

    async def get_all_metadata(self) -> Dict[int, DocumentMetadata]:
        """Get all document metadata."""
        db_docs = self.db.query(DBDocument).all()
        result = {}
        for db_doc in db_docs:
            meta = await self.get_document_metadata(db_doc.doc_id)
            if meta:
                result[db_doc.doc_id] = meta
        return result

    async def delete_document(self, doc_id: int) -> bool:
        """
        Delete a document and its metadata.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            db_doc = self.db.query(DBDocument).filter_by(doc_id=doc_id).first()
            if not db_doc:
                return False

            # Delete vector document
            self.db.query(DBVectorDocument).filter_by(doc_id=doc_id).delete()

            # Delete document (concepts deleted via cascade)
            self.db.delete(db_doc)
            self.db.commit()

            # Remove from vector store
            # Note: VectorStore doesn't have delete, would need to rebuild
            logger.debug(f"Deleted document {doc_id}")
            return True

    # =============================================================================
    # CLUSTER OPERATIONS
    # =============================================================================

    async def add_cluster(self, cluster: Cluster) -> int:
        """
        Add a new cluster.

        Args:
            cluster: Cluster object

        Returns:
            Cluster ID
        """
        async with self._lock:
            db_cluster = DBCluster(
                name=cluster.name,
                primary_concepts=cluster.primary_concepts,
                skill_level=cluster.skill_level
            )
            self.db.add(db_cluster)
            self.db.commit()
            self.db.refresh(db_cluster)
            logger.debug(f"Added cluster {db_cluster.id}: {cluster.name}")
            return db_cluster.id

    async def get_cluster(self, cluster_id: int) -> Optional[Cluster]:
        """Get cluster by ID."""
        db_cluster = self.db.query(DBCluster).filter_by(id=cluster_id).first()
        if not db_cluster:
            return None

        # Get document IDs in this cluster
        doc_ids = [doc.doc_id for doc in db_cluster.documents]

        return Cluster(
            id=db_cluster.id,
            name=db_cluster.name,
            doc_ids=doc_ids,
            primary_concepts=db_cluster.primary_concepts,
            skill_level=db_cluster.skill_level,
            doc_count=len(doc_ids)
        )

    async def get_all_clusters(self) -> Dict[int, Cluster]:
        """Get all clusters."""
        db_clusters = self.db.query(DBCluster).all()
        result = {}
        for db_cluster in db_clusters:
            cluster = await self.get_cluster(db_cluster.id)
            if cluster:
                result[db_cluster.id] = cluster
        return result

    async def update_cluster(self, cluster: Cluster) -> bool:
        """
        Update an existing cluster.

        Args:
            cluster: Cluster with updated data

        Returns:
            True if updated, False if not found
        """
        async with self._lock:
            db_cluster = self.db.query(DBCluster).filter_by(id=cluster.id).first()
            if not db_cluster:
                return False

            db_cluster.name = cluster.name
            db_cluster.primary_concepts = cluster.primary_concepts
            db_cluster.skill_level = cluster.skill_level

            self.db.commit()
            logger.debug(f"Updated cluster {cluster.id}")
            return True

    async def add_document_to_cluster(self, doc_id: int, cluster_id: int) -> bool:
        """
        Add a document to a cluster.

        Args:
            doc_id: Document ID
            cluster_id: Cluster ID

        Returns:
            True if successful, False if document or cluster not found
        """
        async with self._lock:
            db_doc = self.db.query(DBDocument).filter_by(doc_id=doc_id).first()
            if not db_doc:
                return False

            db_cluster = self.db.query(DBCluster).filter_by(id=cluster_id).first()
            if not db_cluster:
                return False

            db_doc.cluster_id = cluster_id
            self.db.commit()
            logger.debug(f"Added document {doc_id} to cluster {cluster_id}")
            return True

    # =============================================================================
    # USER OPERATIONS
    # =============================================================================

    async def add_user(self, username: str, hashed_password: str) -> None:
        """
        Add a new user.

        Args:
            username: Username
            hashed_password: Bcrypt hashed password
        """
        async with self._lock:
            db_user = DBUser(
                username=username,
                hashed_password=hashed_password
            )
            self.db.add(db_user)
            self.db.commit()
            logger.debug(f"Added user {username}")

    async def get_user(self, username: str) -> Optional[str]:
        """
        Get user's hashed password.

        Args:
            username: Username to lookup

        Returns:
            Hashed password or None if user not found
        """
        db_user = self.db.query(DBUser).filter_by(username=username).first()
        return db_user.hashed_password if db_user else None

    # =============================================================================
    # SEARCH OPERATIONS
    # =============================================================================

    async def search_documents(
        self,
        query: str,
        top_k: int = 10,
        allowed_doc_ids: Optional[List[int]] = None
    ) -> List[Tuple[int, float]]:
        """
        Semantic search for documents.

        Args:
            query: Search query
            top_k: Number of results to return
            allowed_doc_ids: Optional list of allowed document IDs

        Returns:
            List of (doc_id, score) tuples
        """
        return self.vector_store.search(query, top_k=top_k, allowed_ids=allowed_doc_ids)
