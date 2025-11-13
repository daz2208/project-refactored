"""
Comprehensive tests for Phase 7.5: Document Relationships

Tests document relationship functionality including:
- Creating relationships between documents
- Querying related documents
- Different relationship types
- Bidirectional relationships
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from backend.advanced_features_service import DocumentRelationshipsService
from backend.db_models import DBDocument, DBDocumentRelationship


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def relationships_service(mock_db_session):
    """Create a document relationships service instance."""
    return DocumentRelationshipsService(mock_db_session)


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        DBDocument(id=1, doc_id=101, owner_username="testuser", source_type="text", skill_level="beginner", cluster_id=1),
        DBDocument(id=2, doc_id=102, owner_username="testuser", source_type="url", skill_level="intermediate", cluster_id=1),
        DBDocument(id=3, doc_id=103, owner_username="testuser", source_type="file", skill_level="advanced", cluster_id=2),
        DBDocument(id=4, doc_id=104, owner_username="testuser", source_type="text", skill_level="beginner", cluster_id=1),
        DBDocument(id=5, doc_id=105, owner_username="user2", source_type="text", skill_level="beginner", cluster_id=3),
    ]


@pytest.fixture
def sample_relationships():
    """Create sample relationships for testing."""
    return [
        DBDocumentRelationship(
            id=1,
            source_doc_id=1,  # Internal ID
            target_doc_id=2,
            relationship_type="related",
            strength=0.85,
            created_by_username="testuser",
            created_at=datetime.utcnow()
        ),
        DBDocumentRelationship(
            id=2,
            source_doc_id=1,
            target_doc_id=3,
            relationship_type="prerequisite",
            strength=None,
            created_by_username="testuser",
            created_at=datetime.utcnow()
        ),
        DBDocumentRelationship(
            id=3,
            source_doc_id=2,
            target_doc_id=4,
            relationship_type="followup",
            strength=0.92,
            created_by_username="testuser",
            created_at=datetime.utcnow()
        ),
    ]


class TestAddRelationship:
    """Test suite for creating document relationships."""

    def test_add_relationship_success(self, relationships_service, mock_db_session, sample_documents):
        """Test successfully creating a relationship between two documents."""
        # Setup
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        # Mock document queries
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [source_doc, target_doc]
        mock_db_session.query.return_value = mock_query

        # Mock existing relationship check (none exists)
        mock_existing_query = Mock()
        mock_existing_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_existing_query

        # Execute
        result = relationships_service.add_relationship(
            source_doc_id=101,
            target_doc_id=102,
            relationship_type="related",
            username="testuser",
            strength=0.85
        )

        # Verify
        assert result["status"] == "created"
        assert result["source_doc_id"] == 101
        assert result["target_doc_id"] == 102
        assert result["type"] == "related"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_add_relationship_prerequisite_type(self, relationships_service, mock_db_session, sample_documents):
        """Test creating a prerequisite relationship."""
        # Setup
        source_doc = sample_documents[0]
        target_doc = sample_documents[2]

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            source_doc, target_doc, None
        ]

        # Execute
        result = relationships_service.add_relationship(
            source_doc_id=101,
            target_doc_id=103,
            relationship_type="prerequisite",
            username="testuser"
        )

        # Verify
        assert result["status"] == "created"
        assert result["type"] == "prerequisite"

    def test_add_relationship_all_types(self, relationships_service, mock_db_session, sample_documents):
        """Test creating relationships of all supported types."""
        relationship_types = ["related", "prerequisite", "followup", "alternative", "supersedes"]

        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        for rel_type in relationship_types:
            # Mock queries for each iteration
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [
                source_doc, target_doc, None
            ]

            result = relationships_service.add_relationship(
                source_doc_id=101,
                target_doc_id=102,
                relationship_type=rel_type,
                username="testuser"
            )

            assert result["status"] == "created"
            assert result["type"] == rel_type

    def test_add_relationship_with_strength(self, relationships_service, mock_db_session, sample_documents):
        """Test creating relationship with strength score."""
        # Setup
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            source_doc, target_doc, None
        ]

        # Execute
        result = relationships_service.add_relationship(
            source_doc_id=101,
            target_doc_id=102,
            relationship_type="related",
            username="testuser",
            strength=0.95
        )

        # Verify
        assert result["status"] == "created"

    def test_add_relationship_without_strength(self, relationships_service, mock_db_session, sample_documents):
        """Test creating relationship without strength score."""
        # Setup
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            source_doc, target_doc, None
        ]

        # Execute
        result = relationships_service.add_relationship(
            source_doc_id=101,
            target_doc_id=102,
            relationship_type="prerequisite",
            username="testuser",
            strength=None
        )

        # Verify
        assert result["status"] == "created"

    def test_add_relationship_already_exists(self, relationships_service, mock_db_session, sample_documents, sample_relationships):
        """Test creating relationship that already exists."""
        # Setup
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]
        existing_rel = sample_relationships[0]

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            source_doc, target_doc, existing_rel
        ]

        # Execute
        result = relationships_service.add_relationship(
            source_doc_id=101,
            target_doc_id=102,
            relationship_type="related",
            username="testuser"
        )

        # Verify
        assert result["status"] == "already_exists"
        assert "relationship_id" in result

    def test_add_relationship_source_document_not_found(self, relationships_service, mock_db_session):
        """Test creating relationship when source document doesn't exist."""
        # Setup
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Execute & Verify
        with pytest.raises(ValueError, match="One or both documents not found"):
            relationships_service.add_relationship(
                source_doc_id=999,
                target_doc_id=102,
                relationship_type="related",
                username="testuser"
            )

    def test_add_relationship_target_document_not_found(self, relationships_service, mock_db_session, sample_documents):
        """Test creating relationship when target document doesn't exist."""
        # Setup
        source_doc = sample_documents[0]

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            source_doc, None
        ]

        # Execute & Verify
        with pytest.raises(ValueError, match="One or both documents not found"):
            relationships_service.add_relationship(
                source_doc_id=101,
                target_doc_id=999,
                relationship_type="related",
                username="testuser"
            )

    def test_add_relationship_wrong_owner(self, relationships_service, mock_db_session, sample_documents):
        """Test creating relationship for documents not owned by user."""
        # Setup - documents belong to different user
        wrong_owner_doc = sample_documents[4]  # Belongs to user2

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            None, wrong_owner_doc
        ]

        # Execute & Verify
        with pytest.raises(ValueError, match="One or both documents not found"):
            relationships_service.add_relationship(
                source_doc_id=101,
                target_doc_id=105,
                relationship_type="related",
                username="testuser"
            )


class TestGetRelatedDocuments:
    """Test suite for retrieving related documents."""

    def test_get_related_documents_success(self, relationships_service, mock_db_session, sample_documents, sample_relationships):
        """Test retrieving all documents related to a given document."""
        # Setup
        doc = sample_documents[0]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        mock_rel_query = Mock()
        mock_rel_query.filter.return_value.all.return_value = sample_relationships[:2]  # Doc 1 has 2 relationships

        # Setup document queries for related docs
        target_doc1 = sample_documents[1]
        target_doc2 = sample_documents[2]

        mock_related_doc_query = Mock()
        mock_related_doc_query.filter.return_value.first.side_effect = [target_doc1, target_doc2]

        mock_db_session.query.side_effect = [mock_doc_query, mock_rel_query, mock_related_doc_query, mock_related_doc_query]

        # Execute
        result = relationships_service.get_related_documents(doc_id=101, relationship_type=None)

        # Verify
        assert len(result) == 2
        assert result[0]["doc_id"] in [102, 103]
        assert result[0]["direction"] == "outgoing"

    def test_get_related_documents_filter_by_type(self, relationships_service, mock_db_session, sample_documents, sample_relationships):
        """Test filtering related documents by relationship type."""
        # Setup
        doc = sample_documents[0]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        # Only return prerequisite relationships
        prerequisite_rel = sample_relationships[1]
        mock_rel_query = Mock()
        mock_rel_query.filter.return_value.filter.return_value.all.return_value = [prerequisite_rel]

        target_doc = sample_documents[2]
        mock_related_doc_query = Mock()
        mock_related_doc_query.filter.return_value.first.return_value = target_doc

        mock_db_session.query.side_effect = [mock_doc_query, mock_rel_query, mock_related_doc_query]

        # Execute
        result = relationships_service.get_related_documents(doc_id=101, relationship_type="prerequisite")

        # Verify
        assert len(result) == 1
        assert result[0]["relationship_type"] == "prerequisite"

    def test_get_related_documents_bidirectional(self, relationships_service, mock_db_session, sample_documents):
        """Test that relationships work both ways (incoming and outgoing)."""
        # Setup - doc 102 is both source and target of relationships
        doc = sample_documents[1]  # doc_id 102

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        # Create relationships where 102 is both source and target
        rel_outgoing = DBDocumentRelationship(
            id=1,
            source_doc_id=2,  # doc 102 is source
            target_doc_id=3,
            relationship_type="related",
            strength=0.85
        )

        rel_incoming = DBDocumentRelationship(
            id=2,
            source_doc_id=1,  # doc 101 is source
            target_doc_id=2,  # doc 102 is target
            relationship_type="prerequisite",
            strength=0.90
        )

        mock_rel_query = Mock()
        mock_rel_query.filter.return_value.all.return_value = [rel_outgoing, rel_incoming]

        # Setup related document queries
        target_doc = sample_documents[2]  # doc 103
        source_doc = sample_documents[0]  # doc 101

        mock_related_doc_query = Mock()
        mock_related_doc_query.filter.return_value.first.side_effect = [target_doc, source_doc]

        mock_db_session.query.side_effect = [mock_doc_query, mock_rel_query, mock_related_doc_query, mock_related_doc_query]

        # Execute
        result = relationships_service.get_related_documents(doc_id=102)

        # Verify
        assert len(result) == 2
        # Check directions
        directions = [r["direction"] for r in result]
        assert "outgoing" in directions
        assert "incoming" in directions

    def test_get_related_documents_no_relationships(self, relationships_service, mock_db_session, sample_documents):
        """Test document with no relationships."""
        # Setup
        doc = sample_documents[3]  # doc with no relationships

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        mock_rel_query = Mock()
        mock_rel_query.filter.return_value.all.return_value = []

        mock_db_session.query.side_effect = [mock_doc_query, mock_rel_query]

        # Execute
        result = relationships_service.get_related_documents(doc_id=104)

        # Verify
        assert result == []

    def test_get_related_documents_not_found(self, relationships_service, mock_db_session):
        """Test getting relationships for non-existent document."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute
        result = relationships_service.get_related_documents(doc_id=999)

        # Verify
        assert result == []

    def test_get_related_documents_includes_metadata(self, relationships_service, mock_db_session, sample_documents, sample_relationships):
        """Test that related documents include metadata."""
        # Setup
        doc = sample_documents[0]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.return_value = doc

        mock_rel_query = Mock()
        mock_rel_query.filter.return_value.all.return_value = [sample_relationships[0]]

        target_doc = sample_documents[1]
        mock_related_doc_query = Mock()
        mock_related_doc_query.filter.return_value.first.return_value = target_doc

        mock_db_session.query.side_effect = [mock_doc_query, mock_rel_query, mock_related_doc_query]

        # Execute
        result = relationships_service.get_related_documents(doc_id=101)

        # Verify metadata is included
        assert len(result) == 1
        assert "source_type" in result[0]
        assert "skill_level" in result[0]
        assert "cluster_id" in result[0]
        assert result[0]["source_type"] == "url"
        assert result[0]["skill_level"] == "intermediate"


class TestDeleteRelationship:
    """Test suite for deleting relationships."""

    def test_delete_relationship_success(self, relationships_service, mock_db_session, sample_documents):
        """Test successfully deleting a relationship."""
        # Setup
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.side_effect = [source_doc, target_doc]

        mock_delete_query = Mock()
        mock_delete_query.filter.return_value.delete.return_value = 1  # 1 row deleted

        mock_db_session.query.side_effect = [mock_doc_query, mock_doc_query, mock_delete_query]

        # Execute
        result = relationships_service.delete_relationship(
            source_doc_id=101,
            target_doc_id=102,
            username="testuser"
        )

        # Verify
        assert result["status"] == "deleted"
        mock_db_session.commit.assert_called_once()

    def test_delete_relationship_not_found(self, relationships_service, mock_db_session, sample_documents):
        """Test deleting non-existent relationship."""
        # Setup
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        mock_doc_query = Mock()
        mock_doc_query.filter.return_value.first.side_effect = [source_doc, target_doc]

        mock_delete_query = Mock()
        mock_delete_query.filter.return_value.delete.return_value = 0  # Nothing deleted

        mock_db_session.query.side_effect = [mock_doc_query, mock_doc_query, mock_delete_query]

        # Execute
        result = relationships_service.delete_relationship(
            source_doc_id=101,
            target_doc_id=102,
            username="testuser"
        )

        # Verify
        assert result["status"] == "not_found"

    def test_delete_relationship_document_not_found(self, relationships_service, mock_db_session):
        """Test deleting relationship when document doesn't exist."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute & Verify
        with pytest.raises(ValueError, match="Document not found"):
            relationships_service.delete_relationship(
                source_doc_id=999,
                target_doc_id=102,
                username="testuser"
            )

    def test_delete_relationship_wrong_owner(self, relationships_service, mock_db_session):
        """Test deleting relationship for documents not owned by user."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute & Verify
        with pytest.raises(ValueError, match="Document not found"):
            relationships_service.delete_relationship(
                source_doc_id=101,
                target_doc_id=102,
                username="wronguser"
            )


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_circular_relationship(self, relationships_service, mock_db_session, sample_documents):
        """Test creating relationships that form a circle."""
        # Setup - create A -> B -> C -> A
        doc_a = sample_documents[0]
        doc_b = sample_documents[1]
        doc_c = sample_documents[2]

        # A -> B
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [doc_a, doc_b, None]
        result1 = relationships_service.add_relationship(101, 102, "related", "testuser")
        assert result1["status"] == "created"

        # B -> C
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [doc_b, doc_c, None]
        result2 = relationships_service.add_relationship(102, 103, "related", "testuser")
        assert result2["status"] == "created"

        # C -> A (completes circle)
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [doc_c, doc_a, None]
        result3 = relationships_service.add_relationship(103, 101, "related", "testuser")
        assert result3["status"] == "created"

    def test_self_relationship(self, relationships_service, mock_db_session, sample_documents):
        """Test creating relationship from document to itself."""
        # Setup
        doc = sample_documents[0]

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [doc, doc, None]

        # Execute - should succeed (database constraint might prevent, but service allows)
        result = relationships_service.add_relationship(
            source_doc_id=101,
            target_doc_id=101,
            relationship_type="related",
            username="testuser"
        )

        # Verify
        assert result["status"] == "created"

    def test_multiple_relationship_types_same_documents(self, relationships_service, mock_db_session, sample_documents):
        """Test creating multiple relationships of different types between same documents."""
        # Setup
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        # Create "related" relationship
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [source_doc, target_doc, None]
        result1 = relationships_service.add_relationship(101, 102, "related", "testuser")
        assert result1["status"] == "created"

        # Create "prerequisite" relationship (same docs, different type)
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [source_doc, target_doc, None]
        result2 = relationships_service.add_relationship(101, 102, "prerequisite", "testuser")
        assert result2["status"] == "created"

    def test_relationship_strength_boundaries(self, relationships_service, mock_db_session, sample_documents):
        """Test relationship strength at boundaries (0.0, 1.0)."""
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        # Test strength = 0.0
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [source_doc, target_doc, None]
        result1 = relationships_service.add_relationship(101, 102, "related", "testuser", strength=0.0)
        assert result1["status"] == "created"

        # Test strength = 1.0
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [source_doc, target_doc, None]
        result2 = relationships_service.add_relationship(101, 103, "related", "testuser", strength=1.0)
        assert result2["status"] == "created"

    def test_large_relationship_network(self, relationships_service, mock_db_session, sample_documents):
        """Test document with many relationships (100+)."""
        # Setup - one document related to 100 others
        source_doc = sample_documents[0]

        for i in range(100):
            target_doc = Mock()
            target_doc.id = i + 10
            target_doc.doc_id = 200 + i
            target_doc.owner_username = "testuser"

            mock_db_session.query.return_value.filter.return_value.first.side_effect = [source_doc, target_doc, None]

            result = relationships_service.add_relationship(
                source_doc_id=101,
                target_doc_id=200 + i,
                relationship_type="related",
                username="testuser"
            )
            assert result["status"] == "created"

    def test_relationship_types_case_sensitivity(self, relationships_service, mock_db_session, sample_documents):
        """Test that relationship types are case-sensitive."""
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        # Create with lowercase
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [source_doc, target_doc, None]
        result1 = relationships_service.add_relationship(101, 102, "related", "testuser")

        # Create with uppercase (should be treated as different type)
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [source_doc, target_doc, None]
        result2 = relationships_service.add_relationship(101, 102, "RELATED", "testuser")

        # Both should succeed as they're different types
        assert result1["status"] == "created"
        assert result2["status"] == "created"


class TestIntegration:
    """Integration tests for complete relationship workflows."""

    def test_complete_relationship_lifecycle(self, relationships_service, mock_db_session, sample_documents):
        """Test complete lifecycle: create, query, delete."""
        source_doc = sample_documents[0]
        target_doc = sample_documents[1]

        # Step 1: Create relationship
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [source_doc, target_doc, None]
        create_result = relationships_service.add_relationship(101, 102, "related", "testuser")
        assert create_result["status"] == "created"

        # Step 2: Query relationships
        mock_db_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=source_doc)))),
            Mock(filter=Mock(return_value=Mock(all=Mock(return_value=[
                DBDocumentRelationship(id=1, source_doc_id=1, target_doc_id=2, relationship_type="related", strength=0.85)
            ])))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=target_doc))))
        ]
        query_result = relationships_service.get_related_documents(101)
        assert len(query_result) == 1
        assert query_result[0]["doc_id"] == 102

        # Step 3: Delete relationship
        mock_db_session.query.side_effect = [
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=source_doc)))),
            Mock(filter=Mock(return_value=Mock(first=Mock(return_value=target_doc)))),
            Mock(filter=Mock(return_value=Mock(delete=Mock(return_value=1))))
        ]
        delete_result = relationships_service.delete_relationship(101, 102, "testuser")
        assert delete_result["status"] == "deleted"

    def test_build_knowledge_graph(self, relationships_service, mock_db_session, sample_documents):
        """Test building a knowledge graph with multiple relationship types."""
        # Create a learning path: Beginner -> Intermediate -> Advanced
        docs = sample_documents[:3]

        # Beginner -> Intermediate (prerequisite)
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [docs[0], docs[1], None]
        rel1 = relationships_service.add_relationship(101, 102, "prerequisite", "testuser")

        # Intermediate -> Advanced (prerequisite)
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [docs[1], docs[2], None]
        rel2 = relationships_service.add_relationship(102, 103, "prerequisite", "testuser")

        # Add alternative paths
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [docs[0], docs[2], None]
        rel3 = relationships_service.add_relationship(101, 103, "alternative", "testuser")

        # Verify all relationships created
        assert rel1["status"] == "created"
        assert rel2["status"] == "created"
        assert rel3["status"] == "created"

    def test_relationship_discovery_simulation(self, relationships_service, mock_db_session, sample_documents):
        """Test simulating AI-discovered relationships with strength scores."""
        # Simulate AI discovering related documents with confidence scores
        source_doc = sample_documents[0]
        discovered_relationships = [
            (102, 0.92),  # High confidence
            (103, 0.75),  # Medium confidence
            (104, 0.55),  # Low confidence
        ]

        for target_id, strength in discovered_relationships:
            target_doc = next(d for d in sample_documents if d.doc_id == target_id)
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [source_doc, target_doc, None]

            result = relationships_service.add_relationship(
                source_doc_id=101,
                target_doc_id=target_id,
                relationship_type="related",
                username="testuser",
                strength=strength
            )
            assert result["status"] == "created"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
