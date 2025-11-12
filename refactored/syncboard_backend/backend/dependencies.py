"""
Dependency injection setup for FastAPI.

Provides factory functions for creating and sharing service instances.
"""

import os
import logging
from functools import lru_cache

from .repository import KnowledgeBankRepository
from .concept_extractor import ConceptExtractor
from .build_suggester import BuildSuggester
from .llm_providers import OpenAIProvider
from .services import DocumentService, SearchService, ClusterService, BuildSuggestionService

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

STORAGE_PATH = os.environ.get("SYNCBOARD_STORAGE_PATH", "storage.json")
VECTOR_DIM = int(os.environ.get("SYNCBOARD_VECTOR_DIM", "256"))


# =============================================================================
# SINGLETON INSTANCES
# =============================================================================

@lru_cache()
def get_repository() -> KnowledgeBankRepository:
    """
    Get the repository singleton.

    Uses lru_cache to ensure only one instance is created.
    """
    logger.info(f"Initializing repository with storage path: {STORAGE_PATH}")
    return KnowledgeBankRepository(
        storage_path=STORAGE_PATH,
        vector_dim=VECTOR_DIM
    )


@lru_cache()
def get_llm_provider() -> OpenAIProvider:
    """
    Get the LLM provider singleton.

    Uses lru_cache to ensure connection pooling.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable required")

    logger.info("Initializing OpenAI LLM provider")
    return OpenAIProvider(api_key=api_key)


@lru_cache()
def get_concept_extractor() -> ConceptExtractor:
    """Get the concept extractor singleton."""
    provider = get_llm_provider()
    return ConceptExtractor(llm_provider=provider)


@lru_cache()
def get_build_suggester() -> BuildSuggester:
    """Get the build suggester singleton."""
    provider = get_llm_provider()
    return BuildSuggester(llm_provider=provider)


# =============================================================================
# SERVICE FACTORIES
# =============================================================================

def get_document_service() -> DocumentService:
    """
    Get document service instance.

    Creates new instance with injected dependencies.
    """
    repo = get_repository()
    extractor = get_concept_extractor()
    return DocumentService(repository=repo, concept_extractor=extractor)


def get_search_service() -> SearchService:
    """Get search service instance."""
    repo = get_repository()
    return SearchService(repository=repo)


def get_cluster_service() -> ClusterService:
    """Get cluster service instance."""
    repo = get_repository()
    return ClusterService(repository=repo)


def get_build_suggestion_service() -> BuildSuggestionService:
    """Get build suggestion service instance."""
    repo = get_repository()
    suggester = get_build_suggester()
    return BuildSuggestionService(
        repository=repo,
        suggester=suggester
    )
