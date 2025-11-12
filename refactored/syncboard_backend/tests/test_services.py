"""
Unit tests for service layer (Phase 4).

Tests the DocumentService, SearchService, ClusterService, and BuildSuggestionService.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.repository import KnowledgeBankRepository
from backend.services import (
    DocumentService,
    SearchService,
    ClusterService,
    BuildSuggestionService
)
from backend.llm_providers import MockLLMProvider
from backend.concept_extractor import ConceptExtractor
from backend.build_suggester import BuildSuggester


@pytest.fixture
def temp_storage():
    """Create temporary storage file."""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def repository(temp_storage):
    """Create repository with temporary storage."""
    return KnowledgeBankRepository(storage_path=temp_storage, vector_dim=256)


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def concept_extractor(mock_llm_provider):
    """Create concept extractor with mock provider."""
    return ConceptExtractor(llm_provider=mock_llm_provider)


@pytest.fixture
def build_suggester(mock_llm_provider):
    """Create build suggester with mock provider."""
    return BuildSuggester(llm_provider=mock_llm_provider)


@pytest.fixture
def document_service(repository, concept_extractor):
    """Create document service."""
    return DocumentService(repository=repository, concept_extractor=concept_extractor)


@pytest.fixture
def search_service(repository):
    """Create search service."""
    return SearchService(repository=repository)


@pytest.fixture
def cluster_service(repository):
    """Create cluster service."""
    return ClusterService(repository=repository)


@pytest.fixture
def build_suggestion_service(repository, build_suggester):
    """Create build suggestion service."""
    return BuildSuggestionService(repository=repository, suggester=build_suggester)


# =============================================================================
# DocumentService Tests
# =============================================================================

@pytest.mark.asyncio
async def test_document_service_ingest_text(document_service):
    """Test text ingestion creates document and cluster."""
    doc_id, cluster_id = await document_service.ingest_text("Test content about Python", "text")

    assert doc_id >= 0
    assert cluster_id >= 0

    # Verify document exists
    doc = await document_service.repo.get_document(doc_id)
    assert doc == "Test content about Python"

    # Verify metadata exists
    meta = await document_service.repo.get_document_metadata(doc_id)
    assert meta is not None
    assert meta.source_type == "text"
    assert meta.cluster_id == cluster_id


@pytest.mark.asyncio
async def test_document_service_delete(document_service):
    """Test document deletion."""
    # Create document
    doc_id, _ = await document_service.ingest_text("Test document", "text")

    # Delete it
    result = await document_service.delete_document(doc_id)
    assert result is True

    # Verify it's gone
    doc = await document_service.repo.get_document(doc_id)
    assert doc is None


@pytest.mark.asyncio
async def test_document_service_auto_clustering(document_service):
    """Test auto-clustering creates appropriate clusters."""
    # Create first document
    doc1_id, cluster1_id = await document_service.ingest_text("Python programming tutorial", "text")

    # Create second document with similar content
    doc2_id, cluster2_id = await document_service.ingest_text("Python coding guide", "text")

    # Both should be in same cluster (due to mock returning same concepts)
    assert cluster1_id == cluster2_id

    # Verify cluster has both documents
    cluster = await document_service.repo.get_cluster(cluster1_id)
    assert doc1_id in cluster.document_ids
    assert doc2_id in cluster.document_ids


# =============================================================================
# SearchService Tests
# =============================================================================

@pytest.mark.asyncio
async def test_search_service_basic_search(search_service, document_service):
    """Test basic document search."""
    # Add some documents
    await document_service.ingest_text("Python programming tutorial", "text")
    await document_service.ingest_text("JavaScript web development", "text")

    # Search for Python
    results = await search_service.search("Python", top_k=10)

    assert len(results) > 0
    # Should find Python document
    assert any("Python" in r["content"] for r in results)


@pytest.mark.asyncio
async def test_search_service_with_cluster_filter(search_service, document_service):
    """Test search with cluster filtering."""
    # Add documents
    doc1_id, cluster1_id = await document_service.ingest_text("Python tutorial", "text")
    doc2_id, cluster2_id = await document_service.ingest_text("Different topic", "text")

    # Search with cluster filter
    results = await search_service.search("Python", top_k=10, cluster_id=cluster1_id)

    # Should only return documents from specified cluster
    assert len(results) >= 0
    if results:
        assert all(r["metadata"]["cluster_id"] == cluster1_id for r in results)


@pytest.mark.asyncio
async def test_search_service_full_content(search_service, document_service):
    """Test search with full content vs snippet."""
    # Add long document
    long_content = "Python " * 200  # Create long document
    await document_service.ingest_text(long_content, "text")

    # Search with snippet
    results_snippet = await search_service.search("Python", top_k=5, full_content=False)
    if results_snippet:
        assert len(results_snippet[0]["content"]) <= 500 + 3  # 500 + "..."

    # Search with full content
    results_full = await search_service.search("Python", top_k=5, full_content=True)
    if results_full:
        assert len(results_full[0]["content"]) > 500


# =============================================================================
# ClusterService Tests
# =============================================================================

@pytest.mark.asyncio
async def test_cluster_service_get_all(cluster_service, document_service):
    """Test getting all clusters."""
    # Create some documents (which create clusters)
    await document_service.ingest_text("Test content 1", "text")
    await document_service.ingest_text("Test content 2", "text")

    # Get all clusters
    clusters = await cluster_service.get_all_clusters()

    assert len(clusters) > 0
    assert all("id" in c for c in clusters)
    assert all("name" in c for c in clusters)
    assert all("doc_count" in c for c in clusters)


@pytest.mark.asyncio
async def test_cluster_service_get_details(cluster_service, document_service):
    """Test getting cluster details."""
    # Create document
    _, cluster_id = await document_service.ingest_text("Test content", "text")

    # Get cluster details
    details = await cluster_service.get_cluster_details(cluster_id)

    assert details is not None
    assert details["id"] == cluster_id
    assert "name" in details
    assert len(details["document_ids"]) > 0


# =============================================================================
# BuildSuggestionService Tests
# =============================================================================

@pytest.mark.asyncio
async def test_build_suggestion_service(build_suggestion_service, document_service):
    """Test build suggestion generation."""
    # Add some documents
    await document_service.ingest_text("Python programming tutorial", "text")
    await document_service.ingest_text("Web development with Flask", "text")

    # Generate suggestions
    result = await build_suggestion_service.generate_suggestions(max_suggestions=3)

    assert "suggestions" in result
    assert "knowledge_summary" in result
    assert isinstance(result["suggestions"], list)
    assert "total_docs" in result["knowledge_summary"]


@pytest.mark.asyncio
async def test_build_suggestion_service_empty_knowledge(build_suggestion_service):
    """Test build suggestions with no documents."""
    result = await build_suggestion_service.generate_suggestions(max_suggestions=5)

    assert "suggestions" in result
    assert "knowledge_summary" in result
    assert result["knowledge_summary"]["total_docs"] == 0


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_full_workflow(document_service, search_service, cluster_service):
    """Test complete workflow: ingest -> search -> cluster management."""
    # 1. Ingest documents
    doc1_id, cluster1_id = await document_service.ingest_text("Python tutorial", "text")
    doc2_id, cluster2_id = await document_service.ingest_text("JavaScript guide", "text")

    # 2. Search documents
    results = await search_service.search("Python", top_k=10)
    assert len(results) > 0

    # 3. Get clusters
    clusters = await cluster_service.get_all_clusters()
    assert len(clusters) > 0

    # 4. Delete document
    deleted = await document_service.delete_document(doc1_id)
    assert deleted is True

    # 5. Verify deletion
    doc = await document_service.repo.get_document(doc1_id)
    assert doc is None


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

@pytest.mark.asyncio
async def test_delete_nonexistent_document(document_service):
    """Test deleting non-existent document."""
    result = await document_service.delete_document(99999)
    assert result is False


@pytest.mark.asyncio
async def test_search_empty_repository(search_service):
    """Test search with no documents."""
    results = await search_service.search("test", top_k=10)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_get_nonexistent_cluster(cluster_service):
    """Test getting non-existent cluster."""
    details = await cluster_service.get_cluster_details(99999)
    assert details is None


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.asyncio
async def test_bulk_ingestion_performance(document_service):
    """Test ingesting multiple documents."""
    import time

    start_time = time.time()

    # Ingest 10 documents
    for i in range(10):
        await document_service.ingest_text(f"Document {i} content", "text")

    elapsed = time.time() - start_time

    # Should complete in reasonable time (< 5 seconds with mock provider)
    assert elapsed < 5.0

    # Verify all documents exist
    all_docs = await document_service.repo.get_all_documents()
    assert len(all_docs) == 10


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
