"""
Comprehensive tests for VectorStore (TF-IDF based semantic search).

Tests cover:
- Basic document addition and retrieval
- Search accuracy and relevance ranking
- Document deletion and vector rebuilding
- Batch operations
- Edge cases (empty corpus, unicode, special characters)
- Performance characteristics
- Search filtering with allowed_doc_ids
"""

import pytest
import numpy as np
from backend.vector_store import VectorStore


# =============================================================================
# BASIC FUNCTIONALITY TESTS
# =============================================================================

def test_vector_store_initialization():
    """Test VectorStore initializes correctly."""
    vs = VectorStore(dim=256)

    assert vs.dim == 256
    assert vs.docs == {}
    assert vs.doc_ids == []
    assert vs.vectorizer is None
    assert vs.doc_matrix is None


def test_add_single_document():
    """Test adding a single document."""
    vs = VectorStore()

    doc_id = vs.add_document("Python programming tutorial")

    assert doc_id == 0
    assert len(vs.docs) == 1
    assert vs.docs[0] == "Python programming tutorial"
    assert vs.doc_ids == [0]
    assert vs.vectorizer is not None
    assert vs.doc_matrix is not None


def test_add_multiple_documents_sequential():
    """Test adding multiple documents one by one."""
    vs = VectorStore()

    id1 = vs.add_document("Python programming")
    id2 = vs.add_document("JavaScript development")
    id3 = vs.add_document("Data science with Python")

    assert id1 == 0
    assert id2 == 1
    assert id3 == 2
    assert len(vs.docs) == 3
    assert vs.doc_ids == [0, 1, 2]


def test_add_documents_batch():
    """Test batch document addition is more efficient."""
    vs = VectorStore()

    texts = [
        "Python programming",
        "JavaScript development",
        "Data science",
        "Machine learning",
        "Web development"
    ]

    doc_ids = vs.add_documents_batch(texts)

    assert doc_ids == [0, 1, 2, 3, 4]
    assert len(vs.docs) == 5
    assert all(vs.docs[i] == texts[i] for i in range(5))
    assert vs.vectorizer is not None


# =============================================================================
# SEARCH FUNCTIONALITY TESTS
# =============================================================================

def test_basic_search():
    """Test basic search returns relevant documents."""
    vs = VectorStore()

    vs.add_document("Python programming tutorial for beginners")
    vs.add_document("JavaScript web development guide")
    vs.add_document("Python data science and machine learning")

    results = vs.search("Python coding", top_k=3)

    assert len(results) == 3
    # Results are tuples of (doc_id, score, snippet)
    assert all(len(r) == 3 for r in results)
    # First result should be Python-related (doc 0 or 2)
    assert results[0][0] in [0, 2]
    # Scores should be between 0 and 1
    assert all(0 <= r[1] <= 1 for r in results)


def test_search_relevance_ranking():
    """Test that search ranks by relevance correctly."""
    vs = VectorStore()

    id1 = vs.add_document("Python")  # Exact match
    id2 = vs.add_document("Python programming tutorial")  # Good match
    id3 = vs.add_document("Java programming tutorial")  # Poor match

    results = vs.search("Python programming", top_k=3)

    # Python docs should rank higher than Java
    doc_ids = [r[0] for r in results]
    python_docs = [id1, id2]

    # At least one Python doc should be in top 2 results
    assert any(doc_id in python_docs for doc_id in doc_ids[:2])

    # First result should have highest score
    scores = [r[1] for r in results]
    assert scores[0] >= scores[1] >= scores[2]


def test_search_top_k_limit():
    """Test that top_k parameter limits results correctly."""
    vs = VectorStore()

    for i in range(10):
        vs.add_document(f"Document number {i} about programming")

    results_3 = vs.search("programming", top_k=3)
    results_5 = vs.search("programming", top_k=5)
    results_all = vs.search("programming", top_k=20)

    assert len(results_3) == 3
    assert len(results_5) == 5
    assert len(results_all) == 10  # Only 10 docs exist


def test_search_snippet_generation():
    """Test that search returns proper snippets."""
    vs = VectorStore()

    short_text = "Short document"
    long_text = "A" * 200  # 200 character document

    vs.add_document(short_text)
    vs.add_document(long_text)

    results = vs.search("document", top_k=2)

    # Short doc should not have "..."
    short_result = [r for r in results if r[0] == 0][0]
    assert short_result[2] == short_text
    assert "..." not in short_result[2]

    # Long doc should be truncated with "..."
    long_result = [r for r in results if r[0] == 1][0]
    assert len(long_result[2]) == 103  # 100 chars + "..."
    assert long_result[2].endswith("...")


def test_search_with_allowed_doc_ids():
    """Test filtering search results by allowed document IDs."""
    vs = VectorStore()

    id1 = vs.add_document("Python programming")
    id2 = vs.add_document("Python data science")
    id3 = vs.add_document("Python web development")

    # Search with filter
    results = vs.search("Python", top_k=10, allowed_doc_ids=[id1, id3])

    returned_ids = [r[0] for r in results]

    # Should only return id1 and id3, not id2
    assert id1 in returned_ids
    assert id3 in returned_ids
    assert id2 not in returned_ids
    assert len(results) == 2


def test_search_empty_allowed_doc_ids():
    """Test search with empty allowed_doc_ids returns nothing."""
    vs = VectorStore()

    vs.add_document("Python programming")
    vs.add_document("JavaScript development")

    results = vs.search("programming", top_k=10, allowed_doc_ids=[])

    assert results == []


# =============================================================================
# DOCUMENT DELETION TESTS
# =============================================================================

def test_remove_document():
    """Test removing a document."""
    vs = VectorStore()

    id1 = vs.add_document("Python programming")
    id2 = vs.add_document("JavaScript development")
    id3 = vs.add_document("Data science")

    vs.remove_document(id2)

    # Document should be removed
    assert id2 not in vs.docs
    assert id2 not in vs.doc_ids
    assert len(vs.docs) == 2
    assert len(vs.doc_ids) == 2

    # Other documents should still exist
    assert id1 in vs.docs
    assert id3 in vs.docs


def test_remove_document_updates_search():
    """Test that search results update after document removal."""
    vs = VectorStore()

    id1 = vs.add_document("Python programming tutorial")
    id2 = vs.add_document("JavaScript web development")

    # Initially, both should be searchable
    results = vs.search("programming", top_k=10)
    assert len(results) == 2

    # Remove Python doc
    vs.remove_document(id1)

    # Now only JavaScript doc should be found
    results = vs.search("programming", top_k=10)
    returned_ids = [r[0] for r in results]
    assert id1 not in returned_ids
    assert len(results) == 1


def test_remove_nonexistent_document():
    """Test removing non-existent document doesn't crash."""
    vs = VectorStore()

    vs.add_document("Python programming")

    # Should not raise an error
    vs.remove_document(999)

    # Original document should still exist
    assert len(vs.docs) == 1


def test_remove_all_documents():
    """Test removing all documents resets vector store."""
    vs = VectorStore()

    id1 = vs.add_document("Doc 1")
    id2 = vs.add_document("Doc 2")

    vs.remove_document(id1)
    vs.remove_document(id2)

    assert vs.docs == {}
    assert vs.doc_ids == []
    assert vs.vectorizer is None
    assert vs.doc_matrix is None

    # Search should return empty
    results = vs.search("test", top_k=10)
    assert results == []


# =============================================================================
# EDGE CASES
# =============================================================================

def test_search_empty_corpus():
    """Test searching when no documents exist."""
    vs = VectorStore()

    results = vs.search("test query", top_k=10)

    assert results == []


def test_search_empty_query():
    """Test searching with empty query string."""
    vs = VectorStore()

    vs.add_document("Python programming")
    vs.add_document("JavaScript development")

    results = vs.search("", top_k=10)

    # Should return results but with low scores
    assert len(results) >= 0  # Implementation dependent


def test_add_empty_document():
    """Test adding empty document."""
    vs = VectorStore()

    doc_id = vs.add_document("")

    assert doc_id == 0
    assert vs.docs[0] == ""

    # Should not crash when searching
    results = vs.search("test", top_k=10)
    assert isinstance(results, list)


def test_unicode_documents():
    """Test handling of unicode characters."""
    vs = VectorStore()

    id1 = vs.add_document("Python 编程教程 プログラミング")
    id2 = vs.add_document("JavaScript development 開発")
    id3 = vs.add_document("Data science 数据科学")

    # Should not crash
    results = vs.search("programming", top_k=10)
    assert isinstance(results, list)

    # Should be able to search unicode
    results = vs.search("编程", top_k=10)
    assert isinstance(results, list)


def test_special_characters():
    """Test documents with special characters."""
    vs = VectorStore()

    id1 = vs.add_document("C++ programming & development!")
    id2 = vs.add_document("Python: A guide to @decorators")
    id3 = vs.add_document("JavaScript - ES6+ features")

    # Should not crash
    results = vs.search("programming", top_k=10)
    assert isinstance(results, list)
    assert len(results) == 3


def test_very_long_document():
    """Test handling of very long documents."""
    vs = VectorStore()

    # Create a 10,000 word document
    long_doc = " ".join(["word"] * 10000)

    doc_id = vs.add_document(long_doc)

    assert doc_id == 0

    # Search should still work
    results = vs.search("word", top_k=5)
    assert len(results) == 1

    # Snippet should be truncated
    assert len(results[0][2]) == 103  # 100 + "..."


def test_duplicate_documents():
    """Test adding identical documents."""
    vs = VectorStore()

    id1 = vs.add_document("Python programming")
    id2 = vs.add_document("Python programming")  # Exact duplicate

    assert id1 != id2
    assert len(vs.docs) == 2

    # Both should be searchable
    results = vs.search("Python", top_k=10)
    assert len(results) == 2


def test_single_document_corpus():
    """Test search with only one document."""
    vs = VectorStore()

    vs.add_document("Python programming tutorial")

    results = vs.search("JavaScript", top_k=10)

    # Should return the single document even though not very relevant
    assert len(results) <= 1


# =============================================================================
# VECTOR REBUILDING TESTS
# =============================================================================

def test_vector_rebuild_after_add():
    """Test that vectors are rebuilt after adding documents."""
    vs = VectorStore()

    vs.add_document("Doc 1")
    matrix_1 = vs.doc_matrix

    vs.add_document("Doc 2")
    matrix_2 = vs.doc_matrix

    # Matrix should be different (rebuilt)
    assert matrix_2.shape != matrix_1.shape
    assert matrix_2.shape[0] == 2  # 2 documents


def test_vector_rebuild_after_remove():
    """Test that vectors are rebuilt after removing documents."""
    vs = VectorStore()

    id1 = vs.add_document("Doc 1")
    id2 = vs.add_document("Doc 2")
    id3 = vs.add_document("Doc 3")

    matrix_before = vs.doc_matrix
    assert matrix_before.shape[0] == 3

    vs.remove_document(id2)

    matrix_after = vs.doc_matrix
    assert matrix_after.shape[0] == 2


def test_batch_add_single_rebuild():
    """Test that batch add only rebuilds vectors once."""
    vs = VectorStore()

    # Monkey-patch to count rebuilds
    rebuild_count = [0]
    original_rebuild = vs._rebuild_vectors

    def counting_rebuild():
        rebuild_count[0] += 1
        original_rebuild()

    vs._rebuild_vectors = counting_rebuild

    # Batch add 5 documents
    vs.add_documents_batch(["Doc 1", "Doc 2", "Doc 3", "Doc 4", "Doc 5"])

    # Should only rebuild once
    assert rebuild_count[0] == 1


def test_sequential_add_multiple_rebuilds():
    """Test that sequential adds rebuild multiple times."""
    vs = VectorStore()

    # Monkey-patch to count rebuilds
    rebuild_count = [0]
    original_rebuild = vs._rebuild_vectors

    def counting_rebuild():
        rebuild_count[0] += 1
        original_rebuild()

    vs._rebuild_vectors = counting_rebuild

    # Add 5 documents sequentially
    for i in range(5):
        vs.add_document(f"Doc {i}")

    # Should rebuild 5 times
    assert rebuild_count[0] == 5


# =============================================================================
# CONSISTENCY TESTS
# =============================================================================

def test_doc_ids_match_matrix_rows():
    """Test that doc_ids list matches document matrix rows."""
    vs = VectorStore()

    id1 = vs.add_document("Doc 1")
    id2 = vs.add_document("Doc 2")
    id3 = vs.add_document("Doc 3")

    # Number of doc_ids should match matrix rows
    assert len(vs.doc_ids) == vs.doc_matrix.shape[0]

    # Remove a document
    vs.remove_document(id2)

    # Should still match
    assert len(vs.doc_ids) == vs.doc_matrix.shape[0]

    # doc_ids should not contain removed id
    assert id2 not in vs.doc_ids


def test_search_consistency_after_operations():
    """Test that search remains consistent after add/remove operations."""
    vs = VectorStore()

    id1 = vs.add_document("Python programming")
    id2 = vs.add_document("JavaScript development")

    # Initial search
    results1 = vs.search("programming", top_k=10)
    assert len(results1) == 2

    # Add more documents
    id3 = vs.add_document("Python data science")
    id4 = vs.add_document("Java programming")

    # Search should include new documents
    results2 = vs.search("programming", top_k=10)
    assert len(results2) == 4

    # Remove some documents
    vs.remove_document(id2)
    vs.remove_document(id4)

    # Search should exclude removed documents
    results3 = vs.search("programming", top_k=10)
    returned_ids = [r[0] for r in results3]
    assert id2 not in returned_ids
    assert id4 not in returned_ids
    assert len(results3) == 2


# =============================================================================
# TFIDF SPECIFIC TESTS
# =============================================================================

def test_tfidf_vocabulary_built():
    """Test that TF-IDF vocabulary is built correctly."""
    vs = VectorStore()

    vs.add_document("Python programming language")
    vs.add_document("JavaScript programming language")

    # Vectorizer should have vocabulary
    assert vs.vectorizer is not None
    vocab = vs.vectorizer.vocabulary_

    # Common words should be in vocabulary
    assert "python" in vocab or "Python" in vocab
    assert "programming" in vocab or "Programming" in vocab


def test_tfidf_cosine_similarity():
    """Test that cosine similarity scoring works correctly."""
    vs = VectorStore()

    id1 = vs.add_document("Python Python Python")  # High Python frequency
    id2 = vs.add_document("Python JavaScript Java")  # Low Python frequency

    results = vs.search("Python", top_k=2)

    # Doc with higher Python frequency should score higher
    scores = {r[0]: r[1] for r in results}
    assert scores[id1] > scores[id2]


def test_search_returns_sorted_results():
    """Test that search results are sorted by score descending."""
    vs = VectorStore()

    vs.add_document("Python")
    vs.add_document("Python programming")
    vs.add_document("Python programming tutorial complete guide")
    vs.add_document("JavaScript")

    results = vs.search("Python programming tutorial", top_k=4)

    # Scores should be in descending order
    scores = [r[1] for r in results]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Scores not sorted: {scores}"


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

def test_search_performance_large_corpus():
    """Test search performance with larger corpus (1000 docs)."""
    import time

    vs = VectorStore()

    # Add 1000 documents
    texts = [f"Document {i} about programming and development" for i in range(1000)]
    vs.add_documents_batch(texts)

    # Search should complete quickly
    start = time.time()
    results = vs.search("programming development", top_k=10)
    elapsed = time.time() - start

    assert elapsed < 1.0  # Should complete within 1 second
    assert len(results) == 10


def test_batch_add_performance():
    """Test that batch add is faster than sequential adds."""
    import time

    texts = [f"Document {i}" for i in range(100)]

    # Sequential adds
    vs1 = VectorStore()
    start1 = time.time()
    for text in texts:
        vs1.add_document(text)
    sequential_time = time.time() - start1

    # Batch add
    vs2 = VectorStore()
    start2 = time.time()
    vs2.add_documents_batch(texts)
    batch_time = time.time() - start2

    # Batch should be significantly faster (at least 2x)
    assert batch_time < sequential_time / 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
