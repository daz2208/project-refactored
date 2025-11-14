"""
Shared Dependencies for SyncBoard 3.0 Knowledge Bank.

Provides:
- Global state access (documents, metadata, clusters, users)
- Authentication dependencies (get_current_user)
- Storage lock for thread safety
- Service instances
"""

import os
import asyncio
from typing import Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .models import User, DocumentMetadata, Cluster
from .vector_store import VectorStore
from .concept_extractor import ConceptExtractor
from .clustering import ClusteringEngine
from .image_processor import ImageProcessor
from .build_suggester import BuildSuggester
from .auth import decode_access_token
from .constants import DEFAULT_VECTOR_DIM

# =============================================================================
# OAuth2 Scheme
# =============================================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# =============================================================================
# Global State
# =============================================================================

# Vector store for semantic search
vector_store = VectorStore(dim=int(os.environ.get('SYNCBOARD_VECTOR_DIM', str(DEFAULT_VECTOR_DIM))))

# Document storage (in-memory)
documents: Dict[int, str] = {}
metadata: Dict[int, DocumentMetadata] = {}
clusters: Dict[int, Cluster] = {}
users: Dict[str, str] = {}  # username -> hashed_password

# Storage lock for thread safety
storage_lock = asyncio.Lock()

# =============================================================================
# Service Instances
# =============================================================================

concept_extractor = ConceptExtractor()
clustering_engine = ClusteringEngine()
image_processor = ImageProcessor()
build_suggester = BuildSuggester()

# =============================================================================
# Authentication Dependency
# =============================================================================

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get current user from JWT token.

    Args:
        token: JWT token from Authorization header

    Returns:
        User object with username

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not username or username not in users:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    return User(username=username)

# =============================================================================
# State Access Functions
# =============================================================================

def get_documents() -> Dict[int, str]:
    """Get documents dictionary."""
    return documents

def get_metadata() -> Dict[int, DocumentMetadata]:
    """Get metadata dictionary."""
    return metadata

def get_clusters() -> Dict[int, Cluster]:
    """Get clusters dictionary."""
    return clusters

def get_users() -> Dict[str, str]:
    """Get users dictionary."""
    return users

def get_vector_store() -> VectorStore:
    """Get vector store instance."""
    return vector_store

def get_storage_lock() -> asyncio.Lock:
    """Get storage lock for thread-safe operations."""
    return storage_lock

def get_concept_extractor() -> ConceptExtractor:
    """Get concept extractor instance."""
    return concept_extractor

def get_clustering_engine() -> ClusteringEngine:
    """Get clustering engine instance."""
    return clustering_engine

def get_image_processor() -> ImageProcessor:
    """Get image processor instance."""
    return image_processor

def get_build_suggester() -> BuildSuggester:
    """Get build suggester instance."""
    return build_suggester
