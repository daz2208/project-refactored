"""
Uploads Router for SyncBoard 3.0 Knowledge Bank.

Endpoints:
- POST /upload_text - Upload plain text content
- POST /upload - Upload document via URL (YouTube, web article, etc)
- POST /upload_file - Upload file (PDF, audio, etc) as base64
- POST /upload_image - Upload and process image with OCR
"""

import base64
import logging
from datetime import datetime
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..models import (
    TextUpload,
    DocumentUpload,
    FileBytesUpload,
    ImageUpload,
    User,
    DocumentMetadata,
    Concept,
)
from ..dependencies import (
    get_current_user,
    get_documents,
    get_metadata,
    get_clusters,
    get_users,
    get_vector_store,
    get_storage_lock,
    get_concept_extractor,
    get_clustering_engine,
    get_image_processor,
)
from ..sanitization import (
    sanitize_filename,
    sanitize_text_content,
    sanitize_description,
    validate_url,
)
from ..constants import MAX_UPLOAD_SIZE_BYTES
from .. import ingest
from ..db_storage_adapter import save_storage_to_db

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(
    prefix="",
    tags=["uploads"],
    responses={401: {"description": "Unauthorized"}},
)

# =============================================================================
# Clustering Helper
# =============================================================================

async def find_or_create_cluster(
    doc_id: int,
    suggested_cluster: str,
    concepts: List[Dict]
) -> int:
    """Find best cluster or create new one."""
    metadata = get_metadata()
    clusters = get_clusters()
    clustering_engine = get_clustering_engine()
    
    meta = metadata[doc_id]
    
    # Try to find existing cluster
    cluster_id = clustering_engine.find_best_cluster(
        doc_concepts=concepts,
        suggested_name=suggested_cluster,
        existing_clusters=clusters
    )
    
    if cluster_id is not None:
        clustering_engine.add_to_cluster(cluster_id, doc_id, clusters)
        return cluster_id
    
    # Create new cluster
    cluster_id = clustering_engine.create_cluster(
        doc_id=doc_id,
        name=suggested_cluster,
        concepts=concepts,
        skill_level=meta.skill_level,
        existing_clusters=clusters
    )
    
    return cluster_id

# =============================================================================
# Text Upload Endpoint
# =============================================================================

@router.post("/upload_text")
@limiter.limit("10/minute")
async def upload_text_content(
    req: TextUpload,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Upload plain text content.
    
    Rate limited to 10 uploads per minute.
    
    Args:
        req: Text upload request
        request: FastAPI request (for rate limiting)
        current_user: Authenticated user
    
    Returns:
        Document ID, cluster ID, and extracted concepts
    """
    # Sanitize text content to prevent XSS and resource exhaustion
    content = sanitize_text_content(req.content)
    
    documents = get_documents()
    metadata = get_metadata()
    clusters = get_clusters()
    users = get_users()
    vector_store = get_vector_store()
    storage_lock = get_storage_lock()
    concept_extractor = get_concept_extractor()
    
    async with storage_lock:
        # Extract concepts
        extraction = await concept_extractor.extract(content, "text")
        
        # Add to vector store
        doc_id = vector_store.add_document(content)
        documents[doc_id] = content
        
        # Create metadata
        meta = DocumentMetadata(
            doc_id=doc_id,
            owner=current_user.username,
            source_type="text",
            concepts=[Concept(**c) for c in extraction.get("concepts", [])],
            skill_level=extraction.get("skill_level", "unknown"),
            cluster_id=None,
            ingested_at=datetime.utcnow().isoformat(),
            content_length=len(content)
        )
        metadata[doc_id] = meta
        
        # Find or create cluster
        cluster_id = await find_or_create_cluster(
            doc_id=doc_id,
            suggested_cluster=extraction.get("suggested_cluster", "General"),
            concepts=extraction.get("concepts", [])
        )
        metadata[doc_id].cluster_id = cluster_id
        
        # Save
        save_storage_to_db(documents, metadata, clusters, users)
        
        # Structured logging with request context
        logger.info(
            f"[{request.state.request_id}] User {current_user.username} uploaded text as doc {doc_id} "
            f"(cluster: {cluster_id}, concepts: {len(extraction.get('concepts', []))})"
        )
        
        return {
            "document_id": doc_id,
            "cluster_id": cluster_id,
            "concepts": extraction.get("concepts", [])
        }

# =============================================================================
# URL Upload Endpoint
# =============================================================================

@router.post("/upload")
@limiter.limit("5/minute")
async def upload_url(
    doc: DocumentUpload,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Upload document via URL (YouTube, web article, etc).
    
    Rate limited to 5 uploads per minute.
    
    Args:
        doc: Document upload request with URL
        request: FastAPI request (for rate limiting)
        current_user: Authenticated user
    
    Returns:
        Document ID, cluster ID, and extracted concepts
    """
    # Validate URL to prevent SSRF attacks
    url = validate_url(str(doc.url))
    
    try:
        document_text = ingest.download_url(url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to ingest URL: {exc}")
    
    documents = get_documents()
    metadata = get_metadata()
    clusters = get_clusters()
    users = get_users()
    vector_store = get_vector_store()
    storage_lock = get_storage_lock()
    concept_extractor = get_concept_extractor()
    
    async with storage_lock:
        # Extract concepts
        extraction = await concept_extractor.extract(document_text, "url")
        
        # Add to vector store
        doc_id = vector_store.add_document(document_text)
        documents[doc_id] = document_text
        
        # Create metadata
        meta = DocumentMetadata(
            doc_id=doc_id,
            owner=current_user.username,
            source_type="url",
            source_url=url,
            concepts=[Concept(**c) for c in extraction.get("concepts", [])],
            skill_level=extraction.get("skill_level", "unknown"),
            cluster_id=None,
            ingested_at=datetime.utcnow().isoformat(),
            content_length=len(document_text)
        )
        metadata[doc_id] = meta
        
        # Cluster
        cluster_id = await find_or_create_cluster(
            doc_id=doc_id,
            suggested_cluster=extraction.get("suggested_cluster", "General"),
            concepts=extraction.get("concepts", [])
        )
        metadata[doc_id].cluster_id = cluster_id
        
        # Save
        save_storage_to_db(documents, metadata, clusters, users)
        
        logger.info(f"User {current_user.username} uploaded URL as doc {doc_id}")
        
        return {
            "document_id": doc_id,
            "cluster_id": cluster_id,
            "concepts": extraction.get("concepts", [])
        }

# =============================================================================
# File Upload Endpoint
# =============================================================================

@router.post("/upload_file")
@limiter.limit("5/minute")
async def upload_file(
    req: FileBytesUpload,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Upload file (PDF, audio, etc) as base64.
    
    Rate limited to 5 uploads per minute.
    
    Args:
        req: File upload request
        request: FastAPI request (for rate limiting)
        current_user: Authenticated user
    
    Returns:
        Document ID, cluster ID, and extracted concepts
    """
    # Sanitize filename to prevent path traversal attacks
    filename = sanitize_filename(req.filename)
    
    try:
        file_bytes = base64.b64decode(req.content)
        
        # Validate file size
        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES / (1024*1024):.0f}MB"
            )
        
        document_text = ingest.ingest_upload_file(filename, file_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {exc}")
    
    documents = get_documents()
    metadata = get_metadata()
    clusters = get_clusters()
    users = get_users()
    vector_store = get_vector_store()
    storage_lock = get_storage_lock()
    concept_extractor = get_concept_extractor()
    
    async with storage_lock:
        # Extract concepts
        extraction = await concept_extractor.extract(document_text, "file")
        
        # Add to vector store
        doc_id = vector_store.add_document(document_text)
        documents[doc_id] = document_text
        
        # Create metadata
        meta = DocumentMetadata(
            doc_id=doc_id,
            owner=current_user.username,
            source_type="file",
            filename=filename,
            concepts=[Concept(**c) for c in extraction.get("concepts", [])],
            skill_level=extraction.get("skill_level", "unknown"),
            cluster_id=None,
            ingested_at=datetime.utcnow().isoformat(),
            content_length=len(document_text)
        )
        metadata[doc_id] = meta
        
        # Cluster
        cluster_id = await find_or_create_cluster(
            doc_id=doc_id,
            suggested_cluster=extraction.get("suggested_cluster", "General"),
            concepts=extraction.get("concepts", [])
        )
        metadata[doc_id].cluster_id = cluster_id
        
        # Save
        save_storage_to_db(documents, metadata, clusters, users)
        
        logger.info(f"User {current_user.username} uploaded file {filename} as doc {doc_id}")
        
        return {
            "document_id": doc_id,
            "cluster_id": cluster_id,
            "concepts": extraction.get("concepts", [])
        }

# =============================================================================
# Image Upload Endpoint
# =============================================================================

@router.post("/upload_image")
@limiter.limit("10/minute")
async def upload_image(
    req: ImageUpload,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Upload and process image with OCR.
    
    Rate limited to 10 uploads per minute.
    
    Args:
        req: Image upload request
        request: FastAPI request (for rate limiting)
        current_user: Authenticated user
    
    Returns:
        Document ID, cluster ID, OCR text length, image path, and concepts
    """
    # Sanitize filename to prevent path traversal attacks
    filename = sanitize_filename(req.filename)
    
    # Sanitize optional description
    description = sanitize_description(req.description)
    
    try:
        image_bytes = base64.b64decode(req.content)
        
        # Validate file size
        if len(image_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Image too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES / (1024*1024):.0f}MB"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}")
    
    documents = get_documents()
    metadata = get_metadata()
    clusters = get_clusters()
    users = get_users()
    vector_store = get_vector_store()
    storage_lock = get_storage_lock()
    concept_extractor = get_concept_extractor()
    image_processor = get_image_processor()
    
    async with storage_lock:
        # Extract text via OCR
        extracted_text = image_processor.extract_text_from_image(image_bytes)
        
        # Get image metadata
        img_meta = image_processor.get_image_metadata(image_bytes)
        
        # Combine description + OCR text
        full_content = ""
        if description:
            full_content += f"Description: {description}\n\n"
        if extracted_text:
            full_content += f"Extracted text: {extracted_text}\n\n"
        full_content += f"Image metadata: {img_meta}"
        
        # Add to vector store
        doc_id = vector_store.add_document(full_content)
        documents[doc_id] = full_content
        
        # Save physical image
        image_path = image_processor.store_image(image_bytes, doc_id)
        
        # Extract concepts
        extraction = await concept_extractor.extract(full_content, "image")
        
        # Create metadata
        meta = DocumentMetadata(
            doc_id=doc_id,
            owner=current_user.username,
            source_type="image",
            filename=filename,
            concepts=[Concept(**c) for c in extraction.get("concepts", [])],
            skill_level=extraction.get("skill_level", "unknown"),
            cluster_id=None,
            ingested_at=datetime.utcnow().isoformat(),
            content_length=len(full_content),
            image_path=image_path
        )
        metadata[doc_id] = meta
        
        # Cluster
        cluster_id = await find_or_create_cluster(
            doc_id=doc_id,
            suggested_cluster=extraction.get("suggested_cluster", "Images"),
            concepts=extraction.get("concepts", [])
        )
        metadata[doc_id].cluster_id = cluster_id
        
        # Save
        save_storage_to_db(documents, metadata, clusters, users)
        
        logger.info(
            f"User {current_user.username} uploaded image {filename} as doc {doc_id} "
            f"(OCR: {len(extracted_text)} chars)"
        )
        
        return {
            "document_id": doc_id,
            "cluster_id": cluster_id,
            "ocr_text_length": len(extracted_text),
            "image_path": image_path,
            "concepts": extraction.get("concepts", [])
        }
