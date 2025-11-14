"""
FastAPI backend for SyncBoard 3.0 Knowledge Bank.

Knowledge-first architecture with auto-clustering and build suggestions.
Boards removed - all content organized by AI-discovered concepts.

This main file handles app initialization and router mounting.
All endpoints are organized in the routers/ directory.
"""

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
env_paths = [
    Path(__file__).parent.parent / '.env',
    Path(__file__).parent / '.env',
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import routers
from .routers import auth, uploads, search, clusters, documents, build_suggestions, analytics, ai_generation

# Import dependencies and shared state
from . import dependencies
from .database import init_db, check_database_health
from .db_storage_adapter import load_storage_from_db, save_storage_to_db
from .storage import load_storage
from .auth import hash_password
from .constants import DEFAULT_STORAGE_PATH
from .security_middleware import SecurityHeadersMiddleware, HTTPSRedirectMiddleware, get_environment

# =============================================================================
# Configuration
# =============================================================================

STORAGE_PATH = os.environ.get('SYNCBOARD_STORAGE_PATH', DEFAULT_STORAGE_PATH)
ALLOWED_ORIGINS = os.environ.get('SYNCBOARD_ALLOWED_ORIGINS', '*')
TESTING = os.environ.get('TESTING') == 'true'

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

# Rate limiting (disabled in test mode)
if not TESTING:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("🚦 Rate limiting enabled")
else:
    # Create dummy limiter for tests
    limiter = Limiter(key_func=lambda: "test-client")
    app.state.limiter = limiter
    logger.info("🚦 Rate limiting disabled (test mode)")

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

# Security headers middleware (Phase 2)
environment = get_environment()
logger.info(f"🔒 Running in {environment} environment")

# Add security headers to all responses
app.add_middleware(SecurityHeadersMiddleware, environment=environment)

# Enforce HTTPS in production
if environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware, environment=environment)
    logger.info("🔒 HTTPS enforcement enabled")
else:
    logger.info("ℹ️  HTTPS enforcement disabled (not production)")

# Request ID middleware
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

# =============================================================================
# Startup Event
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database and load data on startup."""
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")

        # Load from database
        docs, meta, clusts, usrs = load_storage_from_db(dependencies.vector_store)
        
        # Update global state
        dependencies.documents.update(docs)
        dependencies.metadata.update(meta)
        dependencies.clusters.update(clusts)
        dependencies.users.update(usrs)
        
        logger.info(f"Loaded from database: {len(docs)} documents, {len(clusts)} clusters, {len(usrs)} users")
    except Exception as e:
        logger.warning(f"Database load failed: {e}. Falling back to file storage.")
        # Fallback to file storage
        docs, meta, clusts, usrs = load_storage(STORAGE_PATH, dependencies.vector_store)
        
        # Update global state
        dependencies.documents.update(docs)
        dependencies.metadata.update(meta)
        dependencies.clusters.update(clusts)
        dependencies.users.update(usrs)
        
        logger.info(f"Loaded from file: {len(docs)} documents, {len(clusts)} clusters, {len(usrs)} users")

    # Create default test user if none exist
    if not dependencies.users:
        dependencies.users['test'] = hash_password('test123')
        try:
            save_storage_to_db(
                dependencies.documents,
                dependencies.metadata,
                dependencies.clusters,
                dependencies.users
            )
            logger.info("Created default test user in database")
        except Exception as e:
            logger.warning(f"Database save failed: {e}")

# =============================================================================
# Mount Routers
# =============================================================================

# Authentication endpoints
app.include_router(auth.router)

# Upload endpoints
app.include_router(uploads.router)

# Search endpoints
app.include_router(search.router)

# Cluster management endpoints
app.include_router(clusters.router)

# Document CRUD endpoints
app.include_router(documents.router)

# Build suggestion endpoints
app.include_router(build_suggestions.router)

# Analytics endpoints
app.include_router(analytics.router)

# AI generation endpoints
app.include_router(ai_generation.router)

# =============================================================================
# Health Check Endpoint
# =============================================================================

@app.get("/health", tags=["health"])
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
            "documents": len(dependencies.documents),
            "clusters": len(dependencies.clusters),
            "users": len(dependencies.users),
            "vector_store_size": len(dependencies.vector_store.docs) if hasattr(dependencies.vector_store, 'docs') else 0
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

    # Check OpenAI API
    try:
        openai_key = os.environ.get('OPENAI_API_KEY')
        health_data["dependencies"]["openai_configured"] = bool(openai_key and openai_key.startswith('sk-'))
    except Exception:
        health_data["dependencies"]["openai_configured"] = False

    # Check database health
    try:
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
        health_data["dependencies"].get("storage_file_exists", False) or health_data["dependencies"].get("database", {}).get("database_connected", False),
        health_data["dependencies"].get("openai_configured", False)
    ])

    if not all_healthy:
        health_data["status"] = "degraded"

    return health_data

# =============================================================================
# Mount Static Files
# =============================================================================

try:
    static_path = Path(__file__).parent / 'static'
    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")
