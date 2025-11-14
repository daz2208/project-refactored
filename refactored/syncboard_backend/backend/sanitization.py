"""
Input Sanitization Module

Provides functions to sanitize and validate user inputs to prevent:
- Path traversal attacks
- XSS attacks
- SQL injection
- Command injection
- Resource exhaustion

All user inputs should pass through these functions before processing.
"""

import re
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from fastapi import HTTPException


# =============================================================================
# Configuration
# =============================================================================

# Maximum lengths to prevent resource exhaustion
MAX_USERNAME_LENGTH = 50
MAX_FILENAME_LENGTH = 255
MAX_TEXT_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB text
MAX_DESCRIPTION_LENGTH = 5000
MAX_CLUSTER_NAME_LENGTH = 100
MAX_URL_LENGTH = 2048

# Allowed characters
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')

# Dangerous path sequences
DANGEROUS_PATH_PATTERNS = [
    '..',
    '~',
    '/',
    '\\',
    '\x00',  # Null byte
]


# =============================================================================
# Filename Sanitization
# =============================================================================

def sanitize_filename(filename: str, allow_extension: bool = True) -> str:
    """
    Sanitize filename to prevent path traversal attacks.

    Prevents:
    - Path traversal (../, ~/, etc.)
    - Null bytes
    - Directory separators
    - Hidden files (.)
    - Overly long filenames

    Args:
        filename: The filename to sanitize
        allow_extension: Whether to preserve file extension

    Returns:
        Sanitized filename safe for filesystem operations

    Raises:
        HTTPException: If filename is invalid or dangerous

    Examples:
        >>> sanitize_filename("document.pdf")
        "document.pdf"
        >>> sanitize_filename("../../../etc/passwd")
        HTTPException (400)
        >>> sanitize_filename("safe file.txt")
        "safe_file.txt"
    """
    if not filename or not filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    original_filename = filename
    filename = filename.strip()

    # Check length
    if len(filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Filename too long. Maximum {MAX_FILENAME_LENGTH} characters."
        )

    # Check for dangerous path patterns
    for pattern in DANGEROUS_PATH_PATTERNS:
        if pattern in filename:
            raise HTTPException(
                status_code=400,
                detail=f"Filename contains forbidden characters: '{original_filename}'"
            )

    # Get basename only (strips any path components)
    filename = os.path.basename(filename)

    # Replace spaces and special characters with underscores
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'\s+', '_', filename)

    # Remove leading dots (hidden files)
    filename = filename.lstrip('.')

    # Ensure we still have a filename
    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Filename invalid after sanitization"
        )

    # Limit filename length (preserve extension if allowed)
    if allow_extension:
        name, ext = os.path.splitext(filename)
        if len(name) > 200:
            name = name[:200]
        filename = name + ext
    else:
        if len(filename) > 200:
            filename = filename[:200]

    return filename


# =============================================================================
# Text Content Sanitization
# =============================================================================

def sanitize_text_content(content: str, max_length: int = MAX_TEXT_CONTENT_LENGTH) -> str:
    """
    Sanitize text content to prevent XSS and resource exhaustion.

    Note: This does NOT strip HTML for knowledge storage (we want to preserve
    code examples, markdown, etc.). Instead, it:
    - Validates length
    - Removes null bytes
    - Normalizes line endings

    HTML escaping should happen at render time in the frontend.

    Args:
        content: The text content to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized content

    Raises:
        HTTPException: If content is too long or contains forbidden characters
    """
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    # Check length
    if len(content) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Content too long. Maximum {max_length / (1024*1024):.0f}MB."
        )

    # Remove null bytes (can cause issues in C-based systems)
    if '\x00' in content:
        raise HTTPException(
            status_code=400,
            detail="Content contains forbidden null bytes"
        )

    # Normalize line endings to Unix style
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    return content


def sanitize_description(description: Optional[str]) -> Optional[str]:
    """
    Sanitize optional description field (shorter length limit).

    Args:
        description: Optional description text

    Returns:
        Sanitized description or None
    """
    if not description:
        return None

    description = description.strip()
    if not description:
        return None

    return sanitize_text_content(description, max_length=MAX_DESCRIPTION_LENGTH)


# =============================================================================
# Username Sanitization
# =============================================================================

def sanitize_username(username: str) -> str:
    """
    Sanitize username to prevent SQL injection and command injection.

    Prevents:
    - SQL injection (quotes, semicolons, etc.)
    - Command injection (shell metacharacters)
    - Unicode exploits
    - Overly long usernames

    Args:
        username: The username to sanitize

    Returns:
        Sanitized username

    Raises:
        HTTPException: If username is invalid

    Examples:
        >>> sanitize_username("john_doe")
        "john_doe"
        >>> sanitize_username("john'; DROP TABLE users; --")
        HTTPException (400)
    """
    if not username or not username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    username = username.strip()

    # Check length
    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters"
        )

    if len(username) > MAX_USERNAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Username too long. Maximum {MAX_USERNAME_LENGTH} characters."
        )

    # Validate characters (alphanumeric, underscore, hyphen only)
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username can only contain letters, numbers, underscores, and hyphens"
        )

    # Prevent reserved names
    reserved = ['admin', 'root', 'system', 'test', 'guest', 'null', 'undefined']
    if username.lower() in reserved:
        raise HTTPException(
            status_code=400,
            detail=f"Username '{username}' is reserved"
        )

    return username


# =============================================================================
# URL Validation
# =============================================================================

def validate_url(url: str) -> str:
    """
    Validate URL for safety beyond Pydantic's HttpUrl.

    Prevents:
    - Local file access (file://)
    - Server-Side Request Forgery (SSRF) via localhost, 127.0.0.1, etc.
    - Very long URLs (resource exhaustion)

    Args:
        url: The URL to validate

    Returns:
        Validated URL

    Raises:
        HTTPException: If URL is unsafe

    Examples:
        >>> validate_url("https://example.com/article")
        "https://example.com/article"
        >>> validate_url("file:///etc/passwd")
        HTTPException (400)
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    url = url.strip()

    # Check length
    if len(url) > MAX_URL_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"URL too long. Maximum {MAX_URL_LENGTH} characters."
        )

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {e}")

    # Check scheme (only http/https allowed)
    if parsed.scheme not in ['http', 'https']:
        raise HTTPException(
            status_code=400,
            detail=f"URL scheme '{parsed.scheme}' not allowed. Only http/https permitted."
        )

    # Check for SSRF attempts (localhost, private IPs)
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="URL must have a hostname")

    # Block localhost variations
    localhost_patterns = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '::1',
        '169.254.',  # Link-local
        '10.',  # Private network
        '172.16.',  # Private network
        '192.168.',  # Private network
    ]

    for pattern in localhost_patterns:
        if hostname.startswith(pattern) or hostname == pattern:
            raise HTTPException(
                status_code=400,
                detail=f"Access to internal/private URLs is forbidden for security"
            )

    return url


# =============================================================================
# Cluster Name Sanitization
# =============================================================================

def sanitize_cluster_name(name: str) -> str:
    """
    Sanitize cluster name.

    Args:
        name: The cluster name to sanitize

    Returns:
        Sanitized name

    Raises:
        HTTPException: If name is invalid
    """
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Cluster name cannot be empty")

    name = name.strip()

    # Check length
    if len(name) > MAX_CLUSTER_NAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Cluster name too long. Maximum {MAX_CLUSTER_NAME_LENGTH} characters."
        )

    # Remove null bytes
    if '\x00' in name:
        raise HTTPException(
            status_code=400,
            detail="Cluster name contains forbidden characters"
        )

    return name


# =============================================================================
# Integer Validation (Prevent Integer Overflow)
# =============================================================================

def validate_positive_integer(value: int, name: str, max_value: int = 1000000) -> int:
    """
    Validate that an integer is positive and within reasonable bounds.

    Args:
        value: The integer to validate
        name: Name of the parameter (for error messages)
        max_value: Maximum allowed value

    Returns:
        Validated integer

    Raises:
        HTTPException: If value is invalid
    """
    if value < 0:
        raise HTTPException(
            status_code=400,
            detail=f"{name} must be positive"
        )

    if value > max_value:
        raise HTTPException(
            status_code=400,
            detail=f"{name} too large. Maximum {max_value}."
        )

    return value
