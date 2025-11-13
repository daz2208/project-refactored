"""
Comprehensive tests for Phase 7.4: Saved Searches

Tests saved search functionality including:
- Creating and managing saved searches
- Using saved searches (executing and tracking usage)
- Deleting saved searches
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from backend.advanced_features_service import SavedSearchesService
from backend.db_models import DBSavedSearch


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def saved_searches_service(mock_db_session):
    """Create a saved searches service instance."""
    return SavedSearchesService(mock_db_session)


@pytest.fixture
def sample_saved_searches():
    """Create sample saved searches for testing."""
    return [
        DBSavedSearch(
            id=1,
            owner_username="testuser",
            name="Python Tutorials",
            query="python programming",
            filters={"skill_level": "beginner"},
            use_count=5,
            last_used_at=datetime(2025, 1, 10, 10, 0, 0),
            created_at=datetime(2025, 1, 1, 10, 0, 0)
        ),
        DBSavedSearch(
            id=2,
            owner_username="testuser",
            name="JavaScript Frameworks",
            query="react vue angular",
            filters={"source_type": "url", "cluster_id": 3},
            use_count=10,
            last_used_at=datetime(2025, 1, 12, 15, 30, 0),
            created_at=datetime(2025, 1, 2, 10, 0, 0)
        ),
        DBSavedSearch(
            id=3,
            owner_username="testuser",
            name="Recent ML Papers",
            query="machine learning",
            filters={"date_from": "2025-01-01"},
            use_count=0,
            last_used_at=None,
            created_at=datetime(2025, 1, 15, 10, 0, 0)
        ),
    ]


class TestSaveSearch:
    """Test suite for saving search queries."""

    def test_save_search_success(self, saved_searches_service, mock_db_session):
        """Test successfully saving a search query."""
        # Execute
        result = saved_searches_service.save_search(
            name="Python Tutorials",
            query="python programming",
            filters={"skill_level": "beginner"},
            username="testuser"
        )

        # Verify
        assert "id" in result
        assert result["name"] == "Python Tutorials"
        assert result["query"] == "python programming"
        assert result["filters"] == {"skill_level": "beginner"}
        assert "created_at" in result
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_save_search_no_filters(self, saved_searches_service, mock_db_session):
        """Test saving search without filters."""
        # Execute
        result = saved_searches_service.save_search(
            name="Simple Search",
            query="database",
            filters=None,
            username="testuser"
        )

        # Verify
        assert result["name"] == "Simple Search"
        assert result["query"] == "database"
        assert result["filters"] is None

    def test_save_search_empty_query(self, saved_searches_service, mock_db_session):
        """Test saving search with empty query string."""
        # Execute - should still work, some users might want to save filter-only searches
        result = saved_searches_service.save_search(
            name="All Beginners",
            query="",
            filters={"skill_level": "beginner"},
            username="testuser"
        )

        # Verify
        assert result["query"] == ""
        assert result["filters"] == {"skill_level": "beginner"}

    def test_save_search_complex_filters(self, saved_searches_service, mock_db_session):
        """Test saving search with complex filters."""
        # Execute
        complex_filters = {
            "cluster_id": 5,
            "source_type": "url",
            "skill_level": "advanced",
            "date_from": "2025-01-01",
            "date_to": "2025-12-31"
        }

        result = saved_searches_service.save_search(
            name="Advanced URL Content 2025",
            query="tutorial guide",
            filters=complex_filters,
            username="testuser"
        )

        # Verify
        assert result["filters"] == complex_filters

    def test_save_search_duplicate_name_allowed(self, saved_searches_service, mock_db_session):
        """Test that duplicate search names are allowed (user might want multiple versions)."""
        # Execute - save two searches with same name
        result1 = saved_searches_service.save_search(
            name="Python",
            query="python basics",
            filters=None,
            username="testuser"
        )

        result2 = saved_searches_service.save_search(
            name="Python",
            query="python advanced",
            filters={"skill_level": "advanced"},
            username="testuser"
        )

        # Verify - both should succeed
        assert result1["name"] == "Python"
        assert result2["name"] == "Python"
        assert result1["query"] != result2["query"]


class TestGetSavedSearches:
    """Test suite for retrieving saved searches."""

    def test_get_saved_searches_success(self, saved_searches_service, mock_db_session, sample_saved_searches):
        """Test retrieving all saved searches for a user."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = sample_saved_searches
        mock_db_session.query.return_value = mock_query

        # Execute
        result = saved_searches_service.get_saved_searches("testuser")

        # Verify
        assert len(result) == 3
        assert result[0]["name"] == "Python Tutorials"
        assert result[0]["use_count"] == 5
        assert result[1]["name"] == "JavaScript Frameworks"
        assert result[1]["use_count"] == 10
        assert result[2]["use_count"] == 0  # Never used
        assert result[2]["last_used_at"] is None

    def test_get_saved_searches_empty(self, saved_searches_service, mock_db_session):
        """Test retrieving searches when user has none."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db_session.query.return_value = mock_query

        # Execute
        result = saved_searches_service.get_saved_searches("testuser")

        # Verify
        assert result == []

    def test_get_saved_searches_ordered_by_last_used(self, saved_searches_service, mock_db_session, sample_saved_searches):
        """Test that searches are ordered by last_used_at (most recent first)."""
        # Setup - searches should be ordered by last_used_at descending
        ordered_searches = sorted(
            sample_saved_searches,
            key=lambda s: s.last_used_at if s.last_used_at else datetime.min,
            reverse=True
        )

        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = ordered_searches
        mock_db_session.query.return_value = mock_query

        # Execute
        result = saved_searches_service.get_saved_searches("testuser")

        # Verify - most recently used should be first
        assert len(result) == 3
        # JavaScript Frameworks was used most recently (2025-01-12)
        assert result[0]["name"] == "JavaScript Frameworks"

    def test_get_saved_searches_filters_preserved(self, saved_searches_service, mock_db_session, sample_saved_searches):
        """Test that filter objects are properly returned."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = sample_saved_searches
        mock_db_session.query.return_value = mock_query

        # Execute
        result = saved_searches_service.get_saved_searches("testuser")

        # Verify filters
        assert result[0]["filters"] == {"skill_level": "beginner"}
        assert result[1]["filters"] == {"source_type": "url", "cluster_id": 3}
        assert result[2]["filters"] == {"date_from": "2025-01-01"}


class TestUseSavedSearch:
    """Test suite for using saved searches."""

    def test_use_saved_search_success(self, saved_searches_service, mock_db_session, sample_saved_searches):
        """Test successfully using a saved search."""
        # Setup
        search = sample_saved_searches[0]
        original_use_count = search.use_count

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = search
        mock_db_session.query.return_value = mock_query

        # Execute
        result = saved_searches_service.use_saved_search(search_id=1, username="testuser")

        # Verify
        assert result["query"] == "python programming"
        assert result["filters"] == {"skill_level": "beginner"}
        assert search.use_count == original_use_count + 1
        assert search.last_used_at is not None
        mock_db_session.commit.assert_called_once()

    def test_use_saved_search_increments_count(self, saved_searches_service, mock_db_session, sample_saved_searches):
        """Test that use count is properly incremented."""
        # Setup
        search = sample_saved_searches[0]
        original_count = search.use_count

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = search
        mock_db_session.query.return_value = mock_query

        # Execute multiple times
        saved_searches_service.use_saved_search(search_id=1, username="testuser")
        saved_searches_service.use_saved_search(search_id=1, username="testuser")
        saved_searches_service.use_saved_search(search_id=1, username="testuser")

        # Verify count increased by 3
        assert search.use_count == original_count + 3

    def test_use_saved_search_updates_last_used_time(self, saved_searches_service, mock_db_session, sample_saved_searches):
        """Test that last_used_at timestamp is updated."""
        # Setup
        search = sample_saved_searches[2]  # Never used before
        assert search.last_used_at is None

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = search
        mock_db_session.query.return_value = mock_query

        # Execute
        saved_searches_service.use_saved_search(search_id=3, username="testuser")

        # Verify timestamp is now set
        assert search.last_used_at is not None
        assert isinstance(search.last_used_at, datetime)

    def test_use_saved_search_not_found(self, saved_searches_service, mock_db_session):
        """Test using non-existent saved search."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute & Verify
        with pytest.raises(ValueError, match="Saved search not found"):
            saved_searches_service.use_saved_search(search_id=999, username="testuser")

    def test_use_saved_search_wrong_owner(self, saved_searches_service, mock_db_session):
        """Test using saved search owned by different user."""
        # Setup - not found for this user
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Execute & Verify
        with pytest.raises(ValueError, match="Saved search not found"):
            saved_searches_service.use_saved_search(search_id=1, username="wronguser")

    def test_use_saved_search_returns_correct_data(self, saved_searches_service, mock_db_session, sample_saved_searches):
        """Test that use_saved_search returns the right query and filters."""
        # Setup
        search = sample_saved_searches[1]  # JavaScript search with filters

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = search
        mock_db_session.query.return_value = mock_query

        # Execute
        result = saved_searches_service.use_saved_search(search_id=2, username="testuser")

        # Verify returned data
        assert result["query"] == "react vue angular"
        assert result["filters"] == {"source_type": "url", "cluster_id": 3}


class TestDeleteSavedSearch:
    """Test suite for deleting saved searches."""

    def test_delete_saved_search_success(self, saved_searches_service, mock_db_session):
        """Test successfully deleting a saved search."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = 1  # 1 row deleted
        mock_db_session.query.return_value = mock_query

        # Execute
        result = saved_searches_service.delete_saved_search(search_id=1, username="testuser")

        # Verify
        assert result["status"] == "deleted"
        mock_db_session.commit.assert_called_once()

    def test_delete_saved_search_not_found(self, saved_searches_service, mock_db_session):
        """Test deleting non-existent saved search."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = 0  # Nothing deleted
        mock_db_session.query.return_value = mock_query

        # Execute
        result = saved_searches_service.delete_saved_search(search_id=999, username="testuser")

        # Verify
        assert result["status"] == "not_found"

    def test_delete_saved_search_wrong_owner(self, saved_searches_service, mock_db_session):
        """Test deleting saved search owned by different user."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = 0  # Not found for this user
        mock_db_session.query.return_value = mock_query

        # Execute
        result = saved_searches_service.delete_saved_search(search_id=1, username="wronguser")

        # Verify
        assert result["status"] == "not_found"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_save_search_very_long_query(self, saved_searches_service, mock_db_session):
        """Test saving search with very long query string."""
        # Setup
        long_query = "python " * 200  # Very long query

        # Execute
        result = saved_searches_service.save_search(
            name="Long Query",
            query=long_query,
            filters=None,
            username="testuser"
        )

        # Verify
        assert result["query"] == long_query

    def test_save_search_special_characters_in_query(self, saved_searches_service, mock_db_session):
        """Test saving search with special characters."""
        # Setup
        special_query = "C++ OR C# AND .NET (framework)"

        # Execute
        result = saved_searches_service.save_search(
            name="C++ and C# Search",
            query=special_query,
            filters=None,
            username="testuser"
        )

        # Verify
        assert result["query"] == special_query

    def test_save_search_unicode_characters(self, saved_searches_service, mock_db_session):
        """Test saving search with unicode characters."""
        # Execute
        result = saved_searches_service.save_search(
            name="Python 教程",
            query="编程 プログラミング",
            filters=None,
            username="testuser"
        )

        # Verify
        assert result["name"] == "Python 教程"
        assert result["query"] == "编程 プログラミング"

    def test_use_search_multiple_times_rapidly(self, saved_searches_service, mock_db_session, sample_saved_searches):
        """Test using same search multiple times in quick succession."""
        # Setup
        search = sample_saved_searches[0]
        original_count = search.use_count

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = search
        mock_db_session.query.return_value = mock_query

        # Execute - use search 10 times
        for _ in range(10):
            result = saved_searches_service.use_saved_search(search_id=1, username="testuser")
            assert result["query"] == search.query

        # Verify count increased by 10
        assert search.use_count == original_count + 10

    def test_filters_with_null_values(self, saved_searches_service, mock_db_session):
        """Test saving filters with null values."""
        # Execute
        result = saved_searches_service.save_search(
            name="Test Search",
            query="test",
            filters={"cluster_id": None, "skill_level": "beginner"},
            username="testuser"
        )

        # Verify
        assert result["filters"]["cluster_id"] is None
        assert result["filters"]["skill_level"] == "beginner"

    def test_save_many_searches_single_user(self, saved_searches_service, mock_db_session):
        """Test user saving many searches (100+)."""
        # Execute - save 150 searches
        for i in range(150):
            result = saved_searches_service.save_search(
                name=f"Search {i}",
                query=f"query {i}",
                filters=None,
                username="testuser"
            )
            assert result["name"] == f"Search {i}"

        # Verify all were created
        assert mock_db_session.add.call_count == 150


class TestIntegration:
    """Integration tests for complete saved search workflows."""

    def test_complete_saved_search_lifecycle(self, saved_searches_service, mock_db_session):
        """Test complete lifecycle: save, use multiple times, delete."""
        # Step 1: Save search
        save_result = saved_searches_service.save_search(
            name="Python Basics",
            query="python programming fundamentals",
            filters={"skill_level": "beginner"},
            username="testuser"
        )
        assert save_result["name"] == "Python Basics"
        search_id = save_result["id"]

        # Step 2: Use search multiple times
        search = DBSavedSearch(
            id=search_id,
            owner_username="testuser",
            name="Python Basics",
            query="python programming fundamentals",
            filters={"skill_level": "beginner"},
            use_count=0,
            last_used_at=None
        )

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = search
        mock_db_session.query.return_value = mock_query

        for _ in range(5):
            use_result = saved_searches_service.use_saved_search(search_id, "testuser")
            assert use_result["query"] == "python programming fundamentals"

        # Verify usage tracking
        assert search.use_count == 5
        assert search.last_used_at is not None

        # Step 3: Delete search
        mock_db_session.query.return_value.filter.return_value.delete.return_value = 1
        delete_result = saved_searches_service.delete_saved_search(search_id, "testuser")
        assert delete_result["status"] == "deleted"

    def test_multiple_users_independent_searches(self, saved_searches_service, mock_db_session):
        """Test that different users have independent saved searches."""
        # User 1 saves search
        result1 = saved_searches_service.save_search(
            name="React Tutorial",
            query="react hooks",
            filters=None,
            username="user1"
        )

        # User 2 saves search with same name
        result2 = saved_searches_service.save_search(
            name="React Tutorial",
            query="react class components",
            filters=None,
            username="user2"
        )

        # Verify both succeeded with different queries
        assert result1["name"] == "React Tutorial"
        assert result2["name"] == "React Tutorial"
        assert result1["query"] != result2["query"]

    def test_update_search_usage_pattern(self, saved_searches_service, mock_db_session, sample_saved_searches):
        """Test realistic usage pattern over time."""
        # Setup
        search = sample_saved_searches[0]
        search.use_count = 0
        search.last_used_at = None

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = search
        mock_db_session.query.return_value = mock_query

        # Simulate usage over time
        usage_times = []
        for i in range(20):
            saved_searches_service.use_saved_search(search_id=1, username="testuser")
            usage_times.append(search.last_used_at)

        # Verify
        assert search.use_count == 20
        # Each usage should update timestamp
        assert len(set(usage_times)) > 1  # Timestamps should be different

    def test_search_filter_combinations(self, saved_searches_service, mock_db_session):
        """Test various filter combinations that users might create."""
        filter_combinations = [
            {"cluster_id": 5},
            {"source_type": "url", "skill_level": "advanced"},
            {"date_from": "2025-01-01", "date_to": "2025-12-31"},
            {"cluster_id": 3, "source_type": "file", "skill_level": "intermediate"},
            {}  # Empty filters
        ]

        for idx, filters in enumerate(filter_combinations):
            result = saved_searches_service.save_search(
                name=f"Test Search {idx}",
                query="test",
                filters=filters,
                username="testuser"
            )
            assert result["filters"] == filters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
