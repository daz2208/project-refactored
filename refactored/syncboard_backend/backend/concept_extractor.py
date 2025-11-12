"""
Concept extraction using GPT-5 nano.
Analyzes content and extracts topics, concepts, skills, and metadata.
"""

import os
import json
import logging
from typing import Dict
from openai import OpenAI

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class ConceptExtractor:
    """Extract concepts from content using GPT-5 nano."""
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-5-nano"
    
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
            response = self.client.chat.completions.create(
                model=self.model,
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
