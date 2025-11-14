"""
Authentication Module for SyncBoard 3.0 Knowledge Bank.

Provides:
- Password hashing (bcrypt with unique salts)
- JWT token creation and verification
- Secure authentication helpers
"""

import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

from .constants import JWT_ALGORITHM, DEFAULT_TOKEN_EXPIRE_MINUTES

# =============================================================================
# Configuration
# =============================================================================

SECRET_KEY = os.environ.get('SYNCBOARD_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        "SYNCBOARD_SECRET_KEY environment variable must be set. "
        "Generate one with: openssl rand -hex 32"
    )

TOKEN_EXPIRE_MINUTES = int(os.environ.get('SYNCBOARD_TOKEN_EXPIRE_MINUTES', str(DEFAULT_TOKEN_EXPIRE_MINUTES)))

# Password hashing configuration (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =============================================================================
# Password Hashing
# =============================================================================

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt with automatic per-user salt generation.

    Security improvements over previous implementation:
    - Each password gets a unique salt (prevents rainbow table attacks)
    - Bcrypt is designed for password hashing (slow by design)
    - Automatically handles salt generation and verification

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hash to check against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

# =============================================================================
# JWT Token Management
# =============================================================================

def create_access_token(data: dict) -> str:
    """
    Create a secure JWT access token using python-jose.

    Security improvements over previous implementation:
    - Uses industry-standard JWT library (python-jose)
    - Automatic expiration handling
    - Prevents timing attacks
    - Standard JWT format (compatible with JWT.io, etc.)

    Args:
        data: Dictionary with user data (e.g., {"sub": "username"})

    Returns:
        JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify JWT token using python-jose.

    Args:
        token: JWT token string

    Returns:
        Decoded token data

    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise ValueError('Invalid token')
