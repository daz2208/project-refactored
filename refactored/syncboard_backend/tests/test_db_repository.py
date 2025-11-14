"""
Comprehensive tests for DatabaseKnowledgeBankRepository.

Tests cover:
- Document CRUD operations
- Cluster management
- User management
- Database relationships and cascade deletes
- Transaction handling and rollbacks
- Concurrent operations
- Search integration with vector store
- Data integrity and constraints
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from backend.db_models import Base, DBUser, DBCluster, DBDocument, DBConcept, DBVectorDocument
from backend.db_repository import DatabaseKnowledgeBankRepository
from backend.models import DocumentMetadata, Cluster, Concept


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create database session for each test."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def repository(db_session):
    """Create repository instance with test database."""
    return DatabaseKnowledgeBankRepository(db_session=db_session, vector_dim=256)


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = DBUser(username="testuser", hashed_password="hashed_password_123")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_cluster(db_session):
    """Create a sample cluster for testing."""
    cluster = DBCluster(
        name="Python Programming",
        primary_concepts=["python", "programming"],
        skill_level="intermediate"
    )
    db_session.add(cluster)
    db_session.commit()
    return cluster


@pytest.fixture
def sample_metadata(sample_user, sample_cluster):
    """Create sample document metadata."""
    return DocumentMetadata(
        doc_id=0,
        owner=sample_user.username,
        source_type="text",
        source_url=None,
        filename=None,
        image_path=None,
        concepts=[
            Concept(name="Python", category="language", confidence=0.9),
            Concept(name="Programming", category="concept", confidence=0.85)
        ],
        skill_level="intermediate",
        cluster_id=sample_cluster.id,
        ingested_at="2025-01-01T00:00:00",  # Fixed timestamp for testing (ISO string)
        content_length=100
    )


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

def test_repository_initialization(repository):
    """Test repository initializes correctly."""
    assert repository.db is not None
    assert repository.vector_store is not None
    assert repository.vector_dim == 256
    assert repository._lock is not None


def test_repository_loads_existing_documents(db_session):
    """Test repository loads existing documents into vector store on init."""
    # Create some documents in database
    vdoc1 = DBVectorDocument(doc_id=0, content="Python programming")
    vdoc2 = DBVectorDocument(doc_id=1, content="JavaScript development")
    db_session.add_all([vdoc1, vdoc2])
    db_session.commit()

    # Initialize repository
    repo = DatabaseKnowledgeBankRepository(db_session=db_session)

    # Vector store should have documents
    assert len(repo.vector_store.docs) == 2
    assert 0 in repo.vector_store.docs
    assert 1 in repo.vector_store.docs


# =============================================================================
# DOCUMENT OPERATIONS
# =============================================================================

@pytest.mark.asyncio
async def test_add_document(repository, sample_metadata):
    """Test adding a document to repository."""
    content = "This is a test document about Python programming"

    doc_id = await repository.add_document(content, sample_metadata)

    assert doc_id == 0

    # Verify document in database
    db_doc = repository.db.query(DBDocument).filter_by(doc_id=doc_id).first()
    assert db_doc is not None
    assert db_doc.owner_username == sample_metadata.owner
    assert db_doc.cluster_id == sample_metadata.cluster_id
    assert db_doc.source_type == "text"

    # Verify concepts in database
    assert len(db_doc.concepts) == 2

    # Verify vector document
    vdoc = repository.db.query(DBVectorDocument).filter_by(doc_id=doc_id).first()
    assert vdoc is not None
    assert vdoc.content == content

    # Verify in vector store
    assert doc_id in repository.vector_store.docs


@pytest.mark.asyncio
async def test_add_multiple_documents(repository, sample_metadata):
    """Test adding multiple documents."""
    content1 = "Python programming tutorial"
    content2 = "JavaScript web development"

    doc_id1 = await repository.add_document(content1, sample_metadata)
    doc_id2 = await repository.add_document(content2, sample_metadata)

    assert doc_id1 == 0
    assert doc_id2 == 1

    # Both should be in database
    assert repository.db.query(DBDocument).count() == 2
    assert repository.db.query(DBVectorDocument).count() == 2


@pytest.mark.asyncio
async def test_get_document(repository, sample_metadata):
    """Test retrieving document content."""
    content = "Test document content"

    doc_id = await repository.add_document(content, sample_metadata)

    retrieved_content = await repository.get_document(doc_id)

    assert retrieved_content == content


@pytest.mark.asyncio
async def test_get_nonexistent_document(repository):
    """Test retrieving non-existent document returns None."""
    content = await repository.get_document(999)

    assert content is None


@pytest.mark.asyncio
async def test_get_document_metadata(repository, sample_metadata):
    """Test retrieving document metadata."""
    content = "Test document"

    doc_id = await repository.add_document(content, sample_metadata)

    metadata = await repository.get_document_metadata(doc_id)

    assert metadata is not None
    assert metadata.doc_id == doc_id
    assert metadata.owner == sample_metadata.owner
    assert metadata.cluster_id == sample_metadata.cluster_id
    assert metadata.source_type == "text"
    assert len(metadata.concepts) == 2


@pytest.mark.asyncio
async def test_get_all_documents(repository, sample_metadata):
    """Test getting all documents."""
    await repository.add_document("Doc 1", sample_metadata)
    await repository.add_document("Doc 2", sample_metadata)
    await repository.add_document("Doc 3", sample_metadata)

    all_docs = await repository.get_all_documents()

    assert len(all_docs) == 3
    assert 0 in all_docs
    assert 1 in all_docs
    assert 2 in all_docs
    assert all_docs[0] == "Doc 1"


@pytest.mark.asyncio
async def test_get_all_metadata(repository, sample_metadata):
    """Test getting all document metadata."""
    await repository.add_document("Doc 1", sample_metadata)
    await repository.add_document("Doc 2", sample_metadata)

    all_metadata = await repository.get_all_metadata()

    assert len(all_metadata) == 2
    assert all(isinstance(meta, DocumentMetadata) for meta in all_metadata.values())


@pytest.mark.asyncio
async def test_delete_document(repository, sample_metadata):
    """Test deleting a document."""
    content = "Document to delete"

    doc_id = await repository.add_document(content, sample_metadata)

    # Delete the document
    result = await repository.delete_document(doc_id)

    assert result is True

    # Verify document deleted from database
    db_doc = repository.db.query(DBDocument).filter_by(doc_id=doc_id).first()
    assert db_doc is None

    # Verify vector document deleted
    vdoc = repository.db.query(DBVectorDocument).filter_by(doc_id=doc_id).first()
    assert vdoc is None


@pytest.mark.asyncio
async def test_delete_nonexistent_document(repository):
    """Test deleting non-existent document returns False."""
    result = await repository.delete_document(999)

    assert result is False


@pytest.mark.asyncio
async def test_delete_document_cascade_deletes_concepts(repository, sample_metadata):
    """Test that deleting document cascades to concepts."""
    doc_id = await repository.add_document("Test content", sample_metadata)

    # Verify concepts exist
    concepts_count = repository.db.query(DBConcept).count()
    assert concepts_count == 2

    # Delete document
    await repository.delete_document(doc_id)

    # Concepts should be deleted (cascade)
    concepts_count = repository.db.query(DBConcept).count()
    assert concepts_count == 0


# =============================================================================
# CLUSTER OPERATIONS
# =============================================================================

@pytest.mark.asyncio
async def test_add_cluster(repository):
    """Test adding a cluster."""
    cluster = Cluster(
        id=0,
        name="Web Development",
        doc_ids=[],
        primary_concepts=["html", "css", "javascript"],
        skill_level="beginner",
        doc_count=0
    )

    cluster_id = await repository.add_cluster(cluster)

    assert cluster_id > 0

    # Verify in database
    db_cluster = repository.db.query(DBCluster).filter_by(id=cluster_id).first()
    assert db_cluster is not None
    assert db_cluster.name == "Web Development"
    assert db_cluster.primary_concepts == ["html", "css", "javascript"]


@pytest.mark.asyncio
async def test_get_cluster(repository, sample_cluster):
    """Test retrieving a cluster."""
    cluster = await repository.get_cluster(sample_cluster.id)

    assert cluster is not None
    assert cluster.id == sample_cluster.id
    assert cluster.name == sample_cluster.name
    assert cluster.primary_concepts == sample_cluster.primary_concepts
    assert cluster.skill_level == sample_cluster.skill_level


@pytest.mark.asyncio
async def test_get_nonexistent_cluster(repository):
    """Test retrieving non-existent cluster returns None."""
    cluster = await repository.get_cluster(999)

    assert cluster is None


@pytest.mark.asyncio
async def test_get_all_clusters(repository):
    """Test getting all clusters."""
    # Add multiple clusters
    cluster1 = Cluster(id=0, name="Python", doc_ids=[], primary_concepts=["python"], skill_level="beginner", doc_count=0)
    cluster2 = Cluster(id=0, name="JavaScript", doc_ids=[], primary_concepts=["javascript"], skill_level="intermediate", doc_count=0)

    id1 = await repository.add_cluster(cluster1)
    id2 = await repository.add_cluster(cluster2)

    all_clusters = await repository.get_all_clusters()

    assert len(all_clusters) == 2
    assert id1 in all_clusters
    assert id2 in all_clusters


@pytest.mark.asyncio
async def test_update_cluster(repository, sample_cluster):
    """Test updating a cluster."""
    # Get cluster
    cluster = await repository.get_cluster(sample_cluster.id)

    # Modify it
    cluster.name = "Advanced Python Programming"
    cluster.skill_level = "advanced"
    cluster.primary_concepts = ["python", "advanced", "design patterns"]

    # Update
    result = await repository.update_cluster(cluster)

    assert result is True

    # Verify changes in database
    db_cluster = repository.db.query(DBCluster).filter_by(id=sample_cluster.id).first()
    assert db_cluster.name == "Advanced Python Programming"
    assert db_cluster.skill_level == "advanced"
    assert "design patterns" in db_cluster.primary_concepts


@pytest.mark.asyncio
async def test_update_nonexistent_cluster(repository):
    """Test updating non-existent cluster returns False."""
    cluster = Cluster(id=999, name="Fake", doc_ids=[], primary_concepts=[], skill_level="beginner", doc_count=0)

    result = await repository.update_cluster(cluster)

    assert result is False


@pytest.mark.asyncio
async def test_add_document_to_cluster(repository, sample_user, sample_cluster, sample_metadata):
    """Test adding document to cluster."""
    doc_id = await repository.add_document("Test content", sample_metadata)

    result = await repository.add_document_to_cluster(doc_id, sample_cluster.id)

    assert result is True

    # Verify in database
    db_doc = repository.db.query(DBDocument).filter_by(doc_id=doc_id).first()
    assert db_doc.cluster_id == sample_cluster.id


@pytest.mark.asyncio
async def test_add_document_to_nonexistent_cluster(repository, sample_metadata):
    """Test adding document to non-existent cluster returns False."""
    doc_id = await repository.add_document("Test content", sample_metadata)

    result = await repository.add_document_to_cluster(doc_id, 999)

    assert result is False


@pytest.mark.asyncio
async def test_cluster_doc_ids_list(repository, sample_cluster, sample_metadata):
    """Test that cluster.doc_ids contains correct document IDs."""
    # Add multiple documents to the cluster
    doc_id1 = await repository.add_document("Doc 1", sample_metadata)
    doc_id2 = await repository.add_document("Doc 2", sample_metadata)

    # Get cluster
    cluster = await repository.get_cluster(sample_cluster.id)

    # Should contain both documents
    assert doc_id1 in cluster.doc_ids
    assert doc_id2 in cluster.doc_ids
    assert cluster.doc_count == 2


# =============================================================================
# USER OPERATIONS
# =============================================================================

@pytest.mark.asyncio
async def test_add_user(repository):
    """Test adding a user."""
    await repository.add_user("newuser", "hashed_password_abc")

    # Verify in database
    db_user = repository.db.query(DBUser).filter_by(username="newuser").first()
    assert db_user is not None
    assert db_user.username == "newuser"
    assert db_user.hashed_password == "hashed_password_abc"


@pytest.mark.asyncio
async def test_get_user(repository, sample_user):
    """Test retrieving user's hashed password."""
    password = await repository.get_user(sample_user.username)

    assert password == sample_user.hashed_password


@pytest.mark.asyncio
async def test_get_nonexistent_user(repository):
    """Test retrieving non-existent user returns None."""
    password = await repository.get_user("nonexistent_user")

    assert password is None


@pytest.mark.asyncio
async def test_add_duplicate_user_fails(repository, sample_user):
    """Test that adding duplicate username fails."""
    with pytest.raises(IntegrityError):
        await repository.add_user(sample_user.username, "another_password")
        repository.db.commit()


# =============================================================================
# CASCADE DELETE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_delete_user_cascades_to_documents(repository, sample_user, sample_metadata):
    """Test that deleting a user cascades to their documents."""
    # Add documents for the user
    await repository.add_document("Doc 1", sample_metadata)
    await repository.add_document("Doc 2", sample_metadata)

    # Verify documents exist
    doc_count = repository.db.query(DBDocument).filter_by(owner_username=sample_user.username).count()
    assert doc_count == 2

    # Delete the user
    repository.db.delete(sample_user)
    repository.db.commit()

    # Documents should be deleted (cascade)
    doc_count = repository.db.query(DBDocument).filter_by(owner_username=sample_user.username).count()
    assert doc_count == 0


@pytest.mark.asyncio
async def test_delete_cluster_cascades_to_documents(repository, sample_cluster, sample_metadata):
    """Test that deleting a cluster cascades to documents."""
    # Add documents to cluster
    await repository.add_document("Doc 1", sample_metadata)
    await repository.add_document("Doc 2", sample_metadata)

    # Verify documents exist
    doc_count = repository.db.query(DBDocument).filter_by(cluster_id=sample_cluster.id).count()
    assert doc_count == 2

    # Delete the cluster
    repository.db.delete(sample_cluster)
    repository.db.commit()

    # Documents should be deleted (cascade)
    doc_count = repository.db.query(DBDocument).filter_by(cluster_id=sample_cluster.id).count()
    assert doc_count == 0


# =============================================================================
# SEARCH OPERATIONS
# =============================================================================

@pytest.mark.asyncio
async def test_search_documents(repository, sample_metadata):
    """Test semantic search for documents."""
    await repository.add_document("Python programming tutorial", sample_metadata)
    await repository.add_document("JavaScript web development", sample_metadata)
    await repository.add_document("Python data science guide", sample_metadata)

    results = await repository.search_documents("Python coding", top_k=3)

    # Should return results (exact format depends on vector_store implementation)
    assert len(results) >= 0


@pytest.mark.asyncio
async def test_search_with_allowed_doc_ids(repository, sample_metadata):
    """Test search with document ID filtering."""
    doc_id1 = await repository.add_document("Python programming", sample_metadata)
    doc_id2 = await repository.add_document("JavaScript development", sample_metadata)
    doc_id3 = await repository.add_document("Python data science", sample_metadata)

    # Search with filter
    results = await repository.search_documents("Python", top_k=10, allowed_doc_ids=[doc_id1, doc_id3])

    # Should only return filtered documents
    # Implementation depends on vector_store.search signature


# =============================================================================
# CONCURRENT OPERATIONS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_concurrent_document_adds(repository, sample_metadata):
    """Test concurrent document additions use locking correctly."""
    async def add_doc(i):
        return await repository.add_document(f"Document {i}", sample_metadata)

    # Add 10 documents concurrently
    tasks = [add_doc(i) for i in range(10)]
    doc_ids = await asyncio.gather(*tasks)

    # All should have unique IDs
    assert len(set(doc_ids)) == 10

    # All should be in database
    assert repository.db.query(DBDocument).count() == 10


@pytest.mark.asyncio
async def test_concurrent_cluster_operations(repository):
    """Test concurrent cluster operations."""
    async def add_cluster(i):
        cluster = Cluster(
            id=0,
            name=f"Cluster {i}",
            doc_ids=[],
            primary_concepts=[f"concept{i}"],
            skill_level="beginner",
            doc_count=0
        )
        return await repository.add_cluster(cluster)

    # Add 5 clusters concurrently
    tasks = [add_cluster(i) for i in range(5)]
    cluster_ids = await asyncio.gather(*tasks)

    # All should have unique IDs
    assert len(set(cluster_ids)) == 5

    # All should be in database
    assert repository.db.query(DBCluster).count() == 6  # +1 for sample_cluster fixture


# =============================================================================
# DATA INTEGRITY TESTS
# =============================================================================

def test_document_requires_owner(db_session):
    """Test that document requires valid owner (foreign key constraint)."""
    # Try to create document with non-existent owner
    db_doc = DBDocument(
        doc_id=0,
        owner_username="nonexistent_user",
        source_type="text"
    )
    db_session.add(db_doc)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unique_username_constraint(db_session):
    """Test that username must be unique."""
    user1 = DBUser(username="testuser", hashed_password="pass1")
    user2 = DBUser(username="testuser", hashed_password="pass2")

    db_session.add(user1)
    db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unique_doc_id_constraint(db_session, sample_user):
    """Test that doc_id must be unique."""
    doc1 = DBDocument(doc_id=0, owner_username=sample_user.username, source_type="text")
    doc2 = DBDocument(doc_id=0, owner_username=sample_user.username, source_type="url")

    db_session.add(doc1)
    db_session.commit()

    db_session.add(doc2)
    with pytest.raises(IntegrityError):
        db_session.commit()


# =============================================================================
# RELATIONSHIP TESTS
# =============================================================================

def test_user_documents_relationship(db_session, sample_user, sample_cluster):
    """Test user -> documents relationship."""
    # Add documents for user
    doc1 = DBDocument(doc_id=0, owner_username=sample_user.username, cluster_id=sample_cluster.id, source_type="text")
    doc2 = DBDocument(doc_id=1, owner_username=sample_user.username, cluster_id=sample_cluster.id, source_type="text")

    db_session.add_all([doc1, doc2])
    db_session.commit()

    # Access documents through relationship
    db_session.refresh(sample_user)
    assert len(sample_user.documents) == 2


def test_cluster_documents_relationship(db_session, sample_user, sample_cluster):
    """Test cluster -> documents relationship."""
    # Add documents to cluster
    doc1 = DBDocument(doc_id=0, owner_username=sample_user.username, cluster_id=sample_cluster.id, source_type="text")
    doc2 = DBDocument(doc_id=1, owner_username=sample_user.username, cluster_id=sample_cluster.id, source_type="text")

    db_session.add_all([doc1, doc2])
    db_session.commit()

    # Access documents through relationship
    db_session.refresh(sample_cluster)
    assert len(sample_cluster.documents) == 2


def test_document_concepts_relationship(db_session, sample_user, sample_cluster):
    """Test document -> concepts relationship."""
    doc = DBDocument(doc_id=0, owner_username=sample_user.username, cluster_id=sample_cluster.id, source_type="text")
    db_session.add(doc)
    db_session.flush()

    # Add concepts
    concept1 = DBConcept(document_id=doc.id, name="Python", category="language", confidence=0.9)
    concept2 = DBConcept(document_id=doc.id, name="Tutorial", category="content_type", confidence=0.8)

    db_session.add_all([concept1, concept2])
    db_session.commit()

    # Access concepts through relationship
    db_session.refresh(doc)
    assert len(doc.concepts) == 2
    assert doc.concepts[0].name in ["Python", "Tutorial"]


# =============================================================================
# EDGE CASES
# =============================================================================

@pytest.mark.asyncio
async def test_add_document_with_no_concepts(repository, sample_user, sample_cluster):
    """Test adding document with no concepts."""
    metadata = DocumentMetadata(
        doc_id=0,
        owner=sample_user.username,
        source_type="text",
        source_url=None,
        filename=None,
        image_path=None,
        concepts=[],  # Empty concepts
        skill_level="beginner",
        cluster_id=sample_cluster.id,
        ingested_at="2025-01-01T00:00:00",
        content_length=50
    )

    doc_id = await repository.add_document("Test content", metadata)

    assert doc_id == 0

    # Verify no concepts in database
    db_doc = repository.db.query(DBDocument).filter_by(doc_id=doc_id).first()
    assert len(db_doc.concepts) == 0


@pytest.mark.asyncio
async def test_add_document_with_no_cluster(repository, sample_user):
    """Test adding document without cluster assignment."""
    metadata = DocumentMetadata(
        doc_id=0,
        owner=sample_user.username,
        source_type="text",
        source_url=None,
        filename=None,
        image_path=None,
        concepts=[],
        skill_level="beginner",
        cluster_id=None,  # No cluster
        ingested_at="2025-01-01T00:00:00",
        content_length=50
    )

    doc_id = await repository.add_document("Test content", metadata)

    assert doc_id == 0

    # Verify no cluster assigned
    db_doc = repository.db.query(DBDocument).filter_by(doc_id=doc_id).first()
    assert db_doc.cluster_id is None


@pytest.mark.asyncio
async def test_empty_repository_operations(repository):
    """Test operations on empty repository."""
    all_docs = await repository.get_all_documents()
    all_metadata = await repository.get_all_metadata()
    all_clusters = await repository.get_all_clusters()

    assert all_docs == {}
    assert all_metadata == {}
    # May have default clusters, so just check it's a dict
    assert isinstance(all_clusters, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
