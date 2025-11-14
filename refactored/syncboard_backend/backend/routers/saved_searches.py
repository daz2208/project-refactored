"""
Saved Searches Router (Phase 7.4).

Provides endpoints for saving and reusing search queries.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any

from ..models import User
from ..dependencies import get_current_user
from ..database import get_db_context
from ..advanced_features_service import SavedSearchesService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["saved-searches"])


@router.post("/saved-searches")
async def save_search(
    name: str,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """Save a search query for quick access.

    Args:
        name: Display name for this saved search
        query: Search query text
        filters: Optional filter parameters (cluster_id, source_type, skill_level, dates)
        current_user: Authenticated user

    Returns:
        Saved search object with ID
    """
    try:
        with get_db_context() as db:
            search_service = SavedSearchesService(db)
            saved = search_service.save_search(name, query, filters, current_user.username)
            return saved
    except Exception as e:
        logger.error(f"Save search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saved-searches")
async def get_saved_searches(current_user: User = Depends(get_current_user)):
    """Get all saved searches for the current user.

    Args:
        current_user: Authenticated user

    Returns:
        List of saved searches with usage statistics
    """
    try:
        with get_db_context() as db:
            search_service = SavedSearchesService(db)
            searches = search_service.get_saved_searches(current_user.username)
            return {"saved_searches": searches}
    except Exception as e:
        logger.error(f"Get saved searches failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/saved-searches/{search_id}/use")
async def use_saved_search(
    search_id: int,
    current_user: User = Depends(get_current_user)
):
    """Use a saved search (returns query and filters, updates usage stats).

    Args:
        search_id: Saved search ID
        current_user: Authenticated user

    Returns:
        Search query and filters to execute
    """
    try:
        with get_db_context() as db:
            search_service = SavedSearchesService(db)
            search_data = search_service.use_saved_search(search_id, current_user.username)
            return search_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Use saved search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(
    search_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a saved search.

    Args:
        search_id: Saved search ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    try:
        with get_db_context() as db:
            search_service = SavedSearchesService(db)
            result = search_service.delete_saved_search(search_id, current_user.username)
            return result
    except Exception as e:
        logger.error(f"Delete saved search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
