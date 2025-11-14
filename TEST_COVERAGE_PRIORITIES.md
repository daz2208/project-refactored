# Test Coverage Priorities for SyncBoard Backend

## Module Dependency Graph

```
API Endpoints (main.py)
    ↓
Authentication (hash_password, JWT token functions)
    ↓
Services Layer (services.py)
    ├─→ DocumentService
    │   ├─→ ConceptExtractor
    │   │   └─→ LLMProvider (OpenAI, Mock)
    │   └─→ Repository (db_repository.py or repository.py)
    │       └─→ VectorStore
    │
    ├─→ SearchService
    │   └─→ Repository + VectorStore
    │
    ├─→ ClusterService
    │   └─→ Repository
    │
    └─→ BuildSuggestionService
        ├─→ BuildSuggester
        │   └─→ LLMProvider
        └─→ Repository

Content Ingestion (ingest.py, image_processor.py)
    ├─→ YouTube transcription (yt-dlp + OpenAI Whisper)
    ├─→ Web extraction (BeautifulSoup)
    ├─→ PDF extraction (pypdf)
    ├─→ Audio transcription (Whisper)
    ├─→ Image OCR (pytesseract)
    └─→ File upload handling

Data Persistence Layer
    ├─→ Database (database.py + db_models.py)
    ├─→ Repository (db_repository.py)
    ├─→ Storage Adapter (db_storage_adapter.py)
    └─→ Vector Store (vector_store.py)

Analytics (analytics_service.py)
    └─→ Database queries
```

---

## Critical Path Test Coverage

### Tier 1: CRITICAL (Must be tested)

These modules handle core business logic and data integrity:

#### 1. **vector_store.py** - Semantic Search
```python
# Test cases needed:
- test_add_single_document()          # Document ID assignment
- test_search_exact_match()           # Query matching identical content
- test_search_similarity()            # TF-IDF cosine similarity
- test_search_with_filters()          # allowed_doc_ids filtering
- test_search_empty_store()           # Handle no documents
- test_remove_document()              # Vector rebuild after removal
- test_batch_add_efficiency()         # Performance: batch vs individual
- test_special_characters()           # Unicode, special chars
- test_large_documents()              # Performance with large text
```

**Why Critical**: Search is the core user-facing feature; accuracy directly affects UX.

#### 2. **db_repository.py** - Database Operations
```python
# Test cases needed:
- test_add_document_full_flow()       # Document + metadata + concepts + vector
- test_get_document_exists()          # Retrieval works
- test_get_document_not_found()       # Proper None return
- test_delete_document_cascade()      # Related concepts deleted
- test_add_cluster()                  # Cluster creation
- test_add_document_to_cluster()      # Association works
- test_search_documents()             # Search integration
- test_concurrent_adds()              # Async lock behavior
- test_user_document_isolation()      # User can only see own docs
```

**Why Critical**: All document operations go through here; affects data integrity.

#### 3. **services.py** - Business Logic Orchestration
```python
# Test cases needed:
- test_ingest_text_full_pipeline()    # Content → concepts → cluster
- test_auto_clustering_logic()        # Jaccard similarity matching
- test_search_with_enrichment()       # Metadata + cluster info
- test_build_suggestions()            # Full flow with AI
- test_empty_knowledge_bank()         # Handle edge cases
- test_concurrent_ingestion()         # Multiple simultaneous uploads
```

**Why Critical**: Orchestrates the user workflow; determines how data flows.

#### 4. **clustering.py** - Document Grouping
```python
# Test cases needed:
- test_jaccard_similarity()           # Similarity calculation
- test_cluster_matching_threshold()   # Threshold 0.5 behavior
- test_cluster_name_boost()           # +0.2 boost for name match
- test_create_new_cluster()           # New cluster creation
- test_empty_clusters_dict()          # Starting with no clusters
- test_concept_deduplication()        # Top 5 concepts selection
```

**Why Critical**: Core algorithm for knowledge organization.

#### 5. **llm_providers.py** - AI Integration
```python
# Test cases needed:
- test_openai_concept_extraction()    # API call + JSON parse
- test_openai_build_suggestions()     # API call + response handling
- test_retry_logic()                  # Exponential backoff (3x)
- test_json_parse_error()             # Fallback on bad JSON
- test_api_error_handling()           # Network errors
- test_mock_provider()                # Mock responses work
```

**Why Critical**: AI is essential feature; failures break concept extraction.

---

### Tier 2: HIGH PRIORITY (Should be tested)

#### 6. **ingest.py** - Content Processing
```python
# Test cases needed:
# YouTube/TikTok:
- test_youtube_transcription()        # Full flow
- test_audio_compression()            # Compression for >25MB
- test_audio_chunking()               # Split long videos
- test_invalid_youtube_url()          # Error handling

# Web:
- test_web_extraction()               # BeautifulSoup parsing
- test_extract_main_content()         # Selector matching
- test_malformed_html()               # Graceful degradation

# PDF:
- test_pdf_extraction()               # pypdf integration
- test_multi_page_pdf()               # Page breaks

# Files:
- test_text_file_upload()             # UTF-8 + latin-1 fallback
- test_audio_file_upload()            # Compression + transcription
- test_file_size_limits()             # 50MB max
- test_corrupted_file()               # Error handling
```

**Why HIGH**: Many ingestion formats; any failure prevents content addition.

#### 7. **analytics_service.py** - Insights Generation
```python
# Test cases needed:
- test_overview_stats()               # Count aggregations
- test_time_series_data()             # Daily counts, gap filling
- test_cluster_distribution()         # Top clusters
- test_skill_distribution()           # Skill level grouping
- test_source_distribution()          # Source type grouping
- test_top_concepts()                 # Most frequent concepts
- test_recent_activity()              # Activity list
- test_multi_user_filtering()         # Username filter
- test_date_calculations()            # today/week/month logic
```

**Why HIGH**: Impacts dashboard; incorrect stats mislead users.

#### 8. **ai_generation_real.py** - RAG Content Generation
```python
# Test cases needed:
- test_generate_with_context()        # Full RAG flow
- test_document_filtering()           # allowed_doc_ids filter
- test_relevance_scoring()            # Score in context
- test_empty_context()                # No relevant docs
- test_model_selection()              # Model string mapping
- test_openai_error_handling()        # API failures
```

**Why HIGH**: User-facing AI feature; broken generation is poor UX.

#### 9. **database.py** - Connection Management
```python
# Test cases needed:
- test_sqlite_init()                  # Table creation
- test_postgresql_init()              # PostgreSQL support
- test_connection_pooling()           # Pool reuse
- test_connection_timeout()           # Failure handling
- test_get_db_context_manager()       # Commit/rollback
- test_health_check()                 # Status endpoint
```

**Why HIGH**: Database is critical dependency; failures block all operations.

#### 10. **main.py** - API Endpoints
```python
# Test cases needed:
# Auth:
- test_user_registration()            # /users POST
- test_login_flow()                   # /token POST
- test_token_validation()             # Token decode
- test_token_expiration()             # Expired token rejection
- test_rate_limiting()                # 3/min for register, 5/min for login

# Upload:
- test_upload_text()                  # /upload_text
- test_upload_url()                   # /upload
- test_upload_file()                  # /upload_file
- test_upload_image()                 # /upload_image with OCR
- test_file_size_limit()              # 50MB max

# Search:
- test_search_full()                  # /search_full
- test_search_with_cluster_filter()   # Cluster filtering
- test_clusters_list()                # /clusters

# AI:
- test_what_can_i_build()             # /what_can_i_build
- test_generate_with_rag()            # /generate

# Admin:
- test_health_check()                 # /health
- test_export_all()                   # /export/all
- test_analytics()                    # /analytics
```

**Why HIGH**: Endpoints are user-facing; broken endpoints break application.

---

### Tier 3: MEDIUM PRIORITY (Nice to have)

#### 11. **image_processor.py** - Image Processing
```python
# Test cases needed:
- test_image_ocr()                    # Text extraction
- test_image_metadata()               # Width, height, format
- test_image_storage()                # File save
- test_path_traversal_security()      # Security check
- test_image_format_conversion()      # RGB conversion
- test_unsupported_format()           # Error handling
```

#### 12. **concept_extractor.py** - Concept Extraction
```python
# Test cases needed:
- test_extract_concepts()             # Basic extraction
- test_content_hashing()              # Hash computation
- test_content_truncation()           # 2000 char limit
- test_error_fallback()               # Safe defaults
- test_caching()                      # lru_cache behavior
```

#### 13. **build_suggester.py** - Build Suggestions
```python
# Test cases needed:
- test_knowledge_summarization()      # Summary building
- test_analyze_knowledge_bank()       # Full flow
- test_empty_knowledge_bank()         # No documents
- test_json_parsing()                 # Response parsing
- test_max_suggestions()              # Limit enforcement
```

#### 14. **db_storage_adapter.py** - Migration Bridge
```python
# Test cases needed:
- test_load_from_db()                 # Load consistency
- test_save_to_db()                   # Upsert logic
- test_migration_data_integrity()     # File → DB migration
- test_orphan_handling()              # Missing references
```

#### 15. **db_models.py** - ORM Models
```python
# Test cases needed:
- test_relationships()                # User → Document → Concept
- test_cascade_delete()               # Orphan cleanup
- test_indexes()                      # Index effectiveness
- test_constraints()                  # Uniqueness, FK
```

---

### Tier 4: LOW PRIORITY (Infrastructure)

#### 16. **storage.py** - File Storage
```python
# Test cases needed (if still used):
- test_atomic_write()                 # Temp file + rename
- test_load_save_roundtrip()          # Data consistency
- test_file_corruption_recovery()     # Partial writes
```

#### 17. **dependencies.py** - Dependency Injection
```python
# Test cases needed:
- test_singleton_instances()          # @lru_cache works
- test_service_creation()             # Factories work
- test_configuration_loading()        # Env vars
```

#### 18. **models.py** - Schema Validation
```python
# Test cases needed:
- test_document_metadata_validation() # Field validation
- test_username_constraints()         # 3-50 chars
- test_password_constraints()         # 8-128 chars
- test_concept_validation()           # 0-1 confidence
```

---

## Integration Test Scenarios

### End-to-End Workflows

```python
test_complete_workflow_1():
    # Register user → Upload text → Search → Generate suggestions
    1. POST /users (register)
    2. POST /token (login)
    3. POST /upload_text (ingest)
    4. GET /search_full (search for content)
    5. POST /what_can_i_build (get suggestions)
    6. POST /generate (ask question about docs)

test_complete_workflow_2():
    # Upload YouTube → Cluster auto-formation → Search by cluster
    1. POST /upload (YouTube URL)
    2. Verify video transcribed
    3. Verify concepts extracted
    4. Verify cluster created
    5. GET /clusters (list clusters)
    6. GET /search_full (search in cluster)

test_multi_user_isolation():
    # Two users, verify no data leakage
    1. Create user A, add documents
    2. Create user B, add documents
    3. User A searches - should only see A's docs
    4. User B searches - should only see B's docs
    5. Analytics show correct counts per user

test_concurrent_uploads():
    # Multiple simultaneous uploads
    1. Start 10 concurrent upload requests
    2. All should succeed
    3. Documents should be queryable immediately
    4. Clustering should complete correctly

test_rate_limiting():
    # Verify rate limits work
    1. POST /users 4 times in 1 min (should fail 4th)
    2. POST /token 6 times in 1 min (should fail 6th)
    3. Verify 429 response
```

---

## Test Coverage by Module (Priority Order)

| Module | Status | Tier | Key Tests | Complexity |
|--------|--------|------|-----------|------------|
| **vector_store.py** | ? | T1 | Search, filter, rebuild | HIGH |
| **db_repository.py** | ? | T1 | CRUD, cascade, locks | HIGH |
| **services.py** | ? | T1 | Pipeline, clustering | HIGH |
| **clustering.py** | ? | T1 | Similarity, matching | MEDIUM |
| **llm_providers.py** | ? | T1 | API, retry, parse | HIGH |
| **ingest.py** | ? | T2 | YouTube, PDF, audio | VERY HIGH |
| **analytics_service.py** | ? | T2 | Aggregation, filtering | HIGH |
| **ai_generation_real.py** | ? | T2 | RAG, context, API | HIGH |
| **database.py** | ? | T2 | Pool, session, health | MEDIUM |
| **main.py** | ? | T2 | Endpoints, auth, rate | VERY HIGH |
| **image_processor.py** | ? | T3 | OCR, storage, security | MEDIUM |
| **concept_extractor.py** | ? | T3 | Extract, hash, cache | LOW |
| **build_suggester.py** | ? | T3 | Summarize, parse | LOW |
| **db_storage_adapter.py** | ? | T3 | Load, save, migrate | MEDIUM |
| **db_models.py** | ? | T3 | Relationships, cascade | MEDIUM |
| **storage.py** | ? | T4 | Atomic, roundtrip | LOW |
| **dependencies.py** | ? | T4 | Singleton, inject | LOW |
| **models.py** | ? | T4 | Validation | LOW |

---

## Recommended Test Implementation Order

1. **Week 1**: Core data layer (vector_store, db_repository, database)
2. **Week 2**: Business logic (services, clustering, llm_providers)
3. **Week 3**: Content processing (ingest, analytics, ai_generation)
4. **Week 4**: API & integration (main.py endpoints)
5. **Week 5**: Edge cases & security (concurrency, validation, path traversal)

---

## Testing Tools Recommendations

```python
# Unit testing
import pytest
from pytest-asyncio import pytest_mark_asyncio

# Mocking
from unittest.mock import Mock, patch, AsyncMock
from pytest-mock import mocker

# Database testing
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool  # In-memory SQLite

# API testing
from fastapi.testclient import TestClient

# Vector store testing
import numpy as np
from scipy.sparse import csr_matrix

# Common fixtures
@pytest.fixture
def test_db():
    """In-memory SQLite for testing"""
    engine = create_engine('sqlite:///:memory:', poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield SessionLocal(bind=engine)

@pytest.fixture
def mock_openai(mocker):
    """Mock OpenAI provider"""
    return mocker.patch('backend.llm_providers.OpenAI')

@pytest.fixture
def test_vector_store():
    """Fresh vector store for each test"""
    return VectorStore(dim=256)
```

---

## Security Testing Checklist

- [ ] Path traversal attacks (image_processor.py)
- [ ] SQL injection (database queries)
- [ ] XSS (API responses)
- [ ] Token tampering (JWT validation)
- [ ] Rate limiting bypass
- [ ] User isolation (multi-user access control)
- [ ] File upload validation (size, type, content)
- [ ] API authentication required
- [ ] CORS proper configuration
- [ ] Password hashing strength

---

## Performance Testing Checklist

- [ ] Vector store search with 10k documents
- [ ] Database query performance with indexes
- [ ] Concurrent user uploads
- [ ] Memory usage during ingestion
- [ ] API response time (<500ms)
- [ ] Batch operations efficiency
- [ ] Large file handling (50MB upload)
- [ ] Image processing performance
