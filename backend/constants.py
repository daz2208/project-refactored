"""
Application Constants for SyncBoard 3.0 Knowledge Bank.

Centralizes configuration values, limits, and magic numbers.
"""

import os

# =============================================================================
# File Upload Limits
# =============================================================================

MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50MB max file upload
MAX_TEXT_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max text content
MAX_DESCRIPTION_LENGTH = 5000  # 5000 chars for descriptions

# =============================================================================
# Pagination & Search Defaults
# =============================================================================

DEFAULT_TOP_K = 10  # Default number of search results
MAX_TOP_K = 50  # Maximum search results allowed
MAX_SUGGESTIONS = 10  # Maximum build suggestions

# =============================================================================
# Vector Store Configuration
# =============================================================================

DEFAULT_VECTOR_DIM = 256  # Default vector dimension
SNIPPET_LENGTH = 500  # Character length for search result snippets

# =============================================================================
# User & Content Limits
# =============================================================================

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 50
MAX_FILENAME_LENGTH = 255
MAX_CLUSTER_NAME_LENGTH = 100
MAX_URL_LENGTH = 2048

# =============================================================================
# Authentication Configuration
# =============================================================================

DEFAULT_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
JWT_ALGORITHM = "HS256"

# =============================================================================
# Storage Configuration
# =============================================================================

DEFAULT_STORAGE_PATH = "storage.json"

# =============================================================================
# Skill Levels
# =============================================================================

SKILL_LEVELS = ["beginner", "intermediate", "advanced", "unknown"]

# =============================================================================
# Reserved Usernames
# =============================================================================

RESERVED_USERNAMES = ["admin", "root", "system", "test", "guest", "null", "undefined"]
