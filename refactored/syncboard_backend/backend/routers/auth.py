"""
Authentication Router for SyncBoard 3.0 Knowledge Bank.

Endpoints:
- POST /users - Register new user
- POST /token - Login and get JWT token
"""

import os
import logging
from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..models import User, UserCreate, Token, UserLogin
from ..auth import hash_password, verify_password, create_access_token
from ..sanitization import sanitize_username
from ..dependencies import get_users
from ..db_storage_adapter import save_storage_to_db

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Test mode detection
TESTING = os.environ.get('TESTING') == 'true'
REGISTER_RATE_LIMIT = "1000/minute" if TESTING else "3/minute"
LOGIN_RATE_LIMIT = "1000/minute" if TESTING else "5/minute"

# Create router
router = APIRouter(
    prefix="",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}},
)

# =============================================================================
# Registration Endpoint
# =============================================================================

@router.post("/users", response_model=User)
@limiter.limit(REGISTER_RATE_LIMIT)
async def create_user(request: Request, user_create: UserCreate) -> User:
    """
    Register new user.

    Rate limited to 3 attempts per minute in production (1000/min in tests) to prevent abuse.
    
    Args:
        request: FastAPI request object (for rate limiting)
        user_create: User creation data (username, password)
    
    Returns:
        Created user object
    
    Raises:
        HTTPException 400: If username already exists or is invalid
    """
    # Sanitize username to prevent injection attacks
    username = sanitize_username(user_create.username)
    
    users = get_users()
    
    if username in users:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Import global state for saving
    from ..dependencies import documents, metadata, clusters
    
    users[username] = hash_password(user_create.password)
    save_storage_to_db(documents, metadata, clusters, users)
    logger.info(f"Created user: {username}")
    
    return User(username=username)

# =============================================================================
# Login Endpoint
# =============================================================================

@router.post("/token", response_model=Token)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(request: Request, user_login: UserLogin) -> Token:
    """
    Login and get JWT token.

    Rate limited to 5 attempts per minute in production (1000/min in tests) to prevent brute force attacks.
    
    Security: Uses bcrypt password verification (timing-attack resistant).
    
    Args:
        request: FastAPI request object (for rate limiting)
        user_login: Login credentials (username, password)
    
    Returns:
        JWT access token
    
    Raises:
        HTTPException 401: If credentials are invalid
    """
    # Sanitize username to prevent injection attacks
    username = sanitize_username(user_login.username)
    
    users = get_users()
    stored_hash = users.get(username)
    
    if not stored_hash or not verify_password(user_login.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(data={"sub": username})
    return Token(access_token=access_token)
