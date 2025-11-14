"""
SQLAlchemy database models (Phase 6).

Maps application domain models to PostgreSQL tables.
Separate from Pydantic models (models.py) which handle API validation.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class DBUser(Base):
    """User account table."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("DBDocument", back_populates="owner_user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DBUser(id={self.id}, username='{self.username}')>"


class DBCluster(Base):
    """Cluster/topic grouping table."""
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    primary_concepts = Column(JSON, nullable=False, default=list)  # List of concept names
    skill_level = Column(String(50), nullable=True)  # beginner, intermediate, advanced
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("DBDocument", back_populates="cluster", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_cluster_skill_level', 'skill_level'),
    )

    def __repr__(self):
        return f"<DBCluster(id={self.id}, name='{self.name}', docs={len(self.documents)})>"


class DBDocument(Base):
    """Document metadata table."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, unique=True, nullable=False, index=True)  # Vector store ID
    owner_username = Column(String(50), ForeignKey("users.username"), nullable=False, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=True, index=True)

    # Source information
    source_type = Column(String(50), nullable=False, index=True)  # text, url, file, image
    source_url = Column(String(2048), nullable=True)
    filename = Column(String(512), nullable=True)
    image_path = Column(String(1024), nullable=True)

    # Content metadata
    content_length = Column(Integer, nullable=True)
    skill_level = Column(String(50), nullable=True, index=True)

    # Timestamps
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner_user = relationship("DBUser", back_populates="documents")
    cluster = relationship("DBCluster", back_populates="documents")
    concepts = relationship("DBConcept", back_populates="document", cascade="all, delete-orphan")

    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_doc_owner_cluster', 'owner_username', 'cluster_id'),
        Index('idx_doc_source_skill', 'source_type', 'skill_level'),
        Index('idx_doc_ingested', 'ingested_at'),
    )

    def __repr__(self):
        return f"<DBDocument(doc_id={self.doc_id}, owner='{self.owner_username}', cluster={self.cluster_id})>"


class DBConcept(Base):
    """Extracted concepts/tags from documents."""
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)  # language, framework, concept, etc.
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("DBDocument", back_populates="concepts")

    # Indexes for search
    __table_args__ = (
        Index('idx_concept_name_category', 'name', 'category'),
        Index('idx_concept_confidence', 'confidence'),
    )

    def __repr__(self):
        return f"<DBConcept(name='{self.name}', category='{self.category}', conf={self.confidence:.2f})>"


class DBVectorDocument(Base):
    """
    Stores actual document content and vector data.
    Separate table for performance (large text fields).
    """
    __tablename__ = "vector_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, unique=True, nullable=False, index=True)  # Links to DBDocument.doc_id
    content = Column(Text, nullable=False)  # Full document text

    # TF-IDF vector representation (stored as JSON for now)
    # In production, consider pgvector extension for native vector search
    tfidf_vector = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<DBVectorDocument(doc_id={self.doc_id}, content_len={len(self.content) if self.content else 0})>"


# =============================================================================
# Phase 7.3-7.5: Advanced Features
# =============================================================================

class DBTag(Base):
    """User-defined tags for documents (Phase 7.3)."""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    owner_username = Column(String(50), ForeignKey("users.username"), nullable=False, index=True)
    color = Column(String(7), nullable=True)  # Hex color code (e.g., "#00d4ff")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint: one tag name per user
    __table_args__ = (
        Index('idx_tag_owner_name', 'owner_username', 'name', unique=True),
    )

    def __repr__(self):
        return f"<DBTag(id={self.id}, name='{self.name}', owner='{self.owner_username}')>"


class DBDocumentTag(Base):
    """Many-to-many relationship between documents and tags (Phase 7.3)."""
    __tablename__ = "document_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint: each document-tag pair only once
    __table_args__ = (
        Index('idx_doctag_unique', 'document_id', 'tag_id', unique=True),
    )

    def __repr__(self):
        return f"<DBDocumentTag(doc={self.document_id}, tag={self.tag_id})>"


class DBSavedSearch(Base):
    """Saved search queries for quick access (Phase 7.4)."""
    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_username = Column(String(50), ForeignKey("users.username"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    query = Column(String(1000), nullable=False)

    # Search filters (stored as JSON)
    filters = Column(JSON, nullable=True)  # {cluster_id, source_type, skill_level, date_from, date_to}

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index('idx_saved_search_owner', 'owner_username'),
    )

    def __repr__(self):
        return f"<DBSavedSearch(id={self.id}, name='{self.name}', owner='{self.owner_username}')>"


class DBDocumentRelationship(Base):
    """Links between related documents (Phase 7.5)."""
    __tablename__ = "document_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_doc_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    target_doc_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

    relationship_type = Column(String(50), nullable=False, default="related")
    # Types: "related", "prerequisite", "followup", "alternative", "supersedes"

    strength = Column(Float, nullable=True)  # 0.0-1.0, for AI-discovered relationships
    created_by_username = Column(String(50), nullable=True)  # Null if AI-generated
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Prevent duplicate relationships
    __table_args__ = (
        Index('idx_doc_rel_unique', 'source_doc_id', 'target_doc_id', 'relationship_type', unique=True),
    )

    def __repr__(self):
        return f"<DBDocumentRelationship(source={self.source_doc_id}, target={self.target_doc_id}, type='{self.relationship_type}')>"
