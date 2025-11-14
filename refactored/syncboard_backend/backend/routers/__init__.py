"""
API Routers for SyncBoard 3.0 Knowledge Bank.

Each router handles a specific domain:
- auth: User authentication (register, login)
- uploads: Content upload endpoints (text, URL, file, image)
- search: Semantic search functionality
- clusters: Cluster management
- documents: Document CRUD operations
- build_suggestions: Build suggestion generation
- analytics: Analytics dashboard
- ai_generation: AI content generation
- duplicates: Duplicate detection (Phase 7.2)
- tags: Tagging system (Phase 7.3)
- saved_searches: Saved searches (Phase 7.4)
- relationships: Document relationships (Phase 7.5)
"""

from . import (
    auth,
    uploads,
    search,
    clusters,
    documents,
    build_suggestions,
    analytics,
    ai_generation,
    duplicates,
    tags,
    saved_searches,
    relationships
)
