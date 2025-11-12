"""
AI-powered build suggestion system with LLM provider abstraction.
Analyzes knowledge bank and suggests viable projects.
"""

import os
import json
import logging
from typing import List, Dict, Optional

from .llm_providers import LLMProvider, OpenAIProvider
from .models import Cluster, DocumentMetadata, BuildSuggestion

logger = logging.getLogger(__name__)


class BuildSuggester:
    """Generate project suggestions from knowledge bank."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize build suggester.

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

    async def analyze_knowledge_bank(
        self,
        clusters: Dict[int, Cluster],
        metadata: Dict[int, DocumentMetadata],
        documents: Dict[int, str],
        max_suggestions: int = 5
    ) -> List[BuildSuggestion]:
        """
        Analyze user's knowledge and suggest builds.

        Args:
            clusters: User's content clusters
            metadata: Document metadata
            documents: Full document content
            max_suggestions: Number of suggestions to return

        Returns:
            List of BuildSuggestion objects
        """

        # Build knowledge summary
        knowledge_summary = self._summarize_knowledge(clusters, metadata)

        try:
            # Delegate to LLM provider
            suggestions_data = await self.provider.generate_build_suggestions(
                knowledge_summary, max_suggestions
            )

            # Convert to BuildSuggestion objects
            suggestions = []
            for data in suggestions_data[:max_suggestions]:
                suggestions.append(BuildSuggestion(**data))

            logger.info(f"Generated {len(suggestions)} build suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Build suggestion failed: {e}")
            return []
    
    def _summarize_knowledge(
        self,
        clusters: Dict[int, Cluster],
        metadata: Dict[int, DocumentMetadata]
    ) -> str:
        """Create text summary of knowledge bank."""
        
        if not clusters:
            return "Empty knowledge bank"
        
        lines = []
        
        for cluster_id, cluster in clusters.items():
            lines.append(f"\nCLUSTER {cluster_id}: {cluster.name}")
            lines.append(f"  - Documents: {cluster.doc_count}")
            lines.append(f"  - Skill level: {cluster.skill_level}")
            lines.append(f"  - Primary concepts: {', '.join(cluster.primary_concepts[:5])}")
            
            # Sample doc concepts from this cluster
            cluster_docs = [
                meta for meta in metadata.values()
                if meta.cluster_id == cluster_id
            ][:3]  # First 3 docs
            
            if cluster_docs:
                lines.append(f"  - Sample concepts:")
                for meta in cluster_docs:
                    concept_names = [c.name for c in meta.concepts[:3]]
                    lines.append(f"    • {meta.source_type}: {', '.join(concept_names)}")
        
        return "\n".join(lines)
