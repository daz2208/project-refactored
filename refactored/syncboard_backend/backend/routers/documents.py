"""
Documents Router for SyncBoard 3.0 Knowledge Bank.

Endpoints:
- GET /documents/{doc_id} - Get a single document
- DELETE /documents/{doc_id} - Delete a document
- PUT /documents/{doc_id}/metadata - Update document metadata
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends

from ..models import User
from ..dependencies import (
    get_current_user,
    get_documents,
    get_metadata,
    get_clusters,
    get_users,
)
from ..constants import SKILL_LEVELS
from ..db_storage_adapter import save_storage_to_db

# Initialize logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={401: {"description": "Unauthorized"}},
)

# =============================================================================
# Get Document Endpoint
# =============================================================================

@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    user: User = Depends(get_current_user)
):
    """
    Get a single document with metadata.
    
    Args:
        doc_id: Document ID
        user: Authenticated user
    
    Returns:
        Document content, metadata, and cluster information
    
    Raises:
        HTTPException 404: If document not found
    """
    documents = get_documents()
    metadata = get_metadata()
    clusters = get_clusters()
    
    if doc_id not in documents:
        raise HTTPException(404, f"Document {doc_id} not found")
    
    meta = metadata.get(doc_id)
    cluster_info = None
    
    if meta and meta.cluster_id is not None:
        cluster = clusters.get(meta.cluster_id)
        if cluster:
            cluster_info = {
                "id": cluster.id,
                "name": cluster.name
            }
    
    return {
        "doc_id": doc_id,
        "content": documents[doc_id],
        "metadata": meta.dict() if meta else None,
        "cluster": cluster_info
    }

# =============================================================================
# Delete Document Endpoint
# =============================================================================

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Delete a document from the knowledge bank.
    
    Args:
        doc_id: Document ID
        request: FastAPI request (for logging)
        user: Authenticated user
    
    Returns:
        Success message
    
    Raises:
        HTTPException 404: If document not found
    """
    documents = get_documents()
    metadata = get_metadata()
    clusters = get_clusters()
    users = get_users()
    
    if doc_id not in documents:
        raise HTTPException(404, f"Document {doc_id} not found")
    
    # Remove from documents and metadata
    del documents[doc_id]
    meta = metadata.pop(doc_id, None)
    
    # Remove from vector store (if it has a remove method)
    # Note: Current VectorStore doesn't have remove, but we'll handle this gracefully
    
    # Remove from cluster
    cluster_id = meta.cluster_id if meta else None
    if meta and meta.cluster_id is not None:
        cluster = clusters.get(meta.cluster_id)
        if cluster and doc_id in cluster.doc_ids:
            cluster.doc_ids.remove(doc_id)
    
    # Save to database
    save_storage_to_db(documents, metadata, clusters, users)
    
    # Structured logging with request context
    logger.info(
        f"[{request.state.request_id}] User {user.username} deleted document {doc_id} "
        f"(cluster: {cluster_id}, source: {meta.source_type if meta else 'unknown'})"
    )
    return {"message": f"Document {doc_id} deleted successfully"}

# =============================================================================
# Update Document Metadata Endpoint
# =============================================================================

@router.put("/{doc_id}/metadata")
async def update_document_metadata(
    doc_id: int,
    updates: dict,
    user: User = Depends(get_current_user)
):
    """
    Update document metadata (cluster_id, primary_topic, etc).
    
    Args:
        doc_id: Document ID
        updates: Dictionary of fields to update
        user: Authenticated user
    
    Returns:
        Updated metadata
    
    Raises:
        HTTPException 404: If document not found
    """
    documents = get_documents()
    metadata = get_metadata()
    clusters = get_clusters()
    users = get_users()
    
    if doc_id not in documents:
        raise HTTPException(404, f"Document {doc_id} not found")
    
    if doc_id not in metadata:
        raise HTTPException(404, f"Metadata for document {doc_id} not found")
    
    meta = metadata[doc_id]
    
    # Update allowed fields
    if 'primary_topic' in updates:
        meta.primary_topic = updates['primary_topic']
    
    if 'skill_level' in updates:
        if updates['skill_level'] in SKILL_LEVELS:
            meta.skill_level = updates['skill_level']
    
    if 'cluster_id' in updates:
        new_cluster_id = updates['cluster_id']
        old_cluster_id = meta.cluster_id
        
        # Remove from old cluster
        if old_cluster_id is not None and old_cluster_id in clusters:
            old_cluster = clusters[old_cluster_id]
            if doc_id in old_cluster.doc_ids:
                old_cluster.doc_ids.remove(doc_id)
        
        # Add to new cluster
        if new_cluster_id is not None:
            if new_cluster_id not in clusters:
                raise HTTPException(404, f"Cluster {new_cluster_id} not found")
            clusters[new_cluster_id].doc_ids.append(doc_id)
        
        meta.cluster_id = new_cluster_id
    
    # Save to database
    save_storage_to_db(documents, metadata, clusters, users)
    
    logger.info(f"Updated metadata for document {doc_id}")
    return {"message": "Metadata updated", "metadata": meta.dict()}
