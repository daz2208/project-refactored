"""Data models and schemas for SyncBoard 3.0 Knowledge Bank."""

from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

# =============================================================================
# REMOVED: Board, BoardCreate (entire board system deleted)
# =============================================================================

# =============================================================================
# Upload Models (board_id removed)
# =============================================================================

class DocumentUpload(BaseModel):
    """Schema for uploading a document via URL."""
    url: HttpUrl


class TextUpload(BaseModel):
    """Schema for uploading raw text content directly."""
    content: str


class FileBytesUpload(BaseModel):
    """Schema for uploading a file encoded as base64 bytes."""
    filename: str
    content: str


class ImageUpload(BaseModel):
    """Schema for uploading images with optional description."""
    filename: str
    content: str  # base64 encoded
    description: Optional[str] = None


# =============================================================================
# Search Models
# =============================================================================

class SearchRequest(BaseModel):
    """Schema for search queries."""
    query: str
    top_k: Optional[int] = 5


class SearchResult(BaseModel):
    """Schema for returning search results from the knowledge base."""
    document_id: int
    similarity: float
    snippet: str


# =============================================================================
# Authentication Models
# =============================================================================

class User(BaseModel):
    """Public representation of a user."""
    username: str


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    username: str
    password: str


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class Token(BaseModel):
    """Representation of an authentication token returned after login."""
    access_token: str
    token_type: str = "bearer"


# =============================================================================
# AI Generation Models
# =============================================================================

class GenerationRequest(BaseModel):
    """Schema for AI content generation requests."""
    prompt: str
    model: Optional[str] = "gpt-5-mini"


class BuildSuggestionRequest(BaseModel):
    """Schema for build suggestion requests."""
    max_suggestions: Optional[int] = 5


# =============================================================================
# NEW: Concept Extraction & Clustering Models
# =============================================================================

class Concept(BaseModel):
    """Extracted concept/topic from content."""
    name: str
    category: str  # "technology", "skill", "tool", "language", "framework", "concept", "domain"
    confidence: float  # 0.0 to 1.0


class DocumentMetadata(BaseModel):
    """Metadata for ingested document."""
    doc_id: int
    owner: str
    source_type: str  # "youtube", "pdf", "text", "url", "audio", "image"
    source_url: Optional[str] = None
    filename: Optional[str] = None
    concepts: List[Concept] = []
    skill_level: str  # "beginner", "intermediate", "advanced", "unknown"
    cluster_id: Optional[int] = None
    ingested_at: str  # ISO timestamp
    content_length: int
    image_path: Optional[str] = None  # For images


class Cluster(BaseModel):
    """Group of related documents."""
    id: int
    name: str  # e.g., "Docker & Containerization"
    primary_concepts: List[str]
    doc_ids: List[int]
    skill_level: str
    doc_count: int


class BuildSuggestion(BaseModel):
    """AI-generated project suggestion."""
    title: str
    description: str
    feasibility: str  # "high", "medium", "low"
    effort_estimate: str  # "1 day", "1 week", etc.
    required_skills: List[str]
    missing_knowledge: List[str]
    relevant_clusters: List[int]
    starter_steps: List[str]
    file_structure: Optional[str] = None
