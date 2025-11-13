"""
Database Storage Adapter (Phase 6.5).

Provides file-storage-compatible interface using database backend.
Drop-in replacement for storage.py with database persistence.
"""

import logging
from typing import Dict, Tuple
from sqlalchemy.orm import Session

from .models import DocumentMetadata, Cluster, Concept
from .db_models import DBUser, DBCluster, DBDocument, DBConcept, DBVectorDocument
from .vector_store import VectorStore
from .database import get_db_context

logger = logging.getLogger(__name__)


def load_storage_from_db(
    vector_store: VectorStore
) -> Tuple[Dict[int, str], Dict[int, DocumentMetadata], Dict[int, Cluster], Dict[str, str]]:
    """
    Load documents, metadata, clusters, and users from database.

    Args:
        vector_store: VectorStore instance where document embeddings will be added

    Returns:
        Tuple of (documents, metadata, clusters, users) where:
        - documents: Dict[doc_id, full_text]
        - metadata: Dict[doc_id, DocumentMetadata]
        - clusters: Dict[cluster_id, Cluster]
        - users: Dict[username, hashed_password]
    """
    documents: Dict[int, str] = {}
    metadata: Dict[int, DocumentMetadata] = {}
    clusters: Dict[int, Cluster] = {}
    users: Dict[str, str] = {}

    try:
        with get_db_context() as db:
            # Load vector documents and rebuild vector store
            vector_docs = db.query(DBVectorDocument).all()
            for vdoc in vector_docs:
                # Add to vector store (this assigns the doc_id)
                actual_doc_id = vector_store.add_document(vdoc.content)
                # Map database doc_id to vector store doc_id
                documents[vdoc.doc_id] = vdoc.content

            # Load document metadata
            db_docs = db.query(DBDocument).all()
            for db_doc in db_docs:
                # Load concepts
                concepts = [
                    Concept(
                        name=c.name,
                        category=c.category,
                        confidence=c.confidence
                    )
                    for c in db_doc.concepts
                ]

                metadata[db_doc.doc_id] = DocumentMetadata(
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

            # Load clusters
            db_clusters = db.query(DBCluster).all()
            for db_cluster in db_clusters:
                # Get document IDs in this cluster
                doc_ids = [doc.doc_id for doc in db_cluster.documents]

                clusters[db_cluster.id] = Cluster(
                    id=db_cluster.id,
                    name=db_cluster.name,
                    doc_ids=doc_ids,
                    primary_concepts=db_cluster.primary_concepts,
                    skill_level=db_cluster.skill_level
                )

            # Load users
            db_users = db.query(DBUser).all()
            for db_user in db_users:
                users[db_user.username] = db_user.hashed_password

        logger.info(f"Loaded from database: {len(documents)} documents, {len(clusters)} clusters, {len(users)} users")

    except Exception as e:
        logger.warning(f"Database load failed: {e}. Starting with empty state.")

    return documents, metadata, clusters, users


def save_storage_to_db(
    documents: Dict[int, str],
    metadata: Dict[int, DocumentMetadata],
    clusters: Dict[int, Cluster],
    users: Dict[str, str]
) -> None:
    """
    Persist documents, metadata, clusters, and users to database.

    This performs a full sync - adds new items, updates existing ones.
    Does NOT delete items that are missing (for safety).

    Args:
        documents: Mapping of doc_id to full text
        metadata: Mapping of doc_id to DocumentMetadata
        clusters: Mapping of cluster_id to Cluster
        users: Mapping of username to hashed password
    """
    try:
        with get_db_context() as db:
            # Sync users
            for username, hashed_password in users.items():
                db_user = db.query(DBUser).filter_by(username=username).first()
                if not db_user:
                    db_user = DBUser(username=username, hashed_password=hashed_password)
                    db.add(db_user)
                else:
                    db_user.hashed_password = hashed_password

            # Sync clusters
            for cluster_id, cluster in clusters.items():
                db_cluster = db.query(DBCluster).filter_by(id=cluster_id).first()
                if not db_cluster:
                    db_cluster = DBCluster(
                        id=cluster_id,
                        name=cluster.name,
                        primary_concepts=cluster.primary_concepts,
                        skill_level=cluster.skill_level
                    )
                    db.add(db_cluster)
                else:
                    db_cluster.name = cluster.name
                    db_cluster.primary_concepts = cluster.primary_concepts
                    db_cluster.skill_level = cluster.skill_level

            db.commit()  # Commit users and clusters first

            # Sync documents and vector documents
            for doc_id, content in documents.items():
                # Vector document
                db_vdoc = db.query(DBVectorDocument).filter_by(doc_id=doc_id).first()
                if not db_vdoc:
                    db_vdoc = DBVectorDocument(doc_id=doc_id, content=content)
                    db.add(db_vdoc)
                else:
                    db_vdoc.content = content

                # Document metadata
                if doc_id in metadata:
                    meta = metadata[doc_id]
                    db_doc = db.query(DBDocument).filter_by(doc_id=doc_id).first()

                    if not db_doc:
                        db_doc = DBDocument(
                            doc_id=doc_id,
                            owner_username=meta.owner,
                            cluster_id=meta.cluster_id,
                            source_type=meta.source_type,
                            source_url=meta.source_url,
                            filename=meta.filename,
                            image_path=meta.image_path,
                            content_length=meta.content_length,
                            skill_level=meta.skill_level
                        )
                        db.add(db_doc)
                        db.flush()  # Get the database ID

                        # Add concepts
                        for concept in meta.concepts:
                            db_concept = DBConcept(
                                document_id=db_doc.id,
                                name=concept.name,
                                category=concept.category,
                                confidence=concept.confidence
                            )
                            db.add(db_concept)
                    else:
                        # Update existing document
                        db_doc.owner_username = meta.owner
                        db_doc.cluster_id = meta.cluster_id
                        db_doc.source_type = meta.source_type
                        db_doc.source_url = meta.source_url
                        db_doc.filename = meta.filename
                        db_doc.image_path = meta.image_path
                        db_doc.content_length = meta.content_length
                        db_doc.skill_level = meta.skill_level

                        # Update concepts (simple approach: delete and recreate)
                        db.query(DBConcept).filter_by(document_id=db_doc.id).delete()
                        for concept in meta.concepts:
                            db_concept = DBConcept(
                                document_id=db_doc.id,
                                name=concept.name,
                                category=concept.category,
                                confidence=concept.confidence
                            )
                            db.add(db_concept)

            db.commit()
            logger.debug(f"Saved to database: {len(documents)} documents, {len(clusters)} clusters")

    except Exception as e:
        logger.error(f"Failed to save to database: {e}")
        raise
