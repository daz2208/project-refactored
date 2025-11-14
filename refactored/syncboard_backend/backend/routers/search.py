"""
Search Router for SyncBoard 3.0 Knowledge Bank.

Endpoints:
- GET /search_full - Semantic search with filters
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..models import User
from ..dependencies import (
    get_current_user,
    get_documents,
    get_metadata,
    get_clusters,
    get_vector_store,
)
from ..sanitization import validate_positive_integer
from ..constants import DEFAULT_TOP_K, MAX_TOP_K, SNIPPET_LENGTH

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(
    prefix="",
    tags=["search"],
    responses={401: {"description": "Unauthorized"}},
)

# =============================================================================
# Search Endpoint
# =============================================================================

@router.get("/search_full")
@limiter.limit("30/minute")
async def search_full_content(
    q: str,
    top_k: int = DEFAULT_TOP_K,
    cluster_id: Optional[int] = None,
    full_content: bool = False,
    source_type: Optional[str] = None,
    skill_level: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    request: Request = None,
    current_user: User = Depends(get_current_user)
):
    """
    Search documents with optional filters.
    
    Rate limited to 30 searches per minute.
    
    Filters:
    - source_type: Filter by source (text, url, pdf, etc.)
    - skill_level: Filter by skill level (beginner, intermediate, advanced)
    - date_from/date_to: Filter by ingestion date (ISO format)
    - cluster_id: Filter by cluster
    - full_content: Return full content or 500-char snippet
    
    By default returns 500-char snippets for performance.
    
    Args:
        q: Search query
        top_k: Number of results to return (max 50)
        cluster_id: Optional cluster filter
        full_content: Return full content or snippet
        source_type: Optional source type filter
        skill_level: Optional skill level filter
        date_from: Optional start date filter (ISO format)
        date_to: Optional end date filter (ISO format)
        request: FastAPI request (for rate limiting)
        current_user: Authenticated user
    
    Returns:
        Search results with metadata and cluster information
    """
    documents = get_documents()
    metadata = get_metadata()
    clusters = get_clusters()
    vector_store = get_vector_store()
    
    # Validate top_k parameter
    top_k = validate_positive_integer(top_k, "top_k", max_value=MAX_TOP_K)
    if top_k < 1:
        top_k = DEFAULT_TOP_K
    
    # Get user's documents
    user_doc_ids = [
        doc_id for doc_id, meta in metadata.items()
        if meta.owner == current_user.username
    ]
    
    if not user_doc_ids:
        return {"results": [], "grouped_by_cluster": {}}
    
    # Apply filters
    filtered_ids = user_doc_ids.copy()
    
    # Filter by cluster
    if cluster_id is not None:
        filtered_ids = [
            doc_id for doc_id in filtered_ids
            if metadata[doc_id].cluster_id == cluster_id
        ]
    
    # Filter by source type
    if source_type:
        filtered_ids = [
            doc_id for doc_id in filtered_ids
            if metadata[doc_id].source_type == source_type
        ]
    
    # Filter by skill level
    if skill_level:
        filtered_ids = [
            doc_id for doc_id in filtered_ids
            if metadata[doc_id].skill_level == skill_level
        ]
    
    # Filter by date range
    if date_from or date_to:
        date_filtered = []
        for doc_id in filtered_ids:
            meta = metadata[doc_id]
            if not meta.ingested_at:
                continue
            
            try:
                doc_date = datetime.fromisoformat(meta.ingested_at.replace('Z', '+00:00'))
                
                if date_from:
                    from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                    if doc_date < from_date:
                        continue
                
                if date_to:
                    to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                    if doc_date > to_date:
                        continue
                
                date_filtered.append(doc_id)
            except:
                # Skip documents with invalid dates
                continue
        
        filtered_ids = date_filtered
    
    if not filtered_ids:
        return {"results": [], "grouped_by_cluster": {}, "filters_applied": {
            "source_type": source_type,
            "skill_level": skill_level,
            "date_from": date_from,
            "date_to": date_to,
            "cluster_id": cluster_id
        }}
    
    # Search
    search_results = vector_store.search(
        query=q,
        top_k=top_k,
        allowed_doc_ids=filtered_ids
    )
    
    # Build response with metadata
    results = []
    cluster_groups = {}
    
    for doc_id, score, snippet in search_results:
        meta = metadata[doc_id]
        cluster = clusters.get(meta.cluster_id) if meta.cluster_id else None
        
        # Return full content or snippet based on parameter
        if full_content:
            content = documents[doc_id]
        else:
            # Return 500 char snippet for performance
            doc_text = documents[doc_id]
            content = doc_text[:SNIPPET_LENGTH] + ("..." if len(doc_text) > SNIPPET_LENGTH else "")
        
        results.append({
            "doc_id": doc_id,
            "score": score,
            "content": content,
            "metadata": meta.dict(),
            "cluster": cluster.dict() if cluster else None
        })
        
        # Group by cluster
        if meta.cluster_id:
            if meta.cluster_id not in cluster_groups:
                cluster_groups[meta.cluster_id] = []
            cluster_groups[meta.cluster_id].append(doc_id)
    
    return {
        "results": results,
        "grouped_by_cluster": cluster_groups,
        "filters_applied": {
            "source_type": source_type,
            "skill_level": skill_level,
            "date_from": date_from,
            "date_to": date_to,
            "cluster_id": cluster_id
        },
        "total_results": len(results)
    }
