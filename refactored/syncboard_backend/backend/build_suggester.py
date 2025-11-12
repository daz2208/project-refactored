"""
AI-powered build suggestion system using GPT-5 mini.
Analyzes knowledge bank and suggests viable projects.
"""

import os
import json
import logging
from typing import List, Dict
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .models import Cluster, DocumentMetadata, BuildSuggestion

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class BuildSuggester:
    """Generate project suggestions from knowledge bank."""
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-5-mini"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def _call_openai_with_retry(self, messages, temperature, max_tokens):
        """Call OpenAI API with retry logic for transient failures."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

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
        
        prompt = f"""You are analyzing a user's knowledge bank to suggest viable project builds.

KNOWLEDGE BANK SUMMARY:
{knowledge_summary}

Based on this knowledge, suggest {max_suggestions} specific, actionable projects the user could build RIGHT NOW.

For each project, provide:
1. Title (short, specific)
2. Description (2-3 sentences, what it does)
3. Feasibility (high/medium/low based on knowledge completeness)
4. Effort estimate (realistic: "2 hours", "1 day", "3 days", "1 week", etc.)
5. Required skills (list specific skills from their knowledge)
6. Missing knowledge (gaps they'd need to fill, be honest)
7. Relevant clusters (which cluster IDs to reference)
8. Starter steps (3-5 concrete first steps)
9. File structure (basic project structure)

Return ONLY valid JSON array (no markdown):
[
  {{
    "title": "Project Name",
    "description": "What it does...",
    "feasibility": "high",
    "effort_estimate": "2 days",
    "required_skills": ["skill1", "skill2"],
    "missing_knowledge": ["gap1", "gap2"],
    "relevant_clusters": [1, 3],
    "starter_steps": ["step 1", "step 2", "step 3"],
    "file_structure": "project/\\n  src/\\n  tests/\\n  README.md"
  }}
]

Be specific. Reference actual content from their knowledge. Prioritize projects they can START TODAY."""

        try:
            response = self._call_openai_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a project advisor. Return only valid JSON arrays of build suggestions."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean markdown if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            suggestions_data = json.loads(result_text)
            
            # Convert to BuildSuggestion objects
            suggestions = []
            for data in suggestions_data[:max_suggestions]:
                suggestions.append(BuildSuggestion(**data))
            
            logger.info(f"Generated {len(suggestions)} build suggestions")
            return suggestions
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Raw response: {result_text}")
            return []
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
