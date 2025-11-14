"""
Build Suggestions Router for SyncBoard 3.0 Knowledge Bank.

Endpoints:
- POST /what_can_i_build - Analyze knowledge bank and suggest viable projects
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..models import User, BuildSuggestionRequest
from ..dependencies import (
    get_current_user,
    get_documents,
    get_metadata,
    get_clusters,
    get_build_suggester,
)
from ..sanitization import validate_positive_integer
from ..constants import MAX_SUGGESTIONS

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(
    prefix="",
    tags=["build-suggestions"],
    responses={401: {"description": "Unauthorized"}},
)

# =============================================================================
# Build Suggestion Endpoint
# =============================================================================

@router.post("/what_can_i_build")
@limiter.limit("3/minute")
async def what_can_i_build(
    req: BuildSuggestionRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze knowledge bank and suggest viable projects.
    
    Rate limited to 3 requests per minute (expensive operation).
    
    Args:
        req: Build suggestion request with max_suggestions parameter
        request: FastAPI request (for rate limiting)
        current_user: Authenticated user
    
    Returns:
        Project suggestions based on user's knowledge bank
    """
    documents = get_documents()
    metadata = get_metadata()
    clusters = get_clusters()
    build_suggester = get_build_suggester()
    
    # Validate max_suggestions parameter
    max_suggestions = validate_positive_integer(req.max_suggestions, "max_suggestions", max_value=MAX_SUGGESTIONS)
    if max_suggestions < 1:
        max_suggestions = 5
    
    # Filter to user's content
    user_clusters = {
        cid: cluster for cid, cluster in clusters.items()
        if any(metadata[did].owner == current_user.username for did in cluster.doc_ids)
    }
    
    user_metadata = {
        did: meta for did, meta in metadata.items()
        if meta.owner == current_user.username
    }
    
    user_documents = {
        did: doc for did, doc in documents.items()
        if did in user_metadata
    }
    
    if not user_clusters:
        return {
            "suggestions": [],
            "knowledge_summary": {
                "total_docs": 0,
                "total_clusters": 0,
                "clusters": []
            }
        }
    
    # Generate suggestions
    suggestions = await build_suggester.analyze_knowledge_bank(
        clusters=user_clusters,
        metadata=user_metadata,
        documents=user_documents,
        max_suggestions=max_suggestions
    )
    
    return {
        "suggestions": [s.dict() for s in suggestions],
        "knowledge_summary": {
            "total_docs": len(user_documents),
            "total_clusters": len(user_clusters),
            "clusters": [c.dict() for c in user_clusters.values()]
        }
    }
