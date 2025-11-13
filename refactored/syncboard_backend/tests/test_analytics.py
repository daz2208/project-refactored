"""
Tests for analytics dashboard functionality (Phase 7.1).
"""

import pytest
from datetime import datetime, timedelta
from backend.analytics_service import AnalyticsService
from backend.db_models import (
    DBDocument,
    DBCluster,
    DBConcept,
    DBUser,
    DBVectorDocument
)


@pytest.fixture
def analytics_service(db_session):
    """Create analytics service with test database."""
    return AnalyticsService(db_session)


@pytest.fixture
def sample_data(db_session):
    """Create sample data for analytics tests."""
    # Create user
    user = DBUser(username="testuser", hashed_password="hashed")
    db_session.add(user)

    # Create clusters
    cluster1 = DBCluster(id=1, name="Python Basics", skill_level="beginner")
    cluster2 = DBCluster(id=2, name="Web Development", skill_level="intermediate")
    db_session.add_all([cluster1, cluster2])

    # Create documents with different timestamps
    now = datetime.utcnow()
    docs = [
        DBDocument(
            doc_id=1,
            owner_username="testuser",
            source_type="text",
            skill_level="beginner",
            cluster_id=1,
            created_at=now
        ),
        DBDocument(
            doc_id=2,
            owner_username="testuser",
            source_type="url",
            skill_level="beginner",
            cluster_id=1,
            created_at=now - timedelta(days=1)
        ),
        DBDocument(
            doc_id=3,
            owner_username="testuser",
            source_type="file",
            skill_level="intermediate",
            cluster_id=2,
            created_at=now - timedelta(days=7)
        ),
        DBDocument(
            doc_id=4,
            owner_username="testuser",
            source_type="text",
            skill_level="intermediate",
            cluster_id=2,
            created_at=now - timedelta(days=15)
        ),
    ]
    db_session.add_all(docs)

    # Create concepts
    concepts = [
        DBConcept(doc_id=1, concept_text="variables"),
        DBConcept(doc_id=1, concept_text="functions"),
        DBConcept(doc_id=2, concept_text="variables"),
        DBConcept(doc_id=3, concept_text="html"),
        DBConcept(doc_id=4, concept_text="css"),
    ]
    db_session.add_all(concepts)

    # Create vector documents
    vector_docs = [
        DBVectorDocument(doc_id=1, content="Python basics content"),
        DBVectorDocument(doc_id=2, content="More Python content"),
        DBVectorDocument(doc_id=3, content="Web dev content"),
        DBVectorDocument(doc_id=4, content="Advanced web content"),
    ]
    db_session.add_all(vector_docs)

    db_session.commit()
    return {"user": user, "clusters": [cluster1, cluster2], "docs": docs}


class TestAnalyticsService:
    """Test analytics service methods."""

    def test_get_overview_stats(self, analytics_service, sample_data):
        """Test overview statistics calculation."""
        stats = analytics_service.get_overview_stats(username="testuser")

        assert stats["total_documents"] == 4
        assert stats["total_clusters"] == 2
        assert stats["total_concepts"] == 5
        assert stats["documents_today"] >= 1
        assert stats["documents_this_week"] >= 2
        assert stats["documents_this_month"] == 4
        assert "last_updated" in stats

    def test_get_time_series_data(self, analytics_service, sample_data):
        """Test time series data generation."""
        time_series = analytics_service.get_time_series_data(
            days=30,
            username="testuser"
        )

        assert "labels" in time_series
        assert "data" in time_series
        assert time_series["period_days"] == 30
        assert len(time_series["labels"]) == 31  # 30 days + today
        assert len(time_series["data"]) == 31
        assert sum(time_series["data"]) == 4  # Total documents

    def test_get_cluster_distribution(self, analytics_service, sample_data):
        """Test cluster distribution calculation."""
        distribution = analytics_service.get_cluster_distribution(username="testuser")

        assert "labels" in distribution
        assert "data" in distribution
        assert len(distribution["labels"]) == 2
        assert len(distribution["data"]) == 2

        # Check cluster names and counts
        cluster_data = dict(zip(distribution["labels"], distribution["data"]))
        assert "Python Basics" in cluster_data
        assert "Web Development" in cluster_data
        assert cluster_data["Python Basics"] == 2
        assert cluster_data["Web Development"] == 2

    def test_get_skill_level_distribution(self, analytics_service, sample_data):
        """Test skill level distribution calculation."""
        distribution = analytics_service.get_skill_level_distribution(username="testuser")

        assert "labels" in distribution
        assert "data" in distribution

        skill_data = dict(zip(distribution["labels"], distribution["data"]))
        assert skill_data.get("beginner", 0) == 2
        assert skill_data.get("intermediate", 0) == 2

    def test_get_source_type_distribution(self, analytics_service, sample_data):
        """Test source type distribution calculation."""
        distribution = analytics_service.get_source_type_distribution(username="testuser")

        assert "labels" in distribution
        assert "data" in distribution

        source_data = dict(zip(distribution["labels"], distribution["data"]))
        assert source_data.get("text", 0) == 2
        assert source_data.get("url", 0) == 1
        assert source_data.get("file", 0) == 1

    def test_get_top_concepts(self, analytics_service, sample_data):
        """Test top concepts extraction."""
        top_concepts = analytics_service.get_top_concepts(
            limit=10,
            username="testuser"
        )

        assert len(top_concepts) > 0
        assert all("concept" in c and "count" in c for c in top_concepts)

        # Variables should appear twice
        variables_concept = next(
            (c for c in top_concepts if c["concept"] == "variables"),
            None
        )
        assert variables_concept is not None
        assert variables_concept["count"] == 2

    def test_get_recent_activity(self, analytics_service, sample_data):
        """Test recent activity retrieval."""
        activity = analytics_service.get_recent_activity(
            limit=10,
            username="testuser"
        )

        assert len(activity) == 4
        assert all("doc_id" in a for a in activity)
        assert all("source_type" in a for a in activity)
        assert all("created_at" in a for a in activity)

        # Should be sorted by most recent first
        assert activity[0]["doc_id"] == 1

    def test_get_complete_analytics(self, analytics_service, sample_data):
        """Test complete analytics retrieval."""
        analytics = analytics_service.get_complete_analytics(
            username="testuser",
            time_period_days=30
        )

        assert "overview" in analytics
        assert "time_series" in analytics
        assert "cluster_distribution" in analytics
        assert "skill_level_distribution" in analytics
        assert "source_type_distribution" in analytics
        assert "top_concepts" in analytics
        assert "recent_activity" in analytics

        # Verify overview stats
        assert analytics["overview"]["total_documents"] == 4
        assert analytics["overview"]["total_clusters"] == 2

    def test_analytics_with_no_data(self, analytics_service, db_session):
        """Test analytics with empty database."""
        stats = analytics_service.get_overview_stats(username="nonexistent")

        assert stats["total_documents"] == 0
        assert stats["total_clusters"] == 2  # Clusters exist globally
        assert stats["total_concepts"] == 0

    def test_analytics_filtered_by_user(self, analytics_service, sample_data, db_session):
        """Test that analytics correctly filters by username."""
        # Add document for different user
        other_doc = DBDocument(
            doc_id=99,
            owner_username="otheruser",
            source_type="text",
            skill_level="beginner",
            cluster_id=1,
            created_at=datetime.utcnow()
        )
        db_session.add(other_doc)
        db_session.commit()

        # Stats should only include testuser's documents
        stats = analytics_service.get_overview_stats(username="testuser")
        assert stats["total_documents"] == 4  # Should not include otheruser's doc


class TestAnalyticsEndpoint:
    """Test analytics API endpoint."""

    def test_analytics_endpoint_requires_auth(self, client):
        """Test that analytics endpoint requires authentication."""
        response = client.get("/analytics")
        assert response.status_code == 401

    def test_analytics_endpoint_with_auth(self, client, auth_headers, sample_data):
        """Test analytics endpoint with valid authentication."""
        response = client.get("/analytics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "overview" in data
        assert "time_series" in data
        assert "cluster_distribution" in data
        assert "skill_level_distribution" in data
        assert "source_type_distribution" in data
        assert "top_concepts" in data
        assert "recent_activity" in data

    def test_analytics_endpoint_with_time_period(self, client, auth_headers, sample_data):
        """Test analytics endpoint with custom time period."""
        response = client.get("/analytics?time_period=7", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Time series should reflect 7-day period
        assert data["time_series"]["period_days"] == 7
        assert len(data["time_series"]["labels"]) == 8  # 7 days + today

    def test_analytics_endpoint_performance(self, client, auth_headers, sample_data):
        """Test analytics endpoint response time."""
        import time

        start = time.time()
        response = client.get("/analytics", headers=auth_headers)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 2.0  # Should respond within 2 seconds
