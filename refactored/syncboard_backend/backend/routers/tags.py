"""
Tags Router (Phase 7.3).

Provides endpoints for managing user-defined tags and tagging documents.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from ..models import User
from ..dependencies import get_current_user
from ..database import get_db_context
from ..advanced_features_service import TagsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tags"])


@router.post("/tags")
async def create_tag(
    name: str,
    color: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Create a new tag.

    Args:
        name: Tag name
        color: Optional hex color code (e.g., "#00d4ff")
        current_user: Authenticated user

    Returns:
        Created tag object
    """
    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            tag = tags_service.create_tag(name, current_user.username, color)
            return tag
    except Exception as e:
        logger.error(f"Tag creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags")
async def get_tags(current_user: User = Depends(get_current_user)):
    """Get all tags for the current user.

    Args:
        current_user: Authenticated user

    Returns:
        List of user's tags with usage statistics
    """
    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            tags = tags_service.get_user_tags(current_user.username)
            return {"tags": tags}
    except Exception as e:
        logger.error(f"Get tags failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{doc_id}/tags/{tag_id}")
async def add_tag_to_document(
    doc_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user)
):
    """Add a tag to a document.

    Args:
        doc_id: Document ID
        tag_id: Tag ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            result = tags_service.add_tag_to_document(doc_id, tag_id, current_user.username)
            return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Add tag to document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}/tags/{tag_id}")
async def remove_tag_from_document(
    doc_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user)
):
    """Remove a tag from a document.

    Args:
        doc_id: Document ID
        tag_id: Tag ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            result = tags_service.remove_tag_from_document(doc_id, tag_id, current_user.username)
            return result
    except Exception as e:
        logger.error(f"Remove tag from document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}/tags")
async def get_document_tags(
    doc_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get all tags for a document.

    Args:
        doc_id: Document ID
        current_user: Authenticated user

    Returns:
        List of tags assigned to the document
    """
    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            tags = tags_service.get_document_tags(doc_id)
            return {"tags": tags}
    except Exception as e:
        logger.error(f"Get document tags failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a tag.

    Args:
        tag_id: Tag ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            result = tags_service.delete_tag(tag_id, current_user.username)
            return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Delete tag failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
