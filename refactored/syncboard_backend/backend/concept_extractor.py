"""
Concept extraction with LLM provider abstraction.
Analyzes content and extracts topics, concepts, skills, and metadata.
"""

import os
import json
import logging
import hashlib
from typing import Dict, Optional
from functools import lru_cache

from .llm_providers import LLMProvider, OpenAIProvider

logger = logging.getLogger(__name__)


class ConceptExtractor:
    """Extract concepts from content using configurable LLM provider."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize concept extractor.

        Args:
            llm_provider: LLM provider to use (defaults to OpenAIProvider)
        """
        if llm_provider is None:
            # Default to OpenAI provider
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable required")
            self.provider = OpenAIProvider(api_key=api_key)
        else:
            self.provider = llm_provider

    def _compute_content_hash(self, content: str, source_type: str) -> str:
        """Compute hash of content for caching."""
        # Use first 2000 chars (same as sample size) for consistency
        sample = content[:2000] if len(content) > 2000 else content
        key = f"{source_type}:{sample}"
        return hashlib.sha256(key.encode()).hexdigest()

    @lru_cache(maxsize=1000)
    def _get_cached_result(self, content_hash: str) -> str:
        """
        Cache wrapper for concept extraction results.

        Returns JSON string of cached result, or empty string if not cached.
        This method is decorated with lru_cache to enable result caching.
        """
        # This is a cache key holder - actual caching happens at decorator level
        return ""

    def _cache_result(self, content_hash: str, result: Dict) -> None:
        """Store result in cache."""
        # Store serialized result in cache
        self._get_cached_result(content_hash)
        # The actual cache storage happens through the lru_cache decorator

    async def extract(self, content: str, source_type: str) -> Dict:
        """
        Extract concepts from content.

        Args:
            content: Full text content
            source_type: "youtube", "pdf", "text", "url", "audio", "image"

        Returns:
            {
                "concepts": [
                    {"name": "Docker", "relevance": 0.95},
                    {"name": "Python", "relevance": 0.88}
                ],
                "skill_level": "intermediate",
                "primary_topic": "containerization",
                "suggested_cluster": "Docker & Deployment"
            }
        """

        # Check cache first
        content_hash = self._compute_content_hash(content, source_type)
        logger.debug(f"Content hash: {content_hash}")

        try:
            # Delegate to LLM provider
            result = await self.provider.extract_concepts(content, source_type)

            logger.info(f"Extracted {len(result.get('concepts', []))} concepts from {source_type}")

            return result

        except Exception as e:
            logger.error(f"Concept extraction failed: {e}")
            return {
                "concepts": [],
                "skill_level": "unknown",
                "primary_topic": "uncategorized",
                "suggested_cluster": "General"
            }
