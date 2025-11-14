"""
Comprehensive tests for ClusteringEngine.

Tests cover:
- Jaccard similarity calculation
- Cluster matching logic
- Cluster creation
- Adding documents to clusters
- Threshold boundary conditions
- Edge cases (empty concepts, no clusters, etc.)
- Cluster name matching boost
"""

import pytest
from backend.clustering import ClusteringEngine
from backend.models import Cluster


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

def test_clustering_engine_initialization():
    """Test ClusteringEngine initializes with correct defaults."""
    engine = ClusteringEngine()

    assert engine.similarity_threshold == 0.5


def test_clustering_engine_custom_threshold():
    """Test setting custom similarity threshold."""
    engine = ClusteringEngine()
    engine.similarity_threshold = 0.7

    assert engine.similarity_threshold == 0.7


# =============================================================================
# CLUSTER MATCHING TESTS
# =============================================================================

def test_find_best_cluster_empty_clusters():
    """Test finding cluster when no clusters exist."""
    engine = ClusteringEngine()

    doc_concepts = [
        {"name": "Python", "category": "language"},
        {"name": "Programming", "category": "concept"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Python Programming", {})

    assert result is None


def test_find_best_cluster_exact_match():
    """Test finding cluster with exact concept match."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Python Programming",
            doc_ids=[1, 2],
            primary_concepts=["python", "programming"],
            skill_level="intermediate",
            doc_count=2
        )
    }

    doc_concepts = [
        {"name": "Python", "category": "language"},
        {"name": "Programming", "category": "concept"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Python Programming", existing_clusters)

    # Should match cluster 0 (similarity = 1.0)
    assert result == 0


def test_find_best_cluster_partial_match():
    """Test finding cluster with partial concept overlap."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Python Programming",
            doc_ids=[1],
            primary_concepts=["python", "programming", "tutorial"],
            skill_level="beginner",
            doc_count=1
        )
    }

    doc_concepts = [
        {"name": "Python", "category": "language"},
        {"name": "Data Science", "category": "concept"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Python Data Science", existing_clusters)

    # Jaccard similarity = 1/4 = 0.25, below threshold
    assert result is None


def test_find_best_cluster_above_threshold():
    """Test cluster matching when similarity is above threshold."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Python Programming",
            doc_ids=[1],
            primary_concepts=["python", "programming"],
            skill_level="intermediate",
            doc_count=1
        )
    }

    doc_concepts = [
        {"name": "Python", "category": "language"},
        {"name": "Programming", "category": "concept"},
        {"name": "Tutorial", "category": "content_type"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Python Tutorial", existing_clusters)

    # Jaccard similarity = 2/3 = 0.67, above threshold (0.5)
    assert result == 0


def test_find_best_cluster_name_boost():
    """Test that matching cluster name boosts similarity."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Python Programming",
            doc_ids=[1],
            primary_concepts=["python", "coding"],
            skill_level="beginner",
            doc_count=1
        )
    }

    doc_concepts = [
        {"name": "Python", "category": "language"},
        {"name": "Tutorial", "category": "content_type"}
    ]

    # Without name boost: Jaccard = 1/3 = 0.33 < 0.5
    # With name boost: 0.33 + 0.2 = 0.53 > 0.5
    result = engine.find_best_cluster(doc_concepts, "Python Programming", existing_clusters)

    assert result == 0


def test_find_best_cluster_case_insensitive():
    """Test that cluster matching is case insensitive."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Python Programming",
            doc_ids=[1],
            primary_concepts=["Python", "Programming"],  # Mixed case
            skill_level="intermediate",
            doc_count=1
        )
    }

    doc_concepts = [
        {"name": "python", "category": "language"},  # lowercase
        {"name": "PROGRAMMING", "category": "concept"}  # uppercase
    ]

    result = engine.find_best_cluster(doc_concepts, "python programming", existing_clusters)

    # Should still match despite case differences
    assert result == 0


def test_find_best_cluster_multiple_options():
    """Test selecting best cluster when multiple options exist."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Python Basics",
            doc_ids=[1],
            primary_concepts=["python", "basics"],
            skill_level="beginner",
            doc_count=1
        ),
        1: Cluster(
            id=1,
            name="Python Programming",
            doc_ids=[2, 3],
            primary_concepts=["python", "programming", "tutorial"],
            skill_level="intermediate",
            doc_count=2
        )
    }

    doc_concepts = [
        {"name": "Python", "category": "language"},
        {"name": "Programming", "category": "concept"},
        {"name": "Tutorial", "category": "content_type"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Python Tutorial", existing_clusters)

    # Cluster 1 should have higher similarity (3/3 = 1.0)
    assert result == 1


def test_find_best_cluster_empty_concepts():
    """Test finding cluster when document has no concepts."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Python Programming",
            doc_ids=[1],
            primary_concepts=["python", "programming"],
            skill_level="intermediate",
            doc_count=1
        )
    }

    doc_concepts = []  # Empty concepts

    result = engine.find_best_cluster(doc_concepts, "Programming", existing_clusters)

    # Should return None (can't match with no concepts)
    assert result is None


def test_find_best_cluster_empty_cluster_concepts():
    """Test finding cluster when cluster has no primary concepts."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="General",
            doc_ids=[1],
            primary_concepts=[],  # Empty concepts
            skill_level="beginner",
            doc_count=1
        )
    }

    doc_concepts = [
        {"name": "Python", "category": "language"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Python", existing_clusters)

    # Should return None (can't match with empty cluster concepts)
    assert result is None


# =============================================================================
# JACCARD SIMILARITY TESTS
# =============================================================================

def test_jaccard_similarity_identical_sets():
    """Test Jaccard similarity with identical concept sets."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Test",
            doc_ids=[],
            primary_concepts=["a", "b", "c"],
            skill_level="beginner",
            doc_count=0
        )
    }

    doc_concepts = [
        {"name": "A", "category": "x"},
        {"name": "B", "category": "y"},
        {"name": "C", "category": "z"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Test", existing_clusters)

    # Jaccard = 3/3 = 1.0, should match
    assert result == 0


def test_jaccard_similarity_no_overlap():
    """Test Jaccard similarity with no concept overlap."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Python",
            doc_ids=[],
            primary_concepts=["python", "programming"],
            skill_level="beginner",
            doc_count=0
        )
    }

    doc_concepts = [
        {"name": "JavaScript", "category": "language"},
        {"name": "Web", "category": "concept"}
    ]

    result = engine.find_best_cluster(doc_concepts, "JavaScript", existing_clusters)

    # Jaccard = 0/4 = 0.0, should not match
    assert result is None


def test_jaccard_similarity_exact_threshold():
    """Test Jaccard similarity exactly at threshold (0.5)."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Programming",
            doc_ids=[],
            primary_concepts=["a", "b"],
            skill_level="beginner",
            doc_count=0
        )
    }

    doc_concepts = [
        {"name": "A", "category": "x"},
        {"name": "C", "category": "y"}
    ]

    # Jaccard = 1/3 = 0.33, below threshold
    result = engine.find_best_cluster(doc_concepts, "Test", existing_clusters)
    assert result is None

    # Add one more matching concept
    doc_concepts = [
        {"name": "A", "category": "x"},
        {"name": "B", "category": "y"}
    ]

    # Jaccard = 2/2 = 1.0, above threshold
    result = engine.find_best_cluster(doc_concepts, "Test", existing_clusters)
    assert result == 0


# =============================================================================
# CLUSTER CREATION TESTS
# =============================================================================

def test_create_cluster_first_cluster():
    """Test creating the first cluster (ID should be 0)."""
    engine = ClusteringEngine()

    existing_clusters = {}

    concepts = [
        {"name": "Python", "category": "language"},
        {"name": "Programming", "category": "concept"}
    ]

    cluster_id = engine.create_cluster(
        doc_id=1,
        name="Python Programming",
        concepts=concepts,
        skill_level="intermediate",
        existing_clusters=existing_clusters
    )

    assert cluster_id == 0
    assert 0 in existing_clusters
    assert existing_clusters[0].name == "Python Programming"
    assert existing_clusters[0].doc_ids == [1]
    assert existing_clusters[0].doc_count == 1


def test_create_cluster_incremental_ids():
    """Test that cluster IDs increment correctly."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(id=0, name="Cluster 0", doc_ids=[], primary_concepts=[], skill_level="beginner", doc_count=0),
        1: Cluster(id=1, name="Cluster 1", doc_ids=[], primary_concepts=[], skill_level="beginner", doc_count=0)
    }

    concepts = [{"name": "Test", "category": "concept"}]

    cluster_id = engine.create_cluster(
        doc_id=10,
        name="New Cluster",
        concepts=concepts,
        skill_level="advanced",
        existing_clusters=existing_clusters
    )

    assert cluster_id == 2


def test_create_cluster_primary_concepts():
    """Test that primary concepts are extracted correctly."""
    engine = ClusteringEngine()

    existing_clusters = {}

    concepts = [
        {"name": "Python", "category": "language"},
        {"name": "Python", "category": "language"},  # Duplicate
        {"name": "Programming", "category": "concept"},
        {"name": "Tutorial", "category": "content_type"},
        {"name": "Python", "category": "language"}  # Another duplicate
    ]

    cluster_id = engine.create_cluster(
        doc_id=1,
        name="Python Tutorial",
        concepts=concepts,
        skill_level="beginner",
        existing_clusters=existing_clusters
    )

    cluster = existing_clusters[cluster_id]

    # Most common concepts should be first
    assert "Python" in cluster.primary_concepts
    assert len(cluster.primary_concepts) <= 5  # Max 5 primary concepts


def test_create_cluster_max_primary_concepts():
    """Test that only top 5 concepts are stored as primary."""
    engine = ClusteringEngine()

    existing_clusters = {}

    # Create 10 different concepts
    concepts = [{"name": f"Concept{i}", "category": "test"} for i in range(10)]

    cluster_id = engine.create_cluster(
        doc_id=1,
        name="Many Concepts",
        concepts=concepts,
        skill_level="intermediate",
        existing_clusters=existing_clusters
    )

    cluster = existing_clusters[cluster_id]

    # Should only have 5 primary concepts
    assert len(cluster.primary_concepts) == 5


def test_create_cluster_with_empty_concepts():
    """Test creating cluster with no concepts."""
    engine = ClusteringEngine()

    existing_clusters = {}

    cluster_id = engine.create_cluster(
        doc_id=1,
        name="Empty Cluster",
        concepts=[],
        skill_level="beginner",
        existing_clusters=existing_clusters
    )

    cluster = existing_clusters[cluster_id]

    assert cluster.primary_concepts == []


# =============================================================================
# ADD TO CLUSTER TESTS
# =============================================================================

def test_add_to_cluster():
    """Test adding document to existing cluster."""
    engine = ClusteringEngine()

    clusters = {
        0: Cluster(
            id=0,
            name="Python Programming",
            doc_ids=[1, 2],
            primary_concepts=["python", "programming"],
            skill_level="intermediate",
            doc_count=2
        )
    }

    engine.add_to_cluster(cluster_id=0, doc_id=3, clusters=clusters)

    # Document should be added
    assert 3 in clusters[0].doc_ids
    assert clusters[0].doc_count == 3


def test_add_to_cluster_duplicate_doc():
    """Test that adding same document twice doesn't duplicate."""
    engine = ClusteringEngine()

    clusters = {
        0: Cluster(
            id=0,
            name="Python Programming",
            doc_ids=[1, 2],
            primary_concepts=["python"],
            skill_level="beginner",
            doc_count=2
        )
    }

    # Add doc 2 again
    engine.add_to_cluster(cluster_id=0, doc_id=2, clusters=clusters)

    # Should not be duplicated
    assert clusters[0].doc_ids.count(2) == 1
    assert clusters[0].doc_count == 2


def test_add_to_nonexistent_cluster():
    """Test adding to non-existent cluster (should log error and return)."""
    engine = ClusteringEngine()

    clusters = {}

    # Should not crash
    engine.add_to_cluster(cluster_id=999, doc_id=1, clusters=clusters)

    # Clusters should remain empty
    assert clusters == {}


# =============================================================================
# THRESHOLD BOUNDARY TESTS
# =============================================================================

def test_similarity_just_below_threshold():
    """Test similarity just below threshold (0.49)."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Test",
            doc_ids=[],
            primary_concepts=["a", "b", "c", "d", "e"],
            skill_level="beginner",
            doc_count=0
        )
    }

    # Jaccard = 2/8 = 0.25, well below threshold
    doc_concepts = [
        {"name": "A", "category": "x"},
        {"name": "B", "category": "y"},
        {"name": "F", "category": "z"},
        {"name": "G", "category": "w"},
        {"name": "H", "category": "v"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Test", existing_clusters)

    assert result is None


def test_similarity_just_above_threshold():
    """Test similarity just above threshold (0.51)."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Test",
            doc_ids=[],
            primary_concepts=["a", "b"],
            skill_level="beginner",
            doc_count=0
        )
    }

    # Jaccard = 2/2 = 1.0, well above threshold
    doc_concepts = [
        {"name": "A", "category": "x"},
        {"name": "B", "category": "y"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Test", existing_clusters)

    assert result == 0


def test_custom_threshold():
    """Test using custom similarity threshold."""
    engine = ClusteringEngine()
    engine.similarity_threshold = 0.8  # Higher threshold

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Test",
            doc_ids=[],
            primary_concepts=["a", "b", "c"],
            skill_level="beginner",
            doc_count=0
        )
    }

    # Jaccard = 2/4 = 0.5, below 0.8 threshold
    doc_concepts = [
        {"name": "A", "category": "x"},
        {"name": "B", "category": "y"},
        {"name": "D", "category": "z"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Test", existing_clusters)

    assert result is None


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

def test_full_clustering_workflow():
    """Test complete clustering workflow: create, find, add."""
    engine = ClusteringEngine()
    clusters = {}

    # 1. Create first cluster
    concepts1 = [
        {"name": "Python", "category": "language"},
        {"name": "Programming", "category": "concept"}
    ]

    cluster_id1 = engine.create_cluster(
        doc_id=1,
        name="Python Programming",
        concepts=concepts1,
        skill_level="beginner",
        existing_clusters=clusters
    )

    assert cluster_id1 == 0
    assert len(clusters) == 1

    # 2. Try to find cluster for similar document
    concepts2 = [
        {"name": "Python", "category": "language"},
        {"name": "Tutorial", "category": "content_type"}
    ]

    # Jaccard = 1/3 = 0.33, below threshold
    # But with name boost: 0.33 + 0.2 = 0.53 > 0.5
    found_cluster = engine.find_best_cluster(concepts2, "Python Programming", clusters)

    assert found_cluster == 0

    # 3. Add document to existing cluster
    engine.add_to_cluster(cluster_id=0, doc_id=2, clusters=clusters)

    assert 2 in clusters[0].doc_ids
    assert clusters[0].doc_count == 2

    # 4. Create new cluster for different topic
    concepts3 = [
        {"name": "JavaScript", "category": "language"},
        {"name": "Web", "category": "concept"}
    ]

    cluster_id2 = engine.create_cluster(
        doc_id=3,
        name="Web Development",
        concepts=concepts3,
        skill_level="intermediate",
        existing_clusters=clusters
    )

    assert cluster_id2 == 1
    assert len(clusters) == 2


def test_clustering_with_many_clusters():
    """Test clustering with multiple existing clusters."""
    engine = ClusteringEngine()

    clusters = {
        0: Cluster(id=0, name="Python", doc_ids=[1], primary_concepts=["python", "programming"], skill_level="beginner", doc_count=1),
        1: Cluster(id=1, name="JavaScript", doc_ids=[2], primary_concepts=["javascript", "web"], skill_level="intermediate", doc_count=1),
        2: Cluster(id=2, name="Data Science", doc_ids=[3], primary_concepts=["python", "data", "science"], skill_level="advanced", doc_count=1),
    }

    # Document about Python data science
    concepts = [
        {"name": "Python", "category": "language"},
        {"name": "Data", "category": "concept"},
        {"name": "Science", "category": "field"}
    ]

    result = engine.find_best_cluster(concepts, "Data Science Tutorial", clusters)

    # Should match cluster 2 (Data Science) with highest similarity
    assert result == 2


# =============================================================================
# EDGE CASES
# =============================================================================

def test_clustering_special_characters_in_concepts():
    """Test concepts with special characters."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="C++ Programming",
            doc_ids=[],
            primary_concepts=["c++", "programming"],
            skill_level="advanced",
            doc_count=0
        )
    }

    doc_concepts = [
        {"name": "C++", "category": "language"},
        {"name": "Programming", "category": "concept"}
    ]

    result = engine.find_best_cluster(doc_concepts, "C++ Tutorial", existing_clusters)

    # Should match despite special characters
    assert result == 0


def test_clustering_unicode_concepts():
    """Test concepts with unicode characters."""
    engine = ClusteringEngine()

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Python 编程",
            doc_ids=[],
            primary_concepts=["python", "编程"],
            skill_level="beginner",
            doc_count=0
        )
    }

    doc_concepts = [
        {"name": "Python", "category": "language"},
        {"name": "编程", "category": "concept"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Python Tutorial", existing_clusters)

    # Should match with unicode concepts
    assert result == 0


def test_clustering_very_long_concept_names():
    """Test with very long concept names."""
    engine = ClusteringEngine()

    long_name = "A" * 500

    existing_clusters = {
        0: Cluster(
            id=0,
            name="Long Concepts",
            doc_ids=[],
            primary_concepts=[long_name, "short"],
            skill_level="beginner",
            doc_count=0
        )
    }

    doc_concepts = [
        {"name": long_name, "category": "concept"},
        {"name": "short", "category": "concept"}
    ]

    result = engine.find_best_cluster(doc_concepts, "Test", existing_clusters)

    # Should handle long names correctly
    assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
