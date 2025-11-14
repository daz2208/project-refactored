"""
Document Relationships Router (Phase 7.5).

Provides endpoints for linking related documents together.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from ..models import User, RelationshipCreate
from ..dependencies import get_current_user
from ..database import get_db_context
from ..advanced_features_service import DocumentRelationshipsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["relationships"])


@router.post("/documents/{source_doc_id}/relationships")
async def add_document_relationship(
    source_doc_id: int,
    rel_data: RelationshipCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a relationship between two documents.

    Args:
        source_doc_id: Source document ID
        rel_data: Relationship data (target_doc_id, relationship_type, strength)
        current_user: Authenticated user

    Returns:
        Created relationship object
    """
    try:
        with get_db_context() as db:
            rel_service = DocumentRelationshipsService(db)
            result = rel_service.add_relationship(
                source_doc_id,
                rel_data.target_doc_id,
                rel_data.relationship_type,
                current_user.username,
                rel_data.strength
            )
            return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Add relationship failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}/relationships")
async def get_document_relationships(
    doc_id: int,
    relationship_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all relationships for a document.

    Args:
        doc_id: Document ID
        relationship_type: Optional filter by relationship type
        current_user: Authenticated user

    Returns:
        List of related documents with relationship metadata
    """
    try:
        with get_db_context() as db:
            rel_service = DocumentRelationshipsService(db)
            relationships = rel_service.get_related_documents(doc_id, relationship_type)
            return {"relationships": relationships}
    except Exception as e:
        logger.error(f"Get relationships failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{source_doc_id}/relationships/{target_doc_id}")
async def delete_document_relationship(
    source_doc_id: int,
    target_doc_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a relationship between documents.

    Args:
        source_doc_id: Source document ID
        target_doc_id: Target document ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    try:
        with get_db_context() as db:
            rel_service = DocumentRelationshipsService(db)
            result = rel_service.delete_relationship(
                source_doc_id, target_doc_id, current_user.username
            )
            return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Delete relationship failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
