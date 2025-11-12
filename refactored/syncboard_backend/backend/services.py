"""
Service layer for business logic.

Services encapsulate business operations and coordinate between
repository, extractors, and other components.
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .repository import KnowledgeBankRepository
from .concept_extractor import ConceptExtractor
from .build_suggester import BuildSuggester
from .models import DocumentMetadata, Concept, Cluster, BuildSuggestion

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document ingestion and management."""

    def __init__(
        self,
        repository: KnowledgeBankRepository,
        concept_extractor: ConceptExtractor
    ):
        """
        Initialize document service.

        Args:
            repository: Data repository
            concept_extractor: AI concept extraction service
        """
        self.repo = repository
        self.extractor = concept_extractor

    async def ingest_text(
        self,
        content: str,
        source_type: str = "text"
    ) -> Tuple[int, int]:
        """
        Ingest text content with automatic concept extraction and clustering.

        Args:
            content: Text content to ingest
            source_type: Type of source (text, url, pdf, etc.)

        Returns:
            Tuple of (document_id, cluster_id)
        """
        # Extract concepts using AI
        extraction = await self.extractor.extract(content, source_type)

        # Build metadata
        concepts = [
            Concept(name=c["name"], relevance=c["relevance"])
            for c in extraction.get("concepts", [])
        ]

        metadata = DocumentMetadata(
            source_type=source_type,
            concepts=concepts,
            skill_level=extraction.get("skill_level", "unknown"),
            primary_topic=extraction.get("primary_topic", "uncategorized"),
            ingested_at=datetime.utcnow().isoformat(),
            cluster_id=None  # Will be set by auto-clustering
        )

        # Save document
        doc_id = await self.repo.add_document(content, metadata)

        # Auto-cluster the document
        cluster_id = await self._auto_cluster_document(
            doc_id,
            metadata,
            extraction.get("suggested_cluster", "General")
        )

        # Update metadata with cluster ID
        metadata.cluster_id = cluster_id
        await self.repo.add_document_to_cluster(doc_id, cluster_id)

        logger.info(f"Ingested document {doc_id} → cluster {cluster_id}")
        return doc_id, cluster_id

    async def _auto_cluster_document(
        self,
        doc_id: int,
        metadata: DocumentMetadata,
        suggested_name: str
    ) -> int:
        """
        Automatically assign document to a cluster.

        Creates new cluster if no good match exists.

        Args:
            doc_id: Document ID
            metadata: Document metadata
            suggested_name: Suggested cluster name from AI

        Returns:
            Cluster ID
        """
        clusters = await self.repo.get_all_clusters()

        # Try to find matching cluster using Jaccard similarity
        best_cluster_id = None
        best_score = 0.0

        doc_concept_names = {c.name for c in metadata.concepts}

        for cluster in clusters.values():
            # Calculate Jaccard similarity
            cluster_concepts = set(cluster.primary_concepts)
            if not cluster_concepts:
                continue

            intersection = doc_concept_names & cluster_concepts
            union = doc_concept_names | cluster_concepts

            if union:
                score = len(intersection) / len(union)
                if score > best_score:
                    best_score = score
                    best_cluster_id = cluster.id

        # Use existing cluster if similarity > 0.3
        if best_cluster_id is not None and best_score > 0.3:
            logger.info(f"Matched to existing cluster {best_cluster_id} (score: {best_score:.2f})")
            return best_cluster_id

        # Create new cluster
        new_cluster = Cluster(
            id=0,  # Will be set by repository
            name=suggested_name,
            document_ids=[doc_id],
            primary_concepts=list(doc_concept_names)[:5],  # Top 5 concepts
            skill_level=metadata.skill_level
        )

        cluster_id = await self.repo.add_cluster(new_cluster)
        logger.info(f"Created new cluster {cluster_id}: {suggested_name}")
        return cluster_id

    async def delete_document(self, doc_id: int) -> bool:
        """
        Delete a document.

        Args:
            doc_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        return await self.repo.delete_document(doc_id)

    async def get_document_with_metadata(self, doc_id: int) -> Optional[Dict]:
        """
        Get document with its metadata.

        Args:
            doc_id: Document ID

        Returns:
            Dict with 'content' and 'metadata', or None if not found
        """
        content = await self.repo.get_document(doc_id)
        metadata = await self.repo.get_document_metadata(doc_id)

        if content is None or metadata is None:
            return None

        return {
            "content": content,
            "metadata": metadata
        }


class SearchService:
    """Service for searching the knowledge bank."""

    def __init__(self, repository: KnowledgeBankRepository):
        """
        Initialize search service.

        Args:
            repository: Data repository
        """
        self.repo = repository

    async def search(
        self,
        query: str,
        top_k: int = 5,
        cluster_id: Optional[int] = None,
        full_content: bool = False
    ) -> List[Dict]:
        """
        Search documents with optional filtering.

        Args:
            query: Search query
            top_k: Number of results
            cluster_id: Optional cluster filter
            full_content: Return full content or snippet

        Returns:
            List of search results with metadata
        """
        # Search vector store
        results = await self.repo.search_documents(query, top_k, cluster_id)

        # Enrich with metadata
        enriched_results = []
        all_metadata = await self.repo.get_all_metadata()
        all_documents = await self.repo.get_all_documents()
        all_clusters = await self.repo.get_all_clusters()

        for doc_id, score, snippet in results:
            metadata = all_metadata.get(doc_id)
            if not metadata:
                continue

            # Get content (full or snippet)
            if full_content:
                content = all_documents.get(doc_id, "")
            else:
                # Use 500 char snippet for performance
                doc_text = all_documents.get(doc_id, "")
                content = doc_text[:500] + ("..." if len(doc_text) > 500 else "")

            # Get cluster info
            cluster_info = None
            if metadata.cluster_id is not None:
                cluster = all_clusters.get(metadata.cluster_id)
                if cluster:
                    cluster_info = {
                        "id": cluster.id,
                        "name": cluster.name
                    }

            enriched_results.append({
                "doc_id": doc_id,
                "score": score,
                "content": content,
                "metadata": metadata.dict(),
                "cluster": cluster_info
            })

        return enriched_results


class ClusterService:
    """Service for cluster management."""

    def __init__(self, repository: KnowledgeBankRepository):
        """
        Initialize cluster service.

        Args:
            repository: Data repository
        """
        self.repo = repository

    async def get_all_clusters(self) -> List[Dict]:
        """
        Get all clusters with document counts.

        Returns:
            List of cluster summaries
        """
        clusters = await self.repo.get_all_clusters()

        summaries = []
        for cluster in clusters.values():
            summaries.append({
                "id": cluster.id,
                "name": cluster.name,
                "doc_count": len(cluster.document_ids),
                "primary_concepts": cluster.primary_concepts,
                "skill_level": cluster.skill_level
            })

        return summaries

    async def get_cluster_details(self, cluster_id: int) -> Optional[Dict]:
        """
        Get detailed cluster information.

        Args:
            cluster_id: Cluster ID

        Returns:
            Cluster details or None if not found
        """
        cluster = await self.repo.get_cluster(cluster_id)
        if not cluster:
            return None

        return cluster.dict()


class BuildSuggestionService:
    """Service for generating build suggestions."""

    def __init__(
        self,
        repository: KnowledgeBankRepository,
        suggester: BuildSuggester
    ):
        """
        Initialize build suggestion service.

        Args:
            repository: Data repository
            suggester: AI build suggestion generator
        """
        self.repo = repository
        self.suggester = suggester

    async def generate_suggestions(
        self,
        max_suggestions: int = 5
    ) -> Dict:
        """
        Generate project suggestions based on knowledge bank.

        Args:
            max_suggestions: Maximum number of suggestions

        Returns:
            Dict with suggestions and knowledge summary
        """
        # Get all data
        clusters = await self.repo.get_all_clusters()
        metadata = await self.repo.get_all_metadata()
        documents = await self.repo.get_all_documents()

        # Generate suggestions using AI
        suggestions = await self.suggester.analyze_knowledge_bank(
            clusters=clusters,
            metadata=metadata,
            documents=documents,
            max_suggestions=max_suggestions
        )

        # Build knowledge summary
        summary = {
            "total_docs": len(documents),
            "total_clusters": len(clusters),
            "total_concepts": sum(len(m.concepts) for m in metadata.values())
        }

        return {
            "suggestions": [s.dict() for s in suggestions],
            "knowledge_summary": summary
        }
