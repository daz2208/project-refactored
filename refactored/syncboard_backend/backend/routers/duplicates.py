"""
Duplicate Detection Router (Phase 7.2).

Provides endpoints for finding and merging duplicate documents.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ..models import User
from ..dependencies import get_current_user, get_vector_store
from ..database import get_db_context
from ..duplicate_detection import DuplicateDetector
from ..vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["duplicates"])


@router.get("/duplicates")
async def find_duplicates(
    threshold: float = 0.85,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """Find potentially duplicate documents based on content similarity.

    Args:
        threshold: Similarity threshold (0-1), default 0.85 (85% similar)
        limit: Maximum number of duplicate groups to return
        current_user: Authenticated user

    Returns:
        List of duplicate groups with similarity scores
    """
    try:
        with get_db_context() as db:
            detector = DuplicateDetector(db, vector_store)
            duplicates = detector.find_duplicates(
                username=current_user.username,
                similarity_threshold=threshold,
                limit=limit
            )
            return {"duplicate_groups": duplicates}
    except Exception as e:
        logger.error(f"Duplicate detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/duplicates/{doc_id1}/{doc_id2}")
async def get_duplicate_comparison(
    doc_id1: int,
    doc_id2: int,
    current_user: User = Depends(get_current_user),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """Get detailed side-by-side comparison of two potentially duplicate documents.

    Args:
        doc_id1: First document ID
        doc_id2: Second document ID
        current_user: Authenticated user

    Returns:
        Detailed comparison including similarity score and content
    """
    try:
        with get_db_context() as db:
            detector = DuplicateDetector(db, vector_store)
            comparison = detector.get_duplicate_content(doc_id1, doc_id2)
            return comparison
    except Exception as e:
        logger.error(f"Duplicate comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/duplicates/merge")
async def merge_duplicates(
    request: dict,
    current_user: User = Depends(get_current_user),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """Merge duplicate documents, keeping one and deleting the others.

    Args:
        request: JSON with "keep_doc_id" and "delete_doc_ids" list
        current_user: Authenticated user

    Returns:
        Success message with merge results
    """
    try:
        keep_doc_id = request.get("keep_doc_id")
        delete_doc_ids = request.get("delete_doc_ids", [])

        if not keep_doc_id:
            raise HTTPException(status_code=400, detail="keep_doc_id is required")
        if not delete_doc_ids:
            raise HTTPException(status_code=400, detail="delete_doc_ids list is required")

        with get_db_context() as db:
            detector = DuplicateDetector(db, vector_store)
            result = detector.merge_duplicates(
                keep_doc_id=keep_doc_id,
                delete_doc_ids=delete_doc_ids,
                username=current_user.username
            )
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Duplicate merge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
