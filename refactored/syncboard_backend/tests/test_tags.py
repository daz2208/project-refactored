"""
Comprehensive tests for Phase 7.3: Tags System

Tests tag management functionality including:
- Creating and managing tags
- Adding/removing tags from documents
- Querying tags and document-tag relationships
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from backend.advanced_features_service import TagsService
from backend.db_models import DBTag, DBDocumentTag, DBDocument


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def tags_service(mock_db_session):
    """Create a tags service instance."""
    return TagsService(mock_db_session)


@pytest.fixture
def sample_tags():
    """Create sample tags for testing."""
    return [
        DBTag(id=1, name="python", color="#3776ab", owner_username="testuser", created_at=datetime.utcnow()),
        DBTag(id=2, name="tutorial", color="#00d4ff", owner_username="testuser", created_at=datetime.utcnow()),
        DBTag(id=3, name="advanced", color="#ef4444", owner_username="testuser", created_at=datetime.utcnow()),
    ]


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        DBDocument(id=1, doc_id=101, owner_username="testuser", source_type="text", cluster_id=1),
        DBDocument(id=2, doc_id=102, owner_username="testuser", source_type="url", cluster_id=1),
        DBDocument(id=3, doc_id=103, owner_username="testuser", source_type="file", cluster_id=2),
    ]


class TestCreateTag:
    """Test suite for creating tags."""

    def test_create_tag_success(self, tags_service, mock_db_session):
        """Test successfully creating a new tag."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None  # Tag doesn't exist yet
        mock_db_session.query.return_value = mock_query

        # Execute
        result = tags_service.create_tag(name="python", username="testuser", color="#3776ab")

        # Verify
        assert "id" in result
        assert result["name"] == "python"
        assert result["color"] == "#3776ab"
        assert "created_at" in result
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_create_tag_duplicate(self, tags_service, mock_db_session, sample_tags):
        """Test creating a tag that already exists (should return existing)."""
        # Setup
        existing_tag = sample_tags[0]
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = existing_tag
        mock_db_session.query.return_value = mock_query

        # Execute
        result = tags_service.create_tag(name="python", username="testuser", color="#3776ab")

        # Verify - should return existing tag without creating new one
        assert result["id"] == existing_tag.id
        assert result["name"] == existing_tag.name
        mock_db_session.add.assert_not_called()  # Should not add new tag

    def test_create_tag_no_color(self, tags_service, mock_db_session):
        """Test creating a tag without specifying a color."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute
        result = tags_service.create_tag(name="javascript", username="testuser", color=None)

        # Verify
        assert result["name"] == "javascript"
        assert result["color"] is None

    def test_create_tag_different_users_same_name(self, tags_service, mock_db_session):
        """Test that different users can have tags with same name."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None  # No existing tag for this user
        mock_db_session.query.return_value = mock_query

        # Execute - User 1 creates "python" tag
        result1 = tags_service.create_tag(name="python", username="user1", color="#3776ab")

        # Execute - User 2 creates "python" tag
        mock_query.filter.return_value.first.return_value = None  # No conflict
        result2 = tags_service.create_tag(name="python", username="user2", color="#00d4ff")

        # Verify - both should succeed
        assert result1["name"] == "python"
        assert result2["name"] == "python"
        assert mock_db_session.add.call_count == 2


class TestGetUserTags:
    """Test suite for retrieving user tags."""

    def test_get_user_tags_success(self, tags_service, mock_db_session, sample_tags):
        """Test retrieving all tags for a user."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = sample_tags
        mock_db_session.query.return_value = mock_query

        # Mock document counts for each tag
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [5, 3, 2]

        # Execute
        result = tags_service.get_user_tags("testuser")

        # Verify
        assert len(result) == 3
        assert result[0]["name"] == "python"
        assert result[0]["document_count"] == 5
        assert result[1]["document_count"] == 3
        assert result[2]["document_count"] == 2

    def test_get_user_tags_empty(self, tags_service, mock_db_session):
        """Test retrieving tags when user has none."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db_session.query.return_value = mock_query

        # Execute
        result = tags_service.get_user_tags("testuser")

        # Verify
        assert result == []

    def test_get_user_tags_with_zero_documents(self, tags_service, mock_db_session, sample_tags):
        """Test tags that have no documents associated."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = sample_tags
        mock_db_session.query.return_value = mock_query

        # All tags have 0 documents
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0

        # Execute
        result = tags_service.get_user_tags("testuser")

        # Verify
        assert len(result) == 3
        assert all(tag["document_count"] == 0 for tag in result)


class TestAddTagToDocument:
    """Test suite for adding tags to documents."""

    def test_add_tag_to_document_success(self, tags_service, mock_db_session, sample_documents, sample_tags):
        """Test successfully adding a tag to a document."""
        # Setup
        doc = sample_documents[0]
        tag = sample_tags[0]

        # Mock document query
        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        # Mock tag query
        mock_tag_query = Mock()
        mock_tag_query.filter.return_value.first.return_value = tag

        # Mock existing tag check (not tagged yet)
        mock_existing_query = Mock()
        mock_existing_query.filter.return_value.first.return_value = None

        mock_db_session.query.side_effect = [mock_doc_query, mock_tag_query, mock_existing_query]

        # Execute
        result = tags_service.add_tag_to_document(doc_id=101, tag_id=1, username="testuser")

        # Verify
        assert result["status"] == "tagged"
        assert result["doc_id"] == 101
        assert result["tag_id"] == 1
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_add_tag_already_tagged(self, tags_service, mock_db_session, sample_documents, sample_tags):
        """Test adding a tag that's already on the document."""
        # Setup
        doc = sample_documents[0]
        tag = sample_tags[0]
        existing_doc_tag = DBDocumentTag(document_id=doc.id, tag_id=tag.id)

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        mock_tag_query = Mock()
        mock_tag_query.filter.return_value.first.return_value = tag

        mock_existing_query = Mock()
        mock_existing_query.filter.return_value.first.return_value = existing_doc_tag

        mock_db_session.query.side_effect = [mock_doc_query, mock_tag_query, mock_existing_query]

        # Execute
        result = tags_service.add_tag_to_document(doc_id=101, tag_id=1, username="testuser")

        # Verify
        assert result["status"] == "already_tagged"
        mock_db_session.add.assert_not_called()

    def test_add_tag_document_not_found(self, tags_service, mock_db_session):
        """Test adding tag to non-existent document."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute & Verify
        with pytest.raises(ValueError, match="Document not found"):
            tags_service.add_tag_to_document(doc_id=999, tag_id=1, username="testuser")

    def test_add_tag_not_found(self, tags_service, mock_db_session, sample_documents):
        """Test adding non-existent tag to document."""
        # Setup
        doc = sample_documents[0]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        mock_tag_query = Mock()
        mock_tag_query.filter.return_value.first.return_value = None

        mock_db_session.query.side_effect = [mock_doc_query, mock_tag_query]

        # Execute & Verify
        with pytest.raises(ValueError, match="Tag not found"):
            tags_service.add_tag_to_document(doc_id=101, tag_id=999, username="testuser")

    def test_add_tag_wrong_owner(self, tags_service, mock_db_session):
        """Test adding tag to document owned by different user."""
        # Setup - document not found for this user
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute & Verify
        with pytest.raises(ValueError, match="Document not found or not owned by user"):
            tags_service.add_tag_to_document(doc_id=101, tag_id=1, username="wronguser")


class TestRemoveTagFromDocument:
    """Test suite for removing tags from documents."""

    def test_remove_tag_success(self, tags_service, mock_db_session, sample_documents):
        """Test successfully removing a tag from a document."""
        # Setup
        doc = sample_documents[0]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        mock_delete_query = Mock()
        mock_delete_query.filter.return_value.delete.return_value = 1  # 1 row deleted

        mock_db_session.query.side_effect = [mock_doc_query, mock_delete_query]

        # Execute
        result = tags_service.remove_tag_from_document(doc_id=101, tag_id=1, username="testuser")

        # Verify
        assert result["status"] == "removed"
        mock_db_session.commit.assert_called_once()

    def test_remove_tag_not_tagged(self, tags_service, mock_db_session, sample_documents):
        """Test removing a tag that wasn't on the document."""
        # Setup
        doc = sample_documents[0]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        mock_delete_query = Mock()
        mock_delete_query.filter.return_value.delete.return_value = 0  # Nothing deleted

        mock_db_session.query.side_effect = [mock_doc_query, mock_delete_query]

        # Execute
        result = tags_service.remove_tag_from_document(doc_id=101, tag_id=1, username="testuser")

        # Verify
        assert result["status"] == "not_found"

    def test_remove_tag_document_not_found(self, tags_service, mock_db_session):
        """Test removing tag from non-existent document."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute & Verify
        with pytest.raises(ValueError, match="Document not found"):
            tags_service.remove_tag_from_document(doc_id=999, tag_id=1, username="testuser")


class TestGetDocumentTags:
    """Test suite for retrieving tags for a document."""

    def test_get_document_tags_success(self, tags_service, mock_db_session, sample_documents, sample_tags):
        """Test retrieving all tags for a document."""
        # Setup
        doc = sample_documents[0]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        mock_tags_query = Mock()
        mock_tags_query.join.return_value.filter.return_value.all.return_value = sample_tags

        mock_db_session.query.side_effect = [mock_doc_query, mock_tags_query]

        # Execute
        result = tags_service.get_document_tags(doc_id=101)

        # Verify
        assert len(result) == 3
        assert result[0]["name"] == "python"
        assert result[1]["name"] == "tutorial"
        assert result[2]["name"] == "advanced"

    def test_get_document_tags_no_tags(self, tags_service, mock_db_session, sample_documents):
        """Test document with no tags."""
        # Setup
        doc = sample_documents[0]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        mock_tags_query = Mock()
        mock_tags_query.join.return_value.filter.return_value.all.return_value = []

        mock_db_session.query.side_effect = [mock_doc_query, mock_tags_query]

        # Execute
        result = tags_service.get_document_tags(doc_id=101)

        # Verify
        assert result == []

    def test_get_document_tags_document_not_found(self, tags_service, mock_db_session):
        """Test getting tags for non-existent document."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute
        result = tags_service.get_document_tags(doc_id=999)

        # Verify
        assert result == []


class TestDeleteTag:
    """Test suite for deleting tags."""

    def test_delete_tag_success(self, tags_service, mock_db_session, sample_tags):
        """Test successfully deleting a tag."""
        # Setup
        tag = sample_tags[0]

        mock_tag_query = Mock()
        mock_tag_query.filter.return_value.first.return_value = tag

        mock_doc_tags_query = Mock()
        mock_doc_tags_query.filter.return_value.delete.return_value = 3  # Removed from 3 docs

        mock_db_session.query.side_effect = [mock_tag_query, mock_doc_tags_query]

        # Execute
        result = tags_service.delete_tag(tag_id=1, username="testuser")

        # Verify
        assert result["status"] == "deleted"
        assert result["tag_id"] == 1
        mock_db_session.delete.assert_called_once_with(tag)
        mock_db_session.commit.assert_called_once()

    def test_delete_tag_not_found(self, tags_service, mock_db_session):
        """Test deleting non-existent tag."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute & Verify
        with pytest.raises(ValueError, match="Tag not found"):
            tags_service.delete_tag(tag_id=999, username="testuser")

    def test_delete_tag_removes_all_associations(self, tags_service, mock_db_session, sample_tags):
        """Test that deleting a tag removes it from all documents."""
        # Setup
        tag = sample_tags[0]

        mock_tag_query = Mock()
        mock_tag_query.filter.return_value.first.return_value = tag

        mock_doc_tags_query = Mock()
        mock_doc_tags_query.filter.return_value.delete.return_value = 10  # Removed from 10 docs

        mock_db_session.query.side_effect = [mock_tag_query, mock_doc_tags_query]

        # Execute
        result = tags_service.delete_tag(tag_id=1, username="testuser")

        # Verify - all document associations deleted
        assert result["status"] == "deleted"
        mock_doc_tags_query.filter.return_value.delete.assert_called_once()

    def test_delete_tag_wrong_owner(self, tags_service, mock_db_session):
        """Test deleting tag owned by different user."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None  # Not found for this user
        mock_db_session.query.return_value = mock_query

        # Execute & Verify
        with pytest.raises(ValueError, match="Tag not found"):
            tags_service.delete_tag(tag_id=1, username="wronguser")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_create_tag_with_special_characters(self, tags_service, mock_db_session):
        """Test creating tags with special characters in name."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute
        result = tags_service.create_tag(name="C++/C#", username="testuser", color="#3776ab")

        # Verify
        assert result["name"] == "C++/C#"

    def test_create_tag_with_very_long_name(self, tags_service, mock_db_session):
        """Test creating tag with very long name."""
        # Setup
        long_name = "a" * 200  # Very long tag name
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute - should succeed (database will truncate if needed)
        result = tags_service.create_tag(name=long_name, username="testuser")

        # Verify
        assert result["name"] == long_name

    def test_multiple_users_managing_same_tag_name(self, tags_service, mock_db_session):
        """Test that tags are properly isolated between users."""
        # User1 creates "python" tag
        mock_query1 = Mock()
        mock_query1.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query1

        result1 = tags_service.create_tag(name="python", username="user1", color="#3776ab")

        # User2 creates "python" tag
        mock_query2 = Mock()
        mock_query2.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query2

        result2 = tags_service.create_tag(name="python", username="user2", color="#00d4ff")

        # Verify both succeed with different colors
        assert result1["name"] == "python"
        assert result2["name"] == "python"
        assert result1["color"] != result2["color"]

    def test_tag_multiple_documents_at_once(self, tags_service, mock_db_session, sample_documents, sample_tags):
        """Test adding same tag to multiple documents."""
        doc1 = sample_documents[0]
        doc2 = sample_documents[1]
        tag = sample_tags[0]

        # Tag first document
        mock_db_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=doc1)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=tag)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None))))
        ]

        result1 = tags_service.add_tag_to_document(doc_id=101, tag_id=1, username="testuser")

        # Tag second document
        mock_db_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=doc2)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=tag)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None))))
        ]

        result2 = tags_service.add_tag_to_document(doc_id=102, tag_id=1, username="testuser")

        # Verify both succeeded
        assert result1["status"] == "tagged"
        assert result2["status"] == "tagged"


class TestIntegration:
    """Integration tests for complete tag workflows."""

    def test_complete_tag_lifecycle(self, tags_service, mock_db_session, sample_documents):
        """Test complete tag lifecycle: create, add to doc, remove, delete."""
        doc = sample_documents[0]

        # Step 1: Create tag
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        tag_result = tags_service.create_tag(name="python", username="testuser", color="#3776ab")
        assert tag_result["name"] == "python"

        # Step 2: Add tag to document
        tag_obj = DBTag(id=1, name="python", color="#3776ab", owner_username="testuser")
        mock_db_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=doc)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=tag_obj)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None))))
        ]
        add_result = tags_service.add_tag_to_document(doc_id=101, tag_id=1, username="testuser")
        assert add_result["status"] == "tagged"

        # Step 3: Remove tag from document
        mock_db_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=doc)))),
            Mock(filter=Mock(return_value=Mock(delete=Mock(return_value=1))))
        ]
        remove_result = tags_service.remove_tag_from_document(doc_id=101, tag_id=1, username="testuser")
        assert remove_result["status"] == "removed"

        # Step 4: Delete tag
        mock_db_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=tag_obj)))),
            Mock(filter=Mock(return_value=Mock(delete=Mock(return_value=0))))
        ]
        delete_result = tags_service.delete_tag(tag_id=1, username="testuser")
        assert delete_result["status"] == "deleted"

    def test_bulk_tagging_workflow(self, tags_service, mock_db_session, sample_documents, sample_tags):
        """Test tagging multiple documents with multiple tags."""
        docs = sample_documents
        tags = sample_tags

        # Tag each document with each tag
        for doc in docs:
            for tag in tags:
                mock_db_session.query.side_effect = [
                    Mock(filter=Mock(return_value=Mock(first=Mock(return_value=doc)))),
                    Mock(filter=Mock(return_value=Mock(first=Mock(return_value=tag)))),
                    Mock(filter=Mock(return_value=Mock(first=Mock(return_value=None))))
                ]
                result = tags_service.add_tag_to_document(doc_id=doc.doc_id, tag_id=tag.id, username="testuser")
                assert result["status"] == "tagged"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
