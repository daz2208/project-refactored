"""
High‑level vector store for embedding and similarity search.

This implementation uses scikit‑learn’s TF‑IDF vectoriser to produce
semantic vectors for documents and queries.  Unlike the earlier
hash‑based implementation, TF‑IDF captures term frequency and inverse
document frequency, providing improved relevance without requiring
external language models.  When new documents are added the
internal vectors are rebuilt, which is acceptable for small to
medium‑sized datasets typical of a personal or team knowledge base.

If scikit‑learn is unavailable, you can fall back to the original
hash‑based embeddings by importing and using the previous version of
this module.
"""

from typing import Dict, List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class VectorStore:
    """In‑memory semantic vector store using TF‑IDF.

    Documents are stored in insertion order.  On each addition the
    TF‑IDF vocabulary and document matrix are rebuilt.  This keeps
    search results consistent with the current corpus at the cost of
    slightly higher insertion overhead.  For datasets larger than a
    few thousand documents you may wish to swap this out for a
    streaming or database‑backed vector index.
    """

    def __init__(self, dim: int = 256) -> None:
        # ``dim`` is accepted for API compatibility but unused because
        # TF‑IDF determines the dimensionality automatically.
        self.dim = dim
        # Mapping of document ID to text
        self.docs: Dict[int, str] = {}
        # List of document IDs in insertion order, paralleling rows of
        # ``doc_matrix``
        self.doc_ids: List[int] = []
        # TF‑IDF vectoriser and document matrix; initialised on first
        # insertion
        self.vectorizer: TfidfVectorizer | None = None
        self.doc_matrix = None  # type: ignore

    def _rebuild_vectors(self) -> None:
        """(Re)fit the TF‑IDF vectoriser and document matrix.

        Called whenever documents are added or removed.  Uses the
        current list of texts to build the vocabulary.
        """
        texts = [self.docs[doc_id] for doc_id in self.doc_ids]
        if not texts:
            self.vectorizer = None
            self.doc_matrix = None
            return
        self.vectorizer = TfidfVectorizer()
        self.doc_matrix = self.vectorizer.fit_transform(texts)

    def add_document(self, text: str) -> int:
        """Add a document to the vector store and rebuild vectors.

        Args:
            text: Document text.

        Returns:
            Assigned document ID.
        """
        doc_id = len(self.docs)
        self.docs[doc_id] = text
        self.doc_ids.append(doc_id)
        # Rebuild vectoriser and document matrix
        self._rebuild_vectors()
        return doc_id

    def remove_document(self, doc_id: int) -> None:
        """Remove a document from the store and rebuild vectors.

        Args:
            doc_id: ID of the document to remove.

        Notes:
            If the given document ID does not exist, this method
            silently ignores the call.  After removal the TF‑IDF
            vocabulary and document matrix are rebuilt to reflect the
            remaining documents.
        """
        if doc_id not in self.docs:
            return
        # Remove from mapping and order list
        del self.docs[doc_id]
        self.doc_ids = [d for d in self.doc_ids if d != doc_id]
        # Rebuild vectors from remaining docs
        self._rebuild_vectors()

    def search(self, query: str, top_k: int = 5, allowed_doc_ids: List[int] | None = None) -> List[Tuple[int, float, str]]:
        """Return documents semantically similar to the query.

        Args:
            query: User query text.
            top_k: Number of results to return.
            allowed_doc_ids: Optional list of document IDs to restrict
                search to (e.g., documents belonging to a particular
                board).

        Returns:
            A list of tuples ``(document_id, similarity_score, snippet)``
            sorted by descending similarity.
        """
        if self.vectorizer is None or self.doc_matrix is None:
            return []
        # Transform query using existing vocabulary
        q_vec = self.vectorizer.transform([query])
        # Compute cosine similarities between query and all documents
        scores = cosine_similarity(self.doc_matrix, q_vec).flatten()
        # Build list of candidate (index, score) pairs
        candidates: List[Tuple[int, float]] = []
        for idx, score in enumerate(scores):
            # Map row index to document ID
            doc_id = self.doc_ids[idx]
            if allowed_doc_ids is not None and doc_id not in allowed_doc_ids:
                continue
            candidates.append((idx, float(score)))
        # Sort candidates by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        results: List[Tuple[int, float, str]] = []
        for row_idx, score in candidates[:top_k]:
            doc_id = self.doc_ids[row_idx]
            text = self.docs[doc_id]
            snippet = text[:100] + ("..." if len(text) > 100 else "")
            results.append((doc_id, score, snippet))
        return results