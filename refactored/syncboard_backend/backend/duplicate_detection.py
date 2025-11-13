"""
Duplicate detection service (Phase 7.2).

Uses TF-IDF vector similarity to identify potentially duplicate documents.
"""

import logging
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from .db_models import DBDocument, DBVectorDocument
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Detect duplicate or highly similar documents."""

    def __init__(self, db: Session, vector_store: VectorStore):
        """
        Initialize duplicate detector.

        Args:
            db: Database session
            vector_store: Vector store for similarity calculations
        """
        self.db = db
        self.vector_store = vector_store

    def find_duplicates(
        self,
        username: str,
        similarity_threshold: float = 0.85,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find duplicate documents based on content similarity.

        Args:
            username: Username to filter documents
            similarity_threshold: Minimum similarity score (0-1) to consider duplicates
            limit: Maximum number of duplicate groups to return

        Returns:
            List of duplicate groups with similarity scores
        """
        # Get user's documents
        user_docs = self.db.query(DBDocument).filter(
            DBDocument.owner_username == username
        ).all()

        if len(user_docs) < 2:
            return []

        doc_ids = [doc.doc_id for doc in user_docs]

        # Find duplicates using vector similarity
        duplicate_groups = []

        # Track which documents we've already grouped
        grouped_docs = set()

        for i, doc_id1 in enumerate(doc_ids):
            if doc_id1 in grouped_docs:
                continue

            # Find similar documents
            similar_docs = self.vector_store.search_by_doc_id(
                doc_id1,
                top_k=min(20, len(doc_ids))
            )

            # Filter by similarity threshold and user's documents
            duplicates = []
            for sim_doc_id, similarity in similar_docs:
                if (
                    sim_doc_id != doc_id1
                    and sim_doc_id in doc_ids
                    and sim_doc_id not in grouped_docs
                    and similarity >= similarity_threshold
                ):
                    duplicates.append({
                        "doc_id": sim_doc_id,
                        "similarity": float(similarity)
                    })
                    grouped_docs.add(sim_doc_id)

            if duplicates:
                # Get document metadata
                main_doc = next((d for d in user_docs if d.doc_id == doc_id1), None)

                duplicate_ids = [d["doc_id"] for d in duplicates]
                duplicate_docs_meta = [
                    d for d in user_docs if d.doc_id in duplicate_ids
                ]

                group = {
                    "primary_doc": {
                        "doc_id": doc_id1,
                        "source_type": main_doc.source_type if main_doc else None,
                        "skill_level": main_doc.skill_level if main_doc else None,
                        "cluster_id": main_doc.cluster_id if main_doc else None,
                        "created_at": main_doc.created_at.isoformat() if main_doc and main_doc.created_at else None
                    },
                    "duplicates": [
                        {
                            "doc_id": dup["doc_id"],
                            "similarity": dup["similarity"],
                            "source_type": next(
                                (d.source_type for d in duplicate_docs_meta if d.doc_id == dup["doc_id"]),
                                None
                            ),
                            "skill_level": next(
                                (d.skill_level for d in duplicate_docs_meta if d.doc_id == dup["doc_id"]),
                                None
                            ),
                            "cluster_id": next(
                                (d.cluster_id for d in duplicate_docs_meta if d.doc_id == dup["doc_id"]),
                                None
                            ),
                            "created_at": next(
                                (d.created_at.isoformat() for d in duplicate_docs_meta if d.doc_id == dup["doc_id"] and d.created_at),
                                None
                            )
                        }
                        for dup in duplicates
                    ],
                    "group_size": len(duplicates) + 1
                }

                duplicate_groups.append(group)
                grouped_docs.add(doc_id1)

                if len(duplicate_groups) >= limit:
                    break

        # Sort by group size (largest groups first)
        duplicate_groups.sort(key=lambda g: g["group_size"], reverse=True)

        return duplicate_groups

    def get_duplicate_content(
        self,
        doc_id1: int,
        doc_id2: int
    ) -> Dict[str, Any]:
        """
        Get content and metadata for two documents to compare.

        Args:
            doc_id1: First document ID
            doc_id2: Second document ID

        Returns:
            Dictionary with both documents' content and metadata
        """
        doc1_vec = self.db.query(DBVectorDocument).filter(
            DBVectorDocument.doc_id == doc_id1
        ).first()

        doc2_vec = self.db.query(DBVectorDocument).filter(
            DBVectorDocument.doc_id == doc_id2
        ).first()

        doc1_meta = self.db.query(DBDocument).filter(
            DBDocument.doc_id == doc_id1
        ).first()

        doc2_meta = self.db.query(DBDocument).filter(
            DBDocument.doc_id == doc_id2
        ).first()

        # Calculate similarity
        similarity = 0.0
        if doc1_vec and doc2_vec:
            results = self.vector_store.search_by_doc_id(doc_id1, top_k=100)
            for did, sim in results:
                if did == doc_id2:
                    similarity = float(sim)
                    break

        return {
            "doc1": {
                "doc_id": doc_id1,
                "content": doc1_vec.content if doc1_vec else "",
                "source_type": doc1_meta.source_type if doc1_meta else None,
                "skill_level": doc1_meta.skill_level if doc1_meta else None,
                "cluster_id": doc1_meta.cluster_id if doc1_meta else None,
                "created_at": doc1_meta.created_at.isoformat() if doc1_meta and doc1_meta.created_at else None
            },
            "doc2": {
                "doc_id": doc_id2,
                "content": doc2_vec.content if doc2_vec else "",
                "source_type": doc2_meta.source_type if doc2_meta else None,
                "skill_level": doc2_meta.skill_level if doc2_meta else None,
                "cluster_id": doc2_meta.cluster_id if doc2_meta else None,
                "created_at": doc2_meta.created_at.isoformat() if doc2_meta and doc2_meta.created_at else None
            },
            "similarity": similarity
        }

    def merge_duplicates(
        self,
        keep_doc_id: int,
        delete_doc_ids: List[int],
        username: str
    ) -> Dict[str, Any]:
        """
        Merge duplicate documents by keeping one and deleting others.

        Args:
            keep_doc_id: Document ID to keep
            delete_doc_ids: List of document IDs to delete
            username: Username for authorization check

        Returns:
            Result dictionary with merge status
        """
        # Verify ownership of all documents
        all_doc_ids = [keep_doc_id] + delete_doc_ids

        docs = self.db.query(DBDocument).filter(
            DBDocument.doc_id.in_(all_doc_ids),
            DBDocument.owner_username == username
        ).all()

        if len(docs) != len(all_doc_ids):
            raise ValueError("One or more documents not found or not owned by user")

        # Delete the duplicate documents
        deleted_count = 0
        for doc_id in delete_doc_ids:
            # Delete from vector documents
            self.db.query(DBVectorDocument).filter(
                DBVectorDocument.doc_id == doc_id
            ).delete()

            # Delete concepts
            from .db_models import DBConcept
            self.db.query(DBConcept).filter(
                DBConcept.doc_id == doc_id
            ).delete()

            # Delete document
            self.db.query(DBDocument).filter(
                DBDocument.doc_id == doc_id
            ).delete()

            deleted_count += 1

        self.db.commit()

        logger.info(f"Merged duplicates: kept doc {keep_doc_id}, deleted {deleted_count} documents")

        return {
            "kept_doc_id": keep_doc_id,
            "deleted_count": deleted_count,
            "deleted_doc_ids": delete_doc_ids
        }
