"""
Comprehensive tests for Phase 7.2: Duplicate Detection

Tests duplicate detection functionality including:
- Finding duplicate documents based on similarity
- Comparing two documents
- Merging duplicate documents
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.duplicate_detection import DuplicateDetector
from backend.db_models import DBDocument, DBVectorDocument
from backend.vector_store import VectorStore


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store with search capabilities."""
    store = Mock(spec=VectorStore)
    store.search_by_doc_id = Mock(return_value=[])
    store.remove_document = Mock()
    return store


@pytest.fixture
def duplicate_detector(mock_db_session, mock_vector_store):
    """Create a duplicate detector instance."""
    return DuplicateDetector(mock_db_session, mock_vector_store)


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    docs = []

    # Document 1
    doc1 = DBDocument(
        id=1,
        doc_id=101,
        owner_username="testuser",
        source_type="text",
        content_length=100,
        skill_level="beginner",
        cluster_id=1
    )

    # Document 2 (similar to doc1)
    doc2 = DBDocument(
        id=2,
        doc_id=102,
        owner_username="testuser",
        source_type="text",
        content_length=105,
        skill_level="beginner",
        cluster_id=1
    )

    # Document 3 (different)
    doc3 = DBDocument(
        id=3,
        doc_id=103,
        owner_username="testuser",
        source_type="url",
        content_length=200,
        skill_level="advanced",
        cluster_id=2
    )

    return [doc1, doc2, doc3]


@pytest.fixture
def sample_vector_documents():
    """Create sample vector documents with content."""
    return {
        101: DBVectorDocument(
            doc_id=101,
            content="Python programming tutorial for beginners"
        ),
        102: DBVectorDocument(
            doc_id=102,
            content="Python programming tutorial for beginners with examples"
        ),
        103: DBVectorDocument(
            doc_id=103,
            content="Advanced JavaScript frameworks and design patterns"
        )
    }


class TestFindDuplicates:
    """Test suite for finding duplicate documents."""

    def test_find_duplicates_basic(self, duplicate_detector, mock_db_session, mock_vector_store, sample_documents, sample_vector_documents):
        """Test basic duplicate detection functionality."""
        # Setup
        mock_db_session.query.return_value.filter.return_value.all.return_value = sample_documents

        # Mock vector store to return high similarity for doc 101 and 102
        def mock_search(doc_id, top_k):
            if doc_id == 101:
                return [(102, 0.92), (103, 0.15)]  # High similarity with 102
            elif doc_id == 102:
                return [(101, 0.92), (103, 0.15)]
            else:
                return [(101, 0.15), (102, 0.15)]

        mock_vector_store.search_by_doc_id.side_effect = mock_search

        # Mock vector document queries
        def mock_vector_query(doc_id):
            mock_result = Mock()
            mock_result.first.return_value = sample_vector_documents.get(doc_id)
            return mock_result

        mock_db_session.query.return_value.filter.return_value = Mock(first=lambda: sample_vector_documents.get(101))

        # Execute
        result = duplicate_detector.find_duplicates(username="testuser", similarity_threshold=0.85)

        # Verify
        assert "duplicate_groups" in result
        assert "total_duplicates_found" in result
        assert result["total_duplicates_found"] >= 0

    def test_find_duplicates_no_results(self, duplicate_detector, mock_db_session, mock_vector_store):
        """Test finding duplicates when none exist."""
        # Setup - no documents
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        # Execute
        result = duplicate_detector.find_duplicates(username="testuser", similarity_threshold=0.85)

        # Verify
        assert result["duplicate_groups"] == []
        assert result["total_duplicates_found"] == 0

    def test_find_duplicates_high_threshold(self, duplicate_detector, mock_db_session, mock_vector_store, sample_documents):
        """Test with very high similarity threshold (99%)."""
        # Setup
        mock_db_session.query.return_value.filter.return_value.all.return_value = sample_documents
        mock_vector_store.search_by_doc_id.return_value = [(102, 0.95), (103, 0.20)]

        # Execute
        result = duplicate_detector.find_duplicates(username="testuser", similarity_threshold=0.99)

        # Verify - should find fewer duplicates with higher threshold
        assert "duplicate_groups" in result

    def test_find_duplicates_low_threshold(self, duplicate_detector, mock_db_session, mock_vector_store, sample_documents):
        """Test with low similarity threshold (50%)."""
        # Setup
        mock_db_session.query.return_value.filter.return_value.all.return_value = sample_documents
        mock_vector_store.search_by_doc_id.return_value = [(102, 0.55), (103, 0.52)]

        # Execute
        result = duplicate_detector.find_duplicates(username="testuser", similarity_threshold=0.50)

        # Verify - should find more duplicates with lower threshold
        assert "duplicate_groups" in result


class TestCompareTwoDocuments:
    """Test suite for comparing two specific documents."""

    def test_compare_two_documents_success(self, duplicate_detector, mock_db_session, mock_vector_store, sample_vector_documents):
        """Test successfully comparing two documents."""
        # Setup
        doc1 = Mock()
        doc1.doc_id = 101
        doc1.source_type = "text"
        doc1.skill_level = "beginner"
        doc1.cluster_id = 1
        doc1.owner_username = "testuser"

        doc2 = Mock()
        doc2.doc_id = 102
        doc2.source_type = "text"
        doc2.skill_level = "beginner"
        doc2.cluster_id = 1
        doc2.owner_username = "testuser"

        # Mock database queries
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [doc1, doc2]

        # Mock vector store similarity
        mock_vector_store.search_by_doc_id.return_value = [(102, 0.89)]

        # Mock vector documents
        def mock_filter(condition):
            mock_result = Mock()
            # Simulate returning vector documents based on doc_id
            mock_result.first.side_effect = [
                sample_vector_documents[101],
                sample_vector_documents[102]
            ]
            return mock_result

        # Execute
        result = duplicate_detector.compare_two_documents(101, 102, "testuser")

        # Verify
        assert "similarity_score" in result
        assert "doc1" in result
        assert "doc2" in result

    def test_compare_documents_not_found(self, duplicate_detector, mock_db_session):
        """Test comparing when one document doesn't exist."""
        # Setup - first document not found
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Execute & Verify
        with pytest.raises(ValueError, match="Document not found"):
            duplicate_detector.compare_two_documents(999, 102, "testuser")

    def test_compare_same_document(self, duplicate_detector, mock_db_session):
        """Test comparing a document with itself."""
        # Setup
        doc = Mock()
        doc.doc_id = 101
        doc.owner_username = "testuser"

        mock_db_session.query.return_value.filter.return_value.first.return_value = doc

        # Execute
        result = duplicate_detector.compare_two_documents(101, 101, "testuser")

        # Verify - same document should have 100% similarity
        assert result["similarity_score"] == 1.0

    def test_compare_documents_different_owners(self, duplicate_detector, mock_db_session):
        """Test comparing documents from different owners."""
        # Setup
        doc1 = Mock()
        doc1.doc_id = 101
        doc1.owner_username = "user1"

        doc2 = Mock()
        doc2.doc_id = 102
        doc2.owner_username = "user2"

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [doc1, None]

        # Execute & Verify
        with pytest.raises(ValueError, match="Document not found"):
            duplicate_detector.compare_two_documents(101, 102, "user1")


class TestMergeDuplicates:
    """Test suite for merging duplicate documents."""

    def test_merge_duplicates_success(self, duplicate_detector, mock_db_session, mock_vector_store):
        """Test successfully merging duplicates."""
        # Setup
        keep_doc = Mock()
        keep_doc.doc_id = 101
        keep_doc.owner_username = "testuser"

        delete_doc1 = Mock()
        delete_doc1.doc_id = 102
        delete_doc1.owner_username = "testuser"

        delete_doc2 = Mock()
        delete_doc2.doc_id = 103
        delete_doc2.owner_username = "testuser"

        # Mock document queries
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            keep_doc, delete_doc1, delete_doc2
        ]

        # Execute
        result = duplicate_detector.merge_duplicates(
            keep_doc_id=101,
            delete_doc_ids=[102, 103],
            username="testuser"
        )

        # Verify
        assert result["status"] == "merged"
        assert result["kept_doc_id"] == 101
        assert len(result["deleted_doc_ids"]) == 2
        assert 102 in result["deleted_doc_ids"]
        assert 103 in result["deleted_doc_ids"]

        # Verify vector store cleanup
        assert mock_vector_store.remove_document.call_count == 2

    def test_merge_duplicates_document_not_found(self, duplicate_detector, mock_db_session):
        """Test merging when document doesn't exist."""
        # Setup - keep document not found
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Execute & Verify
        with pytest.raises(ValueError, match="Document .* not found"):
            duplicate_detector.merge_duplicates(999, [102], "testuser")

    def test_merge_duplicates_empty_delete_list(self, duplicate_detector, mock_db_session):
        """Test merging with empty delete list."""
        # Setup
        keep_doc = Mock()
        keep_doc.doc_id = 101
        keep_doc.owner_username = "testuser"

        mock_db_session.query.return_value.filter.return_value.first.return_value = keep_doc

        # Execute
        result = duplicate_detector.merge_duplicates(101, [], "testuser")

        # Verify
        assert result["status"] == "merged"
        assert len(result["deleted_doc_ids"]) == 0

    def test_merge_duplicates_unauthorized(self, duplicate_detector, mock_db_session):
        """Test merging documents not owned by user."""
        # Setup
        keep_doc = Mock()
        keep_doc.doc_id = 101
        keep_doc.owner_username = "user1"

        delete_doc = Mock()
        delete_doc.doc_id = 102
        delete_doc.owner_username = "user2"

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            keep_doc, None  # Second doc not found for wrong user
        ]

        # Execute & Verify
        with pytest.raises(ValueError, match="Document .* not found"):
            duplicate_detector.merge_duplicates(101, [102], "user1")

    def test_merge_duplicates_database_commit(self, duplicate_detector, mock_db_session, mock_vector_store):
        """Test that database changes are committed."""
        # Setup
        keep_doc = Mock()
        keep_doc.doc_id = 101
        keep_doc.owner_username = "testuser"

        delete_doc = Mock()
        delete_doc.doc_id = 102
        delete_doc.owner_username = "testuser"

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            keep_doc, delete_doc
        ]

        # Execute
        duplicate_detector.merge_duplicates(101, [102], "testuser")

        # Verify database operations
        mock_db_session.delete.assert_called()
        mock_db_session.commit.assert_called()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_find_duplicates_single_document(self, duplicate_detector, mock_db_session, sample_documents):
        """Test with only one document in database."""
        # Setup
        mock_db_session.query.return_value.filter.return_value.all.return_value = [sample_documents[0]]

        # Execute
        result = duplicate_detector.find_duplicates("testuser", similarity_threshold=0.85)

        # Verify
        assert result["duplicate_groups"] == []
        assert result["total_duplicates_found"] == 0

    def test_vector_store_unavailable(self, mock_db_session):
        """Test behavior when vector store is unavailable."""
        # Setup - vector store is None
        detector = DuplicateDetector(mock_db_session, None)

        # Execute & Verify
        with pytest.raises(Exception):
            detector.find_duplicates("testuser")

    def test_invalid_similarity_threshold(self, duplicate_detector, mock_db_session):
        """Test with invalid similarity threshold values."""
        # Setup
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        # Test threshold > 1.0
        result = duplicate_detector.find_duplicates("testuser", similarity_threshold=1.5)
        assert "duplicate_groups" in result

        # Test threshold < 0.0
        result = duplicate_detector.find_duplicates("testuser", similarity_threshold=-0.5)
        assert "duplicate_groups" in result

    def test_large_batch_merge(self, duplicate_detector, mock_db_session, mock_vector_store):
        """Test merging large number of duplicates."""
        # Setup
        keep_doc = Mock()
        keep_doc.doc_id = 1
        keep_doc.owner_username = "testuser"

        # Create 50 documents to delete
        delete_ids = list(range(2, 52))
        delete_docs = [Mock(doc_id=i, owner_username="testuser") for i in delete_ids]

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [keep_doc] + delete_docs

        # Execute
        result = duplicate_detector.merge_duplicates(1, delete_ids, "testuser")

        # Verify
        assert result["status"] == "merged"
        assert len(result["deleted_doc_ids"]) == 50
        assert mock_vector_store.remove_document.call_count == 50


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_find_and_merge_workflow(self, duplicate_detector, mock_db_session, mock_vector_store, sample_documents, sample_vector_documents):
        """Test complete workflow: find duplicates then merge them."""
        # Step 1: Find duplicates
        mock_db_session.query.return_value.filter.return_value.all.return_value = sample_documents
        mock_vector_store.search_by_doc_id.return_value = [(102, 0.92)]

        find_result = duplicate_detector.find_duplicates("testuser", 0.85)

        # Verify duplicates found
        assert "duplicate_groups" in find_result

        # Step 2: Merge duplicates
        keep_doc = Mock()
        keep_doc.doc_id = 101
        keep_doc.owner_username = "testuser"

        delete_doc = Mock()
        delete_doc.doc_id = 102
        delete_doc.owner_username = "testuser"

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [keep_doc, delete_doc]

        merge_result = duplicate_detector.merge_duplicates(101, [102], "testuser")

        # Verify merge successful
        assert merge_result["status"] == "merged"
        assert merge_result["kept_doc_id"] == 101

    def test_compare_before_merge_workflow(self, duplicate_detector, mock_db_session, mock_vector_store, sample_vector_documents):
        """Test workflow: compare documents before merging."""
        # Step 1: Compare two documents
        doc1 = Mock(doc_id=101, source_type="text", skill_level="beginner", cluster_id=1, owner_username="testuser")
        doc2 = Mock(doc_id=102, source_type="text", skill_level="beginner", cluster_id=1, owner_username="testuser")

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [doc1, doc2]
        mock_vector_store.search_by_doc_id.return_value = [(102, 0.92)]

        compare_result = duplicate_detector.compare_two_documents(101, 102, "testuser")

        # Verify high similarity
        assert compare_result["similarity_score"] >= 0.85

        # Step 2: Merge if similarity is high
        if compare_result["similarity_score"] >= 0.85:
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [doc1, doc2]
            merge_result = duplicate_detector.merge_duplicates(101, [102], "testuser")
            assert merge_result["status"] == "merged"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
