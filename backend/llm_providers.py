"""
Abstract LLM provider interface for decoupling from specific AI vendors.

This allows easy switching between OpenAI, Anthropic, local models, etc.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def extract_concepts(
        self,
        content: str,
        source_type: str
    ) -> Dict:
        """
        Extract concepts from content.

        Args:
            content: Content to analyze
            source_type: Type of content (text, pdf, etc.)

        Returns:
            Dict with concepts, skill_level, primary_topic, suggested_cluster
        """
        pass

    @abstractmethod
    async def generate_build_suggestions(
        self,
        knowledge_summary: str,
        max_suggestions: int
    ) -> List[Dict]:
        """
        Generate project build suggestions.

        Args:
            knowledge_summary: Summary of user's knowledge bank
            max_suggestions: Maximum number of suggestions

        Returns:
            List of build suggestion dictionaries
        """
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""

    def __init__(
        self,
        api_key: str = None,
        concept_model: str = "gpt-5-nano",
        suggestion_model: str = "gpt-5-mini"
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            concept_model: Model for concept extraction
            suggestion_model: Model for build suggestions
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.concept_model = concept_model
        self.suggestion_model = suggestion_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def _call_openai(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call OpenAI API with retry logic."""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    async def extract_concepts(
        self,
        content: str,
        source_type: str
    ) -> Dict:
        """Extract concepts using OpenAI."""
        # Truncate content for concept extraction
        sample = content[:2000] if len(content) > 2000 else content

        prompt = f"""Analyze this {source_type} content and extract structured information.

CONTENT:
{sample}

Return ONLY valid JSON (no markdown, no explanation) with this structure:
{{
  "concepts": [
    {{"name": "concept name", "relevance": 0.9}}
  ],
  "skill_level": "beginner|intermediate|advanced",
  "primary_topic": "main topic in 2-4 words",
  "suggested_cluster": "cluster name for grouping similar content"
}}

Extract 3-10 concepts. Be specific. Use lowercase for names."""

        try:
            response = await self._call_openai(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a concept extraction system. Return only valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                model=self.concept_model,
                temperature=0.3,
                max_tokens=500
            )

            # Parse JSON response
            result = json.loads(response)
            logger.debug(f"Extracted {len(result.get('concepts', []))} concepts")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from OpenAI: {e}")
            return {
                "concepts": [],
                "skill_level": "unknown",
                "primary_topic": "uncategorized",
                "suggested_cluster": "General"
            }
        except Exception as e:
            logger.error(f"Concept extraction failed: {e}")
            return {
                "concepts": [],
                "skill_level": "unknown",
                "primary_topic": "uncategorized",
                "suggested_cluster": "General"
            }

    async def generate_build_suggestions(
        self,
        knowledge_summary: str,
        max_suggestions: int
    ) -> List[Dict]:
        """Generate build suggestions using OpenAI."""
        prompt = f"""Based on this user's knowledge bank, suggest {max_suggestions} practical projects they could build RIGHT NOW.

KNOWLEDGE BANK:
{knowledge_summary}

Return ONLY a JSON array of suggestions (no markdown, no explanation):
[
  {{
    "title": "Project Name",
    "description": "What they'll build and why it's valuable",
    "feasibility": "high|medium|low",
    "effort_estimate": "2-3 days",
    "required_skills": ["skill1", "skill2"],
    "missing_knowledge": ["gap1", "gap2"],
    "starter_steps": ["step 1", "step 2", "step 3"],
    "file_structure": "project/\\n  src/\\n  tests/\\n  README.md"
  }}
]

Be specific. Reference actual content from their knowledge. Prioritize projects they can START TODAY."""

        try:
            response = await self._call_openai(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a project advisor. Return only valid JSON arrays of build suggestions."
                    },
                    {"role": "user", "content": prompt}
                ],
                model=self.suggestion_model,
                temperature=0.7,
                max_tokens=2000
            )

            # Parse JSON response
            suggestions = json.loads(response)
            logger.info(f"Generated {len(suggestions)} build suggestions")
            return suggestions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from OpenAI: {e}")
            return []
        except Exception as e:
            logger.error(f"Build suggestion generation failed: {e}")
            return []


class MockLLMProvider(LLMProvider):
    """
    Mock LLM provider for testing.

    Returns dummy data without making API calls.
    """

    async def extract_concepts(
        self,
        content: str,
        source_type: str
    ) -> Dict:
        """Return mock concept extraction."""
        return {
            "concepts": [
                {"name": "test concept", "relevance": 0.9},
                {"name": "mock data", "relevance": 0.8}
            ],
            "skill_level": "intermediate",
            "primary_topic": "testing",
            "suggested_cluster": "Test Cluster"
        }

    async def generate_build_suggestions(
        self,
        knowledge_summary: str,
        max_suggestions: int
    ) -> List[Dict]:
        """Return mock build suggestions."""
        return [
            {
                "title": "Test Project",
                "description": "A mock project for testing",
                "feasibility": "high",
                "effort_estimate": "1 day",
                "required_skills": ["testing"],
                "missing_knowledge": [],
                "starter_steps": ["Step 1", "Step 2"],
                "file_structure": "test/\n  src/\n  tests/"
            }
        ]
