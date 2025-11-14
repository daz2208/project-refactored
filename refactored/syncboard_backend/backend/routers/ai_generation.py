"""
AI Generation Router for SyncBoard 3.0 Knowledge Bank.

Endpoints:
- POST /generate - Generate AI content with RAG (Retrieval-Augmented Generation)
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..models import User, GenerationRequest
from ..dependencies import (
    get_current_user,
    get_documents,
    get_metadata,
    get_vector_store,
)

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(
    prefix="",
    tags=["ai-generation"],
    responses={401: {"description": "Unauthorized"}},
)

# Try to import AI generation
try:
    from ..ai_generation_real import generate_with_rag, MODELS
    REAL_AI_AVAILABLE = True
    logger.info("[SUCCESS] Real AI integration loaded")
except ImportError as e:
    REAL_AI_AVAILABLE = False
    logger.warning(f"[WARNING] Real AI not available: {e}")

# =============================================================================
# AI Generation Endpoint
# =============================================================================

@router.post("/generate")
@limiter.limit("5/minute")
async def generate_content(
    req: GenerationRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI content with RAG (Retrieval-Augmented Generation).
    
    Rate limited to 5 requests per minute.
    
    Uses the user's knowledge bank to provide context for generation,
    implementing RAG pattern for better, context-aware responses.
    
    Args:
        req: Generation request with prompt and model selection
        request: FastAPI request (for rate limiting)
        current_user: Authenticated user
    
    Returns:
        AI-generated response based on user's knowledge
    """
    if not REAL_AI_AVAILABLE:
        return {"response": "AI generation not available - API keys not configured"}
    
    documents = get_documents()
    metadata = get_metadata()
    vector_store = get_vector_store()
    
    # Get user's documents for RAG
    user_doc_ids = [
        doc_id for doc_id, meta in metadata.items()
        if meta.owner == current_user.username
    ]
    
    try:
        response_text = await generate_with_rag(
            prompt=req.prompt,
            model=req.model,
            vector_store=vector_store,
            allowed_doc_ids=user_doc_ids,
            documents=documents
        )
        return {"response": response_text}
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return {"response": f"Error: {str(e)}"}
