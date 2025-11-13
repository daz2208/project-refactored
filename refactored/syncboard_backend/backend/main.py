"""
FastAPI backend for SyncBoard 3.0 Knowledge Bank.

Knowledge-first architecture with auto-clustering and build suggestions.
Boards removed - all content organized by AI-discovered concepts.
"""

import os
import asyncio
import base64
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_paths = [
    Path(__file__).parent.parent / '.env',
    Path(__file__).parent / '.env',
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
# SlowAPI temporarily disabled for development
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded
# from slowapi.middleware import SlowAPIMiddleware
import logging

from .models import (
    DocumentUpload,
    TextUpload,
    FileBytesUpload,
    ImageUpload,
    SearchResult,
    UserCreate,
    User,
    Token,
    UserLogin,
    GenerationRequest,
    BuildSuggestionRequest,
    DocumentMetadata,
    Cluster,
    Concept,
)
from .vector_store import VectorStore
from .storage import load_storage, save_storage
from .db_storage_adapter import load_storage_from_db, save_storage_to_db
from .database import init_db, check_database_health
from . import ingest
from .concept_extractor import ConceptExtractor
from .clustering import ClusteringEngine
from .image_processor import ImageProcessor
from .build_suggester import BuildSuggester
from .analytics_service import AnalyticsService
from .duplicate_detection import DuplicateDetector
from .advanced_features_service import TagsService, SavedSearchesService, DocumentRelationshipsService

# Try to import AI generation
try:
    from .ai_generation_real import generate_with_rag, MODELS
    REAL_AI_AVAILABLE = True
    print("[SUCCESS] Real AI integration loaded")
except ImportError as e:
    REAL_AI_AVAILABLE = False
    print(f"[WARNING] Real AI not available: {e}")

import json
import hmac
import hashlib

# =============================================================================
# Configuration
# =============================================================================

STORAGE_PATH = os.environ.get('SYNCBOARD_STORAGE_PATH', 'storage.json')
VECTOR_DIM = int(os.environ.get('SYNCBOARD_VECTOR_DIM', '256'))
SECRET_KEY = os.environ.get('SYNCBOARD_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        "SYNCBOARD_SECRET_KEY environment variable must be set. "
        "Generate one with: openssl rand -hex 32"
    )
TOKEN_EXPIRE_MINUTES = int(os.environ.get('SYNCBOARD_TOKEN_EXPIRE_MINUTES', '1440'))
ALLOWED_ORIGINS = os.environ.get('SYNCBOARD_ALLOWED_ORIGINS', '*')

# File upload limits (50MB max)
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024

# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="SyncBoard Knowledge Bank",
    description="AI-powered knowledge management with auto-clustering",
    version="3.0.0"
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting (temporarily disabled for development)
# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
origins = ALLOWED_ORIGINS.split(',') if ALLOWED_ORIGINS != '*' else ['*']

# Warn if using wildcard CORS in production
if origins == ['*']:
    logger.warning(
        "⚠️  SECURITY WARNING: CORS is set to allow ALL origins (*). "
        "This is insecure for production. Set SYNCBOARD_ALLOWED_ORIGINS to specific domains."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware (Phase 5)
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Add unique request ID to each request for tracing.
    Enables debugging by tracking requests through logs.
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Process request
    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    return response

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# =============================================================================
# Global State
# =============================================================================

vector_store = VectorStore(dim=VECTOR_DIM)
documents: Dict[int, str] = {}
metadata: Dict[int, DocumentMetadata] = {}
clusters: Dict[int, Cluster] = {}
users: Dict[str, str] = {}
storage_lock = asyncio.Lock()

# Initialize processors
concept_extractor = ConceptExtractor()
clustering_engine = ClusteringEngine()
image_processor = ImageProcessor()
build_suggester = BuildSuggester()

# =============================================================================
# Startup
# =============================================================================

@app.on_event("startup")
async def startup_event():
    global documents, metadata, clusters, users

    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")

        # Load from database (Phase 6.5)
        documents, metadata, clusters, users = load_storage_from_db(vector_store)
        logger.info(f"Loaded from database: {len(documents)} documents, {len(clusters)} clusters, {len(users)} users")
    except Exception as e:
        logger.warning(f"Database load failed: {e}. Falling back to file storage.")
        # Fallback to file storage
        documents, metadata, clusters, users = load_storage(STORAGE_PATH, vector_store)
        logger.info(f"Loaded from file: {len(documents)} documents, {len(clusters)} clusters, {len(users)} users")

    # Create default test user if none exist
    if not users:
        users['test'] = hash_password('test123')
        try:
            save_storage_to_db(documents, metadata, clusters, users)
            logger.info("Created default test user in database")
        except Exception as e:
            logger.warning(f"Database save failed: {e}. Saving to file.")
            save_storage_to_db(documents, metadata, clusters, users)
            logger.info("Created default test user in file")

# Mount static files
try:
    static_path = Path(__file__).parent / 'static'
    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# =============================================================================
# Authentication Helpers
# =============================================================================

def hash_password(password: str) -> str:
    """Hash password using PBKDF2."""
    salt = SECRET_KEY.encode('utf-8')
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()


def create_access_token(data: dict) -> str:
    """Create JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    
    payload = json.dumps(to_encode).encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    
    token = f"{payload.hex()}.{signature}"
    return token


def decode_access_token(token: str) -> dict:
    """Decode and verify JWT token."""
    try:
        payload_hex, signature = token.split('.')
        payload = bytes.fromhex(payload_hex)
        
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), payload, hashlib.sha256).hexdigest()
        if signature != expected_sig:
            raise ValueError('Invalid signature')
        
        data = json.loads(payload.decode('utf-8'))
        exp = data.get('exp')
        if exp and exp < int(datetime.utcnow().timestamp()):
            raise ValueError('Token expired')
        
        return data
    except Exception:
        raise ValueError('Invalid token')


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from token."""
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
# Authentication Endpoints
# =============================================================================

@app.post("/users", response_model=User)
async def create_user(user_create: UserCreate) -> User:
    """Register new user."""
    if user_create.username in users:
        raise HTTPException(status_code=400, detail="Username already exists")

    users[user_create.username] = hash_password(user_create.password)
    save_storage_to_db(documents, metadata, clusters, users)
    logger.info(f"Created user: {user_create.username}")

    return User(username=user_create.username)


@app.post("/token", response_model=Token)
async def login(user_login: UserLogin) -> Token:
    """Login and get token."""
    stored_hash = users.get(user_login.username)
    if not stored_hash or stored_hash != hash_password(user_login.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token = create_access_token(data={"sub": user_login.username})
    return Token(access_token=access_token)

# =============================================================================
# Clustering Helper
# =============================================================================

async def find_or_create_cluster(
    doc_id: int,
    suggested_cluster: str,
    concepts: List[Dict]
) -> int:
    """Find best cluster or create new one."""
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
# Upload Endpoints (NO BOARD_ID)
# =============================================================================

@app.post("/upload_text")
async def upload_text_content(
    req: TextUpload,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Upload plain text content."""
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    async with storage_lock:
        # Extract concepts
        extraction = await concept_extractor.extract(req.content, "text")

        # Add to vector store
        doc_id = vector_store.add_document(req.content)
        documents[doc_id] = req.content

        # Create metadata
        meta = DocumentMetadata(
            doc_id=doc_id,
            owner=current_user.username,
            source_type="text",
            concepts=[Concept(**c) for c in extraction.get("concepts", [])],
            skill_level=extraction.get("skill_level", "unknown"),
            cluster_id=None,
            ingested_at=datetime.utcnow().isoformat(),
            content_length=len(req.content)
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

        # Structured logging with request context (Phase 5)
        logger.info(
            f"[{request.state.request_id}] User {current_user.username} uploaded text as doc {doc_id} "
            f"(cluster: {cluster_id}, concepts: {len(extraction.get('concepts', []))})"
        )
        
        return {
            "document_id": doc_id,
            "cluster_id": cluster_id,
            "concepts": extraction.get("concepts", [])
        }


@app.post("/upload")
async def upload_url(
    doc: DocumentUpload,
    current_user: User = Depends(get_current_user)
):
    """Upload document via URL (YouTube, web article, etc)."""
    try:
        document_text = ingest.download_url(str(doc.url))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to ingest URL: {exc}")
    
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
            source_url=str(doc.url),
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


@app.post("/upload_file")
async def upload_file(
    req: FileBytesUpload,
    current_user: User = Depends(get_current_user)
):
    """Upload file (PDF, audio, etc) as base64."""
    try:
        file_bytes = base64.b64decode(req.content)

        # Validate file size
        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES / (1024*1024):.0f}MB"
            )

        document_text = ingest.ingest_upload_file(req.filename, file_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {exc}")
    
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
            filename=req.filename,
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
        
        logger.info(f"User {current_user.username} uploaded file {req.filename} as doc {doc_id}")
        
        return {
            "document_id": doc_id,
            "cluster_id": cluster_id,
            "concepts": extraction.get("concepts", [])
        }


@app.post("/upload_image")
async def upload_image(
    req: ImageUpload,
    current_user: User = Depends(get_current_user)
):
    """Upload and process image with OCR."""
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
    
    async with storage_lock:
        # Extract text via OCR
        extracted_text = image_processor.extract_text_from_image(image_bytes)
        
        # Get image metadata
        img_meta = image_processor.get_image_metadata(image_bytes)
        
        # Combine description + OCR text
        full_content = ""
        if req.description:
            full_content += f"Description: {req.description}\n\n"
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
            filename=req.filename,
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
            f"User {current_user.username} uploaded image {req.filename} as doc {doc_id} "
            f"(OCR: {len(extracted_text)} chars)"
        )
        
        return {
            "document_id": doc_id,
            "cluster_id": cluster_id,
            "ocr_text_length": len(extracted_text),
            "image_path": image_path,
            "concepts": extraction.get("concepts", [])
        }

# =============================================================================
# Cluster Endpoints
# =============================================================================

@app.get("/clusters")
async def get_clusters(
    current_user: User = Depends(get_current_user)
):
    """Get user's clusters."""
    user_clusters = []
    
    for cluster_id, cluster in clusters.items():
        # Check if any docs in cluster belong to user
        has_user_docs = any(
            metadata.get(doc_id) and metadata[doc_id].owner == current_user.username
            for doc_id in cluster.doc_ids
        )
        
        if has_user_docs:
            user_clusters.append(cluster.dict())
    
    return {
        "clusters": user_clusters,
        "total": len(user_clusters)
    }

# =============================================================================
# Search Endpoints
# =============================================================================

@app.get("/search_full")
async def search_full_content(
    q: str,
    top_k: int = 10,
    cluster_id: Optional[int] = None,
    full_content: bool = False,
    source_type: Optional[str] = None,
    skill_level: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Search documents with optional filters (Phase 4).

    Filters:
    - source_type: Filter by source (text, url, pdf, etc.)
    - skill_level: Filter by skill level (beginner, intermediate, advanced)
    - date_from/date_to: Filter by ingestion date (ISO format)
    - cluster_id: Filter by cluster
    - full_content: Return full content or 500-char snippet

    By default returns 500-char snippets for performance.
    """
    if top_k < 1 or top_k > 50:
        top_k = 10

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
            content = doc_text[:500] + ("..." if len(doc_text) > 500 else "")

        results.append({
            "doc_id": doc_id,
            "score": score,
            "content": content,  # Snippet or full content based on parameter
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

# =============================================================================
# Build Suggestion Endpoint
# =============================================================================

@app.post("/what_can_i_build")
async def what_can_i_build(
    req: BuildSuggestionRequest,
    current_user: User = Depends(get_current_user)
):
    """Analyze knowledge bank and suggest viable projects."""
    max_suggestions = req.max_suggestions
    if max_suggestions < 1 or max_suggestions > 10:
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

# =============================================================================
# AI Generation Endpoint (existing)
# =============================================================================

@app.post("/generate")
async def generate_content(
    req: GenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate AI content with RAG."""
    if not REAL_AI_AVAILABLE:
        return {"response": "AI generation not available - API keys not configured"}
    
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

# =============================================================================
# Document Management (Phase 4)
# =============================================================================

@app.get("/documents/{doc_id}")
async def get_document(
    doc_id: int,
    user: User = Depends(get_current_user)
):
    """Get a single document with metadata."""
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


@app.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    request: Request,
    user: User = Depends(get_current_user)
):
    """Delete a document from the knowledge bank."""
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

    # Save to disk
    save_storage_to_db(documents, metadata, clusters, users)

    # Structured logging with request context (Phase 5)
    logger.info(
        f"[{request.state.request_id}] User {user.username} deleted document {doc_id} "
        f"(cluster: {cluster_id}, source: {meta.source_type if meta else 'unknown'})"
    )
    return {"message": f"Document {doc_id} deleted successfully"}


@app.put("/documents/{doc_id}/metadata")
async def update_document_metadata(
    doc_id: int,
    updates: dict,
    user: User = Depends(get_current_user)
):
    """Update document metadata (cluster_id, primary_topic, etc)."""
    if doc_id not in documents:
        raise HTTPException(404, f"Document {doc_id} not found")

    if doc_id not in metadata:
        raise HTTPException(404, f"Metadata for document {doc_id} not found")

    meta = metadata[doc_id]

    # Update allowed fields
    if 'primary_topic' in updates:
        meta.primary_topic = updates['primary_topic']

    if 'skill_level' in updates:
        if updates['skill_level'] in ['beginner', 'intermediate', 'advanced']:
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

    # Save to disk
    save_storage_to_db(documents, metadata, clusters, users)

    logger.info(f"Updated metadata for document {doc_id}")
    return {"message": "Metadata updated", "metadata": meta.dict()}


# =============================================================================
# Cluster Management (Phase 4)
# =============================================================================

@app.put("/clusters/{cluster_id}")
async def update_cluster(
    cluster_id: int,
    updates: dict,
    user: User = Depends(get_current_user)
):
    """Update cluster information (rename, etc)."""
    if cluster_id not in clusters:
        raise HTTPException(404, f"Cluster {cluster_id} not found")

    cluster = clusters[cluster_id]

    # Update allowed fields
    if 'name' in updates:
        cluster.name = updates['name']

    if 'skill_level' in updates:
        if updates['skill_level'] in ['beginner', 'intermediate', 'advanced', 'unknown']:
            cluster.skill_level = updates['skill_level']

    # Save to disk
    save_storage_to_db(documents, metadata, clusters, users)

    logger.info(f"Updated cluster {cluster_id}: {cluster.name}")
    return {"message": "Cluster updated", "cluster": cluster.dict()}


@app.get("/export/cluster/{cluster_id}")
async def export_cluster(
    cluster_id: int,
    format: str = "json",
    user: User = Depends(get_current_user)
):
    """Export a cluster as JSON or Markdown."""
    if cluster_id not in clusters:
        raise HTTPException(404, f"Cluster {cluster_id} not found")

    cluster = clusters[cluster_id]

    # Gather all documents in cluster
    cluster_docs = []
    for doc_id in cluster.doc_ids:
        if doc_id in documents:
            meta = metadata.get(doc_id)
            cluster_docs.append({
                "doc_id": doc_id,
                "content": documents[doc_id],
                "metadata": meta.dict() if meta else None
            })

    if format == "markdown":
        # Build markdown export
        md_content = f"# {cluster.name}\n\n"
        md_content += f"**Skill Level:** {cluster.skill_level}\n"
        md_content += f"**Primary Concepts:** {', '.join(cluster.primary_concepts)}\n"
        md_content += f"**Documents:** {len(cluster_docs)}\n\n"
        md_content += "---\n\n"

        for doc in cluster_docs:
            meta = doc['metadata']
            md_content += f"## Document {doc['doc_id']}\n\n"
            if meta:
                md_content += f"**Source:** {meta['source_type']}\n"
                md_content += f"**Topic:** {meta['primary_topic']}\n"
                md_content += f"**Concepts:** {', '.join([c['name'] for c in meta['concepts']])}\n\n"
            md_content += f"{doc['content']}\n\n"
            md_content += "---\n\n"

        return JSONResponse({
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "format": "markdown",
            "content": md_content
        })

    else:  # JSON format
        return {
            "cluster_id": cluster_id,
            "cluster": cluster.dict(),
            "documents": cluster_docs,
            "export_date": datetime.utcnow().isoformat()
        }


@app.get("/export/all")
async def export_all(
    format: str = "json",
    user: User = Depends(get_current_user)
):
    """Export entire knowledge bank."""
    all_docs = []
    for doc_id in sorted(documents.keys()):
        meta = metadata.get(doc_id)
        cluster_id = meta.cluster_id if meta else None
        cluster_name = clusters[cluster_id].name if cluster_id in clusters else None

        all_docs.append({
            "doc_id": doc_id,
            "content": documents[doc_id],
            "metadata": meta.dict() if meta else None,
            "cluster_name": cluster_name
        })

    if format == "markdown":
        md_content = f"# Knowledge Bank Export\n\n"
        md_content += f"**Export Date:** {datetime.utcnow().isoformat()}\n"
        md_content += f"**Total Documents:** {len(all_docs)}\n"
        md_content += f"**Total Clusters:** {len(clusters)}\n\n"
        md_content += "---\n\n"

        # Group by cluster
        for cluster in clusters.values():
            md_content += f"# Cluster: {cluster.name}\n\n"
            cluster_docs = [d for d in all_docs if d['metadata'] and d['metadata']['cluster_id'] == cluster.id]

            for doc in cluster_docs:
                meta = doc['metadata']
                md_content += f"## Document {doc['doc_id']}\n\n"
                if meta:
                    md_content += f"**Topic:** {meta['primary_topic']}\n"
                md_content += f"{doc['content'][:500]}...\n\n"
                md_content += "---\n\n"

        return JSONResponse({
            "format": "markdown",
            "content": md_content
        })

    else:  # JSON
        return {
            "documents": all_docs,
            "clusters": [c.dict() for c in clusters.values()],
            "export_date": datetime.utcnow().isoformat(),
            "total_documents": len(all_docs),
            "total_clusters": len(clusters)
        }


# =============================================================================
# Health Check (Enhanced - Phase 5)
# =============================================================================

@app.get("/health")
async def health_check():
    """
    Enhanced health check endpoint.

    Returns system status and dependency health for monitoring.
    Includes disk space, vector store size, and data integrity checks.
    """
    import shutil

    # Basic statistics
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "statistics": {
            "documents": len(documents),
            "clusters": len(clusters),
            "users": len(users),
            "vector_store_size": len(vector_store.docs) if hasattr(vector_store, 'docs') else 0
        },
        "dependencies": {}
    }

    # Check disk space
    try:
        disk_usage = shutil.disk_usage("/")
        disk_free_gb = disk_usage.free / (1024 ** 3)
        health_data["dependencies"]["disk_space_gb"] = round(disk_free_gb, 2)
        health_data["dependencies"]["disk_healthy"] = disk_free_gb > 1.0  # At least 1GB free
    except Exception as e:
        health_data["dependencies"]["disk_space_gb"] = "error"
        health_data["dependencies"]["disk_healthy"] = False
        logger.error(f"Failed to check disk space: {e}")

    # Check storage file
    try:
        storage_path = Path(STORAGE_PATH)
        if storage_path.exists():
            file_size_mb = storage_path.stat().st_size / (1024 ** 2)
            health_data["dependencies"]["storage_file_mb"] = round(file_size_mb, 2)
            health_data["dependencies"]["storage_file_exists"] = True
        else:
            health_data["dependencies"]["storage_file_exists"] = False
    except Exception as e:
        health_data["dependencies"]["storage_file_exists"] = "error"
        logger.error(f"Failed to check storage file: {e}")

    # Check OpenAI API (optional - only if we want to be comprehensive)
    try:
        # Don't actually call API, just check if key is set
        openai_key = os.environ.get('OPENAI_API_KEY')
        health_data["dependencies"]["openai_configured"] = bool(openai_key and openai_key.startswith('sk-'))
    except Exception:
        health_data["dependencies"]["openai_configured"] = False

    # Check database health (Phase 6)
    try:
        from .database import check_database_health
        db_health = check_database_health()
        health_data["dependencies"]["database"] = db_health
    except Exception as e:
        health_data["dependencies"]["database"] = {
            "database_connected": False,
            "error": str(e)
        }
        logger.error(f"Failed to check database health: {e}")

    # Overall health status
    all_healthy = all([
        health_data["dependencies"].get("disk_healthy", False),
        health_data["dependencies"].get("storage_file_exists", False) or health_data["dependencies"].get("database", {}).get("database_connected", False),  # Either file or database
        health_data["dependencies"].get("openai_configured", False)
    ])

    if not all_healthy:
        health_data["status"] = "degraded"

    return health_data


# =============================================================================
# Analytics Dashboard (Phase 7.1)
# =============================================================================

@app.get("/analytics")
async def get_analytics(
    time_period: int = 30,
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive analytics for the user's knowledge bank.

    Args:
        time_period: Number of days for time-series data (default: 30)

    Returns:
        Complete analytics including:
        - Overview statistics (total docs, clusters, concepts)
        - Time-series data (document growth over time)
        - Distribution metrics (clusters, skill levels, source types)
        - Top concepts
        - Recent activity
    """
    from .database import get_db_context

    try:
        with get_db_context() as db:
            analytics = AnalyticsService(db)
            data = analytics.get_complete_analytics(
                username=current_user.username,
                time_period_days=time_period
            )
            return data
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate analytics: {str(e)}"
        )


# =============================================================================
# Duplicate Detection (Phase 7.2)
# =============================================================================

@app.get("/duplicates")
async def find_duplicates(
    threshold: float = 0.85,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Find potentially duplicate documents based on content similarity."""
    from .database import get_db_context

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


@app.get("/duplicates/{doc_id1}/{doc_id2}")
async def get_duplicate_comparison(
    doc_id1: int,
    doc_id2: int,
    current_user: User = Depends(get_current_user)
):
    """Get detailed comparison of two potentially duplicate documents."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            detector = DuplicateDetector(db, vector_store)
            comparison = detector.get_duplicate_content(doc_id1, doc_id2)
            return comparison
    except Exception as e:
        logger.error(f"Duplicate comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/duplicates/merge")
async def merge_duplicate_documents(
    keep_doc_id: int,
    delete_doc_ids: List[int],
    current_user: User = Depends(get_current_user)
):
    """Merge duplicate documents by keeping one and deleting others."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            detector = DuplicateDetector(db, vector_store)
            result = detector.merge_duplicates(
                keep_doc_id=keep_doc_id,
                delete_doc_ids=delete_doc_ids,
                username=current_user.username
            )

            # Update in-memory storage after merge
            for doc_id in delete_doc_ids:
                if doc_id in documents:
                    del documents[doc_id]
                if doc_id in metadata:
                    del metadata[doc_id]
                vector_store.remove_document(doc_id)

            # Save changes
            save_storage_to_db(documents, metadata, clusters, users)

            return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Merge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Tags System (Phase 7.3)
# =============================================================================

@app.post("/tags")
async def create_tag(
    name: str,
    color: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Create a new tag."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            tag = tags_service.create_tag(name, current_user.username, color)
            return tag
    except Exception as e:
        logger.error(f"Tag creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tags")
async def get_tags(current_user: User = Depends(get_current_user)):
    """Get all tags for the current user."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            tags = tags_service.get_user_tags(current_user.username)
            return {"tags": tags}
    except Exception as e:
        logger.error(f"Get tags failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/{doc_id}/tags/{tag_id}")
async def add_tag_to_document(
    doc_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user)
):
    """Add a tag to a document."""
    from .database import get_db_context

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


@app.delete("/documents/{doc_id}/tags/{tag_id}")
async def remove_tag_from_document(
    doc_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user)
):
    """Remove a tag from a document."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            result = tags_service.remove_tag_from_document(doc_id, tag_id, current_user.username)
            return result
    except Exception as e:
        logger.error(f"Remove tag from document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{doc_id}/tags")
async def get_document_tags(
    doc_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get all tags for a document."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            tags_service = TagsService(db)
            tags = tags_service.get_document_tags(doc_id)
            return {"tags": tags}
    except Exception as e:
        logger.error(f"Get document tags failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a tag."""
    from .database import get_db_context

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


# =============================================================================
# Saved Searches (Phase 7.4)
# =============================================================================

@app.post("/saved-searches")
async def save_search(
    name: str,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """Save a search query for quick access."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            search_service = SavedSearchesService(db)
            saved = search_service.save_search(name, query, filters, current_user.username)
            return saved
    except Exception as e:
        logger.error(f"Save search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/saved-searches")
async def get_saved_searches(current_user: User = Depends(get_current_user)):
    """Get all saved searches for the current user."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            search_service = SavedSearchesService(db)
            searches = search_service.get_saved_searches(current_user.username)
            return {"saved_searches": searches}
    except Exception as e:
        logger.error(f"Get saved searches failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/saved-searches/{search_id}/use")
async def use_saved_search(
    search_id: int,
    current_user: User = Depends(get_current_user)
):
    """Use a saved search (returns query and filters, updates usage stats)."""
    from .database import get_db_context

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


@app.delete("/saved-searches/{search_id}")
async def delete_saved_search(
    search_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a saved search."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            search_service = SavedSearchesService(db)
            result = search_service.delete_saved_search(search_id, current_user.username)
            return result
    except Exception as e:
        logger.error(f"Delete saved search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Document Relationships (Phase 7.5)
# =============================================================================

@app.post("/documents/{source_doc_id}/relationships")
async def add_document_relationship(
    source_doc_id: int,
    target_doc_id: int,
    relationship_type: str = "related",
    strength: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """Create a relationship between two documents."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            rel_service = DocumentRelationshipsService(db)
            result = rel_service.add_relationship(
                source_doc_id, target_doc_id, relationship_type,
                current_user.username, strength
            )
            return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Add relationship failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{doc_id}/relationships")
async def get_document_relationships(
    doc_id: int,
    relationship_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all relationships for a document."""
    from .database import get_db_context

    try:
        with get_db_context() as db:
            rel_service = DocumentRelationshipsService(db)
            relationships = rel_service.get_related_documents(doc_id, relationship_type)
            return {"relationships": relationships}
    except Exception as e:
        logger.error(f"Get relationships failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{source_doc_id}/relationships/{target_doc_id}")
async def delete_document_relationship(
    source_doc_id: int,
    target_doc_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a relationship between documents."""
    from .database import get_db_context

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
