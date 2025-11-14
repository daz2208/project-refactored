# SyncBoard Backend - Module Summary

## Quick Overview

The backend consists of 20 Python modules organized into 6 functional layers:

### Layer 1: Data Models & Persistence (3 modules)
- **models.py** - Pydantic schemas for API validation
- **db_models.py** - SQLAlchemy ORM models (PostgreSQL/SQLite)
- **database.py** - Connection pooling, session management

### Layer 2: Data Access (3 modules)
- **repository.py** - Legacy file-based data access
- **db_repository.py** - Database repository (current primary)
- **db_storage_adapter.py** - Bridge between file and database storage

### Layer 3: Storage & Search (2 modules)
- **storage.py** - JSON file persistence (fallback)
- **vector_store.py** - TF-IDF semantic search

### Layer 4: AI/LLM (4 modules)
- **llm_providers.py** - OpenAI API wrapper with mock support
- **concept_extractor.py** - Extract concepts from content using AI
- **build_suggester.py** - Generate project recommendations
- **ai_generation_real.py** - RAG-based content generation

### Layer 5: Content Processing (2 modules)
- **ingest.py** - Multi-format content ingestion (YouTube, PDF, audio, web)
- **image_processor.py** - Image OCR and storage

### Layer 6: API & Business Logic (6 modules)
- **main.py** - FastAPI application with 19 HTTP endpoints
- **services.py** - Business logic orchestration (4 service classes)
- **clustering.py** - Auto-clustering with Jaccard similarity
- **analytics_service.py** - Dashboard analytics and insights
- **dependencies.py** - Dependency injection setup
- **__init__.py** - Package initialization

---

## Key Statistics

| Metric | Count |
|--------|-------|
| Total Modules | 20 |
| Total Lines of Code | ~4,000 |
| API Endpoints | 19 |
| Database Tables | 5 |
| Service Classes | 4 |
| LLM Operations | 3 (extract, suggest, generate) |
| Content Formats Supported | 7 (YouTube, TikTok, PDF, audio, web, image, text) |

---

## Critical Path

The critical business flow:

```
User Registration
    ↓
Upload Content (text/URL/file/image)
    ↓
Concept Extraction (via OpenAI)
    ↓
Auto-Clustering (Jaccard similarity)
    ↓
Semantic Search (TF-IDF vectors)
    ↓
Build Suggestions (via OpenAI)
    ↓
RAG Content Generation (via OpenAI)
```

---

## What's Tested vs Missing

### Likely Well-Tested:
- Authentication endpoints
- Basic upload functionality
- CRUD operations
- Health check

### Likely Missing Tests:
- **Search accuracy** (vector_store search quality)
- **Clustering algorithm** (Jaccard similarity edge cases)
- **AI error handling** (LLM retry logic, JSON parsing failures)
- **Concurrent operations** (async locks, race conditions)
- **Large file handling** (50MB uploads, video compression)
- **Database integrity** (cascade deletes, transaction handling)
- **Multi-user isolation** (data privacy)
- **End-to-end workflows** (ingest → cluster → search → generate)
- **Analytics accuracy** (aggregation correctness)
- **Security** (path traversal, token validation, SQL injection)

---

## Module Dependencies

```
main.py (API)
    ↓
services.py (Business Logic)
    ├→ ConceptExtractor → LLMProvider
    ├→ SearchService → Repository → VectorStore
    ├→ ClusterService → Repository → ClusteringEngine
    └→ BuildSuggestionService → BuildSuggester → LLMProvider

ingest.py (Content Processing)
    ├→ OpenAI Whisper (YouTube, audio transcription)
    ├→ BeautifulSoup (web extraction)
    ├→ pypdf (PDF extraction)
    └→ pytesseract (image OCR)

Database Layer
    ├→ database.py (connection pooling)
    ├→ db_models.py (SQLAlchemy ORM)
    └→ db_repository.py (CRUD operations)
```

---

## Data Flow Diagram

```
API Endpoint (main.py)
    ↓
Service Layer (services.py)
    ↓
    ├─→ Repository (db_repository.py) ←→ Database (PostgreSQL/SQLite)
    │   ├─→ VectorStore (in-memory TF-IDF)
    │   └─→ ClusteringEngine
    │
    ├─→ ConceptExtractor
    │   └─→ OpenAI API (concept extraction)
    │
    ├─→ BuildSuggester
    │   └─→ OpenAI API (build suggestions)
    │
    └─→ Content Processors
        ├─→ ingest.py (multimodal content)
        └─→ image_processor.py (OCR)

Analytics (analytics_service.py)
    └→ Database queries → Dashboard
```

---

## API Endpoints Quick Reference

### Authentication (3)
- `POST /users` - Register
- `POST /token` - Login
- `GET /me` - Current user

### Upload (4)
- `POST /upload_text` - Raw text
- `POST /upload` - From URL
- `POST /upload_file` - File bytes
- `POST /upload_image` - Image with OCR

### Search & Retrieval (4)
- `GET /clusters` - List clusters
- `GET /search_full` - Semantic search
- `GET /documents/{doc_id}` - Get document
- `DELETE /documents/{doc_id}` - Delete

### AI Generation (3)
- `POST /what_can_i_build` - Build suggestions
- `POST /generate` - RAG generation
- `PUT /documents/{doc_id}/metadata` - Update metadata

### Admin & Analytics (5)
- `PUT /clusters/{cluster_id}` - Update cluster
- `GET /export/cluster/{cluster_id}` - Export cluster
- `GET /export/all` - Export all
- `GET /health` - Health check
- `GET /analytics` - Dashboard analytics

---

## Key Design Patterns

### 1. Repository Pattern (data access)
- Abstraction layer over database
- Enables testing without DB
- Used by services

### 2. Service Layer Pattern (business logic)
- DocumentService, SearchService, ClusterService, BuildSuggestionService
- Coordinates between repositories and processors
- Single responsibility principle

### 3. Dependency Injection (main.py, dependencies.py)
- Singleton services (@lru_cache)
- Testable with mocks

### 4. LLM Provider Pattern (llm_providers.py)
- Abstract base class
- OpenAI implementation + Mock
- Easy to swap implementations

### 5. Adapter Pattern (db_storage_adapter.py)
- File storage ↔ Database conversion
- Enables migration without data loss

---

## Configuration

### Environment Variables Required:
```
SYNCBOARD_SECRET_KEY        # JWT secret (required)
OPENAI_API_KEY              # OpenAI API key (for AI features)
DATABASE_URL                # PostgreSQL or SQLite (optional)
SYNCBOARD_STORAGE_PATH      # JSON storage path (optional)
SYNCBOARD_TOKEN_EXPIRE_MINUTES  # Token lifetime (default: 1440)
SYNCBOARD_ALLOWED_ORIGINS   # CORS origins (default: *)
```

### Optional:
```
TESSERACT_CMD               # Path to tesseract binary (Windows)
SYNCBOARD_VECTOR_DIM        # Vector dimensions (default: 256)
```

---

## Dependencies by Category

### Core Framework
- FastAPI, Pydantic, SQLAlchemy

### AI/ML
- OpenAI API, scikit-learn (TF-IDF)

### Content Processing
- yt-dlp (YouTube), BeautifulSoup (web), pypdf (PDF), python-docx, Pillow, pytesseract

### Infrastructure
- PostgreSQL/SQLite, slowapi (rate limiting)

---

## Testing Recommendations

### Priority 1 (Critical Path)
1. vector_store.py - Search accuracy
2. db_repository.py - Data integrity
3. services.py - Business workflow
4. llm_providers.py - AI integration

### Priority 2 (User-Facing)
5. ingest.py - Content processing
6. main.py - API endpoints
7. analytics_service.py - Dashboard

### Priority 3 (Supporting)
8. clustering.py - Document grouping
9. image_processor.py - Image handling
10. Other modules

**See TEST_COVERAGE_PRIORITIES.md for detailed test cases**

---

## Known Limitations & TODOs

1. **Vector Store**: Rebuilds on every add/remove (ok for <5000 docs)
2. **Concept Caching**: LRU cache implemented but cache keys not stored
3. **Clustering**: Hardcoded 0.5 threshold (could be configurable)
4. **Analytics**: Uses `concept_text` field that doesn't exist in DBConcept model
5. **Image Storage**: Stores on local filesystem (not cloud-ready)
6. **Token**: Custom JWT implementation (not using industry standard library)

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Add document | O(n log n) | Vector rebuild linear in doc count |
| Search | O(n) | Cosine similarity against all docs |
| Cluster | O(n*c) | Jaccard similarity against existing clusters |
| Extract concepts | O(1) | OpenAI API call (async) |
| Store image | O(1) | Local filesystem write |

---

## File Locations Summary

```
/home/user/project-refactored/refactored/syncboard_backend/backend/
├── models.py                 (Pydantic schemas)
├── db_models.py             (SQLAlchemy models)
├── database.py              (Connection management)
├── repository.py            (File-based repo - legacy)
├── db_repository.py         (Database repo - current)
├── db_storage_adapter.py    (File ↔ DB adapter)
├── storage.py               (JSON file storage)
├── vector_store.py          (TF-IDF semantic search)
├── llm_providers.py         (OpenAI wrapper)
├── concept_extractor.py     (Concept extraction)
├── build_suggester.py       (Build suggestions)
├── ai_generation_real.py    (RAG generation)
├── ingest.py                (Multimodal ingestion)
├── image_processor.py       (Image OCR & storage)
├── services.py              (Business logic)
├── clustering.py            (Document clustering)
├── analytics_service.py     (Dashboard analytics)
├── main.py                  (FastAPI app)
├── dependencies.py          (Dependency injection)
└── __init__.py              (Package init)
```

---

## Documentation Files Generated

1. **BACKEND_MODULES_ANALYSIS.md** - Comprehensive module breakdown (7,000+ lines)
2. **TEST_COVERAGE_PRIORITIES.md** - Test prioritization by tier
3. **MODULE_SUMMARY.md** - This file (quick reference)

Use these to:
- Identify what's tested vs missing
- Plan test implementation strategy
- Understand module interactions
- Locate critical business logic
- Find data persistence touchpoints
- Understand AI/LLM integration points
