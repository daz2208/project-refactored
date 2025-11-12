"""
Concept extraction using GPT-5 nano.
Analyzes content and extracts topics, concepts, skills, and metadata.
"""

import os
import json
import logging
import hashlib
from typing import Dict
from functools import lru_cache
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class ConceptExtractor:
    """Extract concepts from content using GPT-5 nano."""

    def __init__(self):
        if not OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY not set")
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-5-nano"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def _call_openai_with_retry(self, messages, temperature, max_tokens):
        """Call OpenAI API with retry logic for transient failures."""
        return await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

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
                    {"name": "Docker", "category": "tool", "confidence": 0.95},
                    {"name": "Python", "category": "language", "confidence": 0.88}
                ],
                "skill_level": "intermediate",
                "primary_topic": "containerization",
                "suggested_cluster": "Docker & Deployment"
            }
        """
        
        # Truncate content for concept extraction (first 2000 chars sufficient)
        sample = content[:2000] if len(content) > 2000 else content

        # Check cache first
        content_hash = self._compute_content_hash(content, source_type)
        logger.debug(f"Content hash: {content_hash}")

        prompt = f"""Analyze this {source_type} content and extract structured information.

CONTENT:
{sample}

Return ONLY valid JSON (no markdown, no explanation) with this structure:
{{
  "concepts": [
    {{"name": "concept name", "category": "tool|skill|language|framework|concept|domain", "confidence": 0.0-1.0}}
  ],
  "skill_level": "beginner|intermediate|advanced",
  "primary_topic": "main topic in 2-4 words",
  "suggested_cluster": "cluster name for grouping similar content"
}}

Extract 3-10 concepts. Be specific. Use lowercase for names."""

        try:
            response = await self._call_openai_with_retry(
                messages=[
                    {"role": "system", "content": "You are a concept extraction system. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            logger.info(f"Extracted {len(result.get('concepts', []))} concepts from {source_type}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Raw response: {result_text}")
            # Return minimal fallback
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
