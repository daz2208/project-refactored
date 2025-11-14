# SyncBoard Backend Module Analysis

## Directory Structure Overview

The backend is organized into 20 Python modules under `/home/user/project-refactored/refactored/syncboard_backend/backend/`:

### Core Data Models & Persistence (3 modules)
1. **models.py** - Pydantic API schemas
2. **db_models.py** - SQLAlchemy ORM models  
3. **database.py** - Database connection & session management

### Data Access Layer (3 modules)
4. **repository.py** - File-based repository (legacy)
5. **db_repository.py** - Database repository (Phase 6.5)
6. **db_storage_adapter.py** - Adapter for database ↔ file compatibility

### Storage & Persistence (2 modules)
7. **storage.py** - JSON file persistence (legacy)
8. **vector_store.py** - TF-IDF vector similarity search

### AI/LLM Integration (4 modules)
9. **llm_providers.py** - Abstract LLM provider interface
10. **concept_extractor.py** - AI concept extraction from content
11. **build_suggester.py** - AI project recommendation system
12. **ai_generation_real.py** - RAG-based content generation

### Content Processing (2 modules)
13. **ingest.py** - Multimodal content ingestion (YouTube, PDF, audio, web)
14. **image_processor.py** - OCR & image handling

### Business Logic (3 modules)
15. **services.py** - High-level service orchestration
16. **clustering.py** - Automatic document clustering
17. **analytics_service.py** - Analytics & insights generation

### API & Initialization (2 modules)
18. **main.py** - FastAPI application & endpoints
19. **dependencies.py** - Dependency injection setup
20. **__init__.py** - Package initialization

---

## Detailed Module Breakdown

### 1. DATA MODELS & PERSISTENCE

#### models.py (Pydantic Schemas)
**Purpose**: Input/output validation for HTTP API

**Key Classes**:
- `DocumentUpload`, `TextUpload`, `FileBytesUpload`, `ImageUpload` - Upload schemas
- `SearchRequest`, `SearchResult` - Search interface
- `User`, `UserCreate`, `UserLogin`, `Token` - Authentication
- `GenerationRequest`, `BuildSuggestionRequest` - AI generation
- `Concept`, `DocumentMetadata`, `Cluster` - Domain models
- `BuildSuggestion` - Project suggestion schema

**Test Coverage Needs**: Validator tests, schema validation tests

#### db_models.py (SQLAlchemy ORM)
**Purpose**: PostgreSQL/SQLite table definitions

**Tables**:
- `DBUser` - User accounts (username, hashed_password, created_at)
- `DBDocument` - Document metadata (doc_id, owner, source_type, skill_level, cluster_id)
- `DBConcept` - Extracted concepts (name, category, confidence)
- `DBCluster` - Document groups (name, primary_concepts, skill_level)
- `DBVectorDocument` - Document content & TF-IDF vectors

**Relationships**: User → Documents, Document → Concepts, Document → Cluster, Cluster → Documents

**Test Coverage Needs**: ORM relationship tests, cascade delete tests, index efficiency tests

#### database.py (Database Connection)
**Purpose**: SQLAlchemy engine, session management, connection pooling

**Key Functions**:
- `init_db()` - Create tables on startup
- `get_db()` - FastAPI dependency for session injection
- `get_db_context()` - Context manager for non-FastAPI code
- `check_database_health()` - Health check for monitoring

**Features**: 
- Supports PostgreSQL (with connection pooling) and SQLite
- Connection recycling, pool pre-ping
- Automatic foreign key enforcement for SQLite

**Test Coverage Needs**: Connection pool tests, failover tests, health check tests

---

### 2. DATA ACCESS LAYER

#### repository.py (Legacy File-Based Repository)
**Purpose**: Abstract data access with in-memory + file persistence

**Key Operations**:
- `add_document(content, metadata)` - Store with vector embedding
- `search_documents(query, top_k, cluster_id)` - Semantic search
- `add_cluster(cluster)` - Create document group
- `add_document_to_cluster(doc_id, cluster_id)` - Associate
- `add_user(username, hashed_password)` - Register user

**Data Structures**:
- `documents: Dict[int, str]` - Full content by ID
- `metadata: Dict[int, DocumentMetadata]` - Extracted metadata
- `clusters: Dict[int, Cluster]` - Document groups
- `users: Dict[str, str]` - Username → hashed password

**Sync**: Uses `asyncio.Lock()` for thread-safe access, persists to disk after changes

**Test Coverage Needs**: Lock/concurrency tests, persistence tests, search accuracy tests

#### db_repository.py (Database Repository - Phase 6.5)
**Purpose**: SQLAlchemy-based replacement with same interface as repository.py

**Key Methods** (same as repository.py):
- `add_document()` - Creates DBDocument + DBConcept + DBVectorDocument
- `get_document()` - Retrieves from DBVectorDocument
- `search_documents()` - Uses VectorStore semantic search
- `add_cluster()` - Creates DBCluster
- `add_user()` - Creates DBUser

**Features**:
- Composite indexes for common queries (owner+cluster, source+skill, ingested_at)
- Cascade deletion for related concepts
- Lazy loads vector store on initialization

**Test Coverage Needs**: Database transaction tests, cascade delete tests, query optimization tests

#### db_storage_adapter.py (Adapter Pattern)
**Purpose**: Bridge between file storage and database for seamless migration

**Functions**:
- `load_storage_from_db()` - Hydrates in-memory data structures from DB
- `save_storage_to_db()` - Syncs in-memory data to DB (upsert strategy)

**Strategy**: Creates DBDocument if not exists, updates if exists. Never deletes (safety).

**Test Coverage Needs**: Migration tests, upsert logic tests, orphan handling tests

---

### 3. STORAGE & PERSISTENCE

#### storage.py (JSON File Storage)
**Purpose**: Atomic JSON file persistence for development/testing

**Key Functions**:
- `load_storage(path, vector_store)` - Load documents, metadata, clusters, users from JSON
- `save_storage(path, docs, metadata, clusters, users)` - Atomic write to disk

**Atomicity**: Uses temp file + rename for crash-safe writes

**Data Format**:
```json
{
  "documents": ["text1", "text2", ...],
  "metadata": [{"doc_id": 0, "owner": "user1", ...}, ...],
  "clusters": [{"id": 0, "name": "Docker", ...}, ...],
  "users": {"alice": "hash123", ...}
}
```

**Test Coverage Needs**: Atomicity tests, file corruption recovery tests, migration tests

#### vector_store.py (TF-IDF Vector Search)
**Purpose**: In-memory semantic search using scikit-learn TF-IDF vectorizer

**Key Methods**:
- `add_document(text)` - Returns assigned doc_id, rebuilds vectors
- `add_documents_batch(texts)` - Efficient batch insertion
- `remove_document(doc_id)` - Removes and rebuilds
- `search(query, top_k, allowed_doc_ids)` - Returns (doc_id, score, snippet) tuples

**Algorithm**:
- TF-IDF vectorization (scikit-learn)
- Cosine similarity between query and documents
- Filters by allowed_doc_ids if specified
- Returns top-k results sorted by similarity

**Performance**: Rebuilds vectors on each add/remove (acceptable for <5000 docs)

**Test Coverage Needs**: 
- Search accuracy tests
- Filtering tests  
- Edge cases (empty store, single doc, identical docs)
- Performance regression tests

---

### 4. AI/LLM INTEGRATION

#### llm_providers.py (Provider Abstraction)
**Purpose**: Abstract interface for pluggable LLM providers

**Abstract Base Class**: `LLMProvider`
- `extract_concepts(content, source_type)` - Returns concepts with relevance
- `generate_build_suggestions(knowledge_summary, max_suggestions)` - Project ideas

**Implementations**:

1. **OpenAIProvider**
   - Uses OpenAI Chat API (gpt-5-nano for concepts, gpt-5-mini for suggestions)
   - Retry logic with exponential backoff (3 attempts max)
   - Expects JSON response, falls back gracefully on parse errors
   
   **Request Structure**:
   - Concept extraction: Prompts to extract 3-10 concepts with relevance scores
   - Build suggestions: Prompts for 5 project ideas with full spec (skills, effort, steps)

2. **MockLLMProvider** 
   - Returns hardcoded dummy data for testing
   - No API calls

**Error Handling**: Catches JSON parse errors and API errors, returns empty/default results

**Test Coverage Needs**:
- Mock provider tests
- API error handling tests
- Retry logic tests
- JSON parsing robustness tests
- Rate limiting tests

#### concept_extractor.py (AI Concept Extraction)
**Purpose**: Extracts topics, skills, and metadata from content using LLM

**Class**: `ConceptExtractor`
- Wraps LLMProvider
- Content hashing for potential caching (lru_cache decorator)
- Fallback to safe defaults on errors

**Method**: `extract(content, source_type)`
- Takes first 2000 chars for API efficiency
- Returns dict with:
  - `concepts`: List[{"name": str, "relevance": float}]
  - `skill_level`: "beginner" | "intermediate" | "advanced" | "unknown"
  - `primary_topic`: Suggested main topic
  - `suggested_cluster`: AI-proposed cluster name

**Caching**: Implements lru_cache but not fully utilized (cache keys not stored)

**Test Coverage Needs**:
- Caching effectiveness tests
- Content truncation tests
- Error fallback tests
- Different source types tests

#### build_suggester.py (AI Project Recommendations)
**Purpose**: Analyzes user's knowledge bank and suggests viable projects

**Class**: `BuildSuggester`
- Wraps LLMProvider
- Summarizes knowledge bank into text format

**Method**: `analyze_knowledge_bank(clusters, metadata, documents, max_suggestions)`

**Process**:
1. Summarizes clusters: name, doc count, skill level, sample concepts
2. Sends summary to LLM for project idea generation
3. Converts JSON response to BuildSuggestion objects

**BuildSuggestion Fields**:
- `title`: Project name
- `description`: What they'll build
- `feasibility`: "high" | "medium" | "low"
- `effort_estimate`: "1 day", "1 week", etc.
- `required_skills`: List of needed skills
- `missing_knowledge`: Gaps to fill first
- `starter_steps`: First 3 steps
- `relevant_clusters`: Cluster IDs to reference
- `file_structure`: Optional project scaffold

**Test Coverage Needs**:
- Summary generation tests
- JSON response parsing tests
- Error handling tests
- Feasibility scoring tests
- Empty knowledge bank tests

#### ai_generation_real.py (RAG Content Generation)
**Purpose**: Generate content using user's documents as context

**Function**: `generate_with_rag(prompt, model, vector_store, allowed_doc_ids, documents, top_k)`

**Process** (Retrieval Augmented Generation):
1. Semantic search for top_k relevant documents
2. Filter to user's allowed documents only
3. Build context from documents with relevance scores
4. System prompt: "You are helping user with their knowledge"
5. User prompt: "Based on these documents, answer: {prompt}"
6. Call OpenAI Chat API

**Models Supported**:
- "gpt-4o-mini" (fast, cheap)
- "gpt-4o" (balanced)
- "gpt-4" (advanced, expensive)

**Error Handling**: Wraps OpenAI exceptions, raises with descriptive messages

**Test Coverage Needs**:
- Context building tests
- Document filtering tests
- API error tests
- Model selection tests
- Empty context handling tests

---

### 5. CONTENT PROCESSING

#### ingest.py (Multimodal Ingestion)
**Purpose**: Extract text from multiple content types

**Supported Types**:
1. **YouTube Videos** (via yt-dlp + OpenAI Whisper)
   - Downloads audio with yt-dlp
   - Audio compression if > 25MB (16kHz, mono, 64kbps)
   - If still > 25MB, splits into 10-min chunks
   - Transcribes with Whisper API
   - Returns formatted transcript with title, channel, duration, URL

2. **TikTok Videos** (same as YouTube)
   - Downloads audio, compresses, transcribes

3. **Web Articles** (BeautifulSoup)
   - Fetches HTML with User-Agent header
   - Strips scripts, styles, nav, footer
   - Extracts main content from <article>, <main>, or <body>
   - Cleans whitespace

4. **PDF Files** (pypdf)
   - Extracts text from all pages
   - Returns "PDF DOCUMENT (N pages)" with page breaks

5. **Audio Files** (OpenAI Whisper)
   - Supports .mp3, .wav, .m4a, .ogg, .flac
   - Compresses if > 25MB
   - Returns "AUDIO FILE TRANSCRIPT"

6. **Word Documents** (python-docx)
   - Extracts paragraphs as text

7. **Text Files** (.txt, .md, .csv, .json)
   - Direct decode (UTF-8, fallback to latin-1)

**Key Functions**:
- `download_url(url)` - Router for different types
- `compress_audio_for_whisper()` - FFmpeg compression
- `chunk_audio_file()` - Split for very long videos
- `transcribe_youtube()` - Main YouTube flow
- `extract_web_article()` - BeautifulSoup extraction
- `ingest_upload_file()` - Handle uploaded files

**Test Coverage Needs**:
- Each content type test
- Audio compression tests
- File size edge cases
- API failure handling
- Malformed input tests
- Security (path traversal, injection)

#### image_processor.py (Image Handling & OCR)
**Purpose**: Extract text from images and store image files

**Class**: `ImageProcessor`

**Methods**:
- `extract_text_from_image(image_bytes)` - OCR via pytesseract
  - Opens with PIL, converts to RGB if needed
  - Uses Tesseract OCR
  - Returns extracted text or empty string

- `get_image_metadata(image_bytes)` - Image properties
  - Returns: width, height, format, mode, size_bytes

- `store_image(image_bytes, doc_id)` - Save image to disk
  - Creates `stored_images/` directory
  - Validates doc_id is positive integer
  - Security: Checks filepath is within images_dir (prevents traversal)
  - Saves as PNG
  - Returns filepath or empty string

**Security**: Implements path traversal protection with `is_relative_to()` check

**Test Coverage Needs**:
- OCR accuracy tests
- Metadata extraction tests
- Image storage tests
- Path traversal security tests
- File format handling tests
- Large image handling tests

---

### 6. BUSINESS LOGIC

#### services.py (Service Layer Orchestration)
**Purpose**: Coordinate business operations across repositories and processors

**Classes**:

1. **DocumentService**
   - `ingest_text(content, source_type)` → (doc_id, cluster_id)
     - Extracts concepts via ConceptExtractor
     - Builds DocumentMetadata
     - Saves to repository
     - Auto-clusters based on Jaccard similarity
   - `delete_document(doc_id)` → bool
   - `get_document_with_metadata(doc_id)` → Dict

2. **SearchService**
   - `search(query, top_k, cluster_id, full_content)` → List[Dict]
     - Semantic search via repository
     - Enriches with metadata
     - Returns snippets or full content
     - Includes cluster info

3. **ClusterService**
   - `get_all_clusters()` → List[Dict]
   - `get_cluster_details(cluster_id)` → Dict

4. **BuildSuggestionService**
   - `generate_suggestions(max_suggestions)` → Dict
     - Fetches all clusters, metadata, documents
     - Calls BuildSuggester
     - Returns suggestions + knowledge summary

**Dependency Injection**: Services depend on Repository + optional processors

**Test Coverage Needs**:
- Service integration tests
- End-to-end document ingestion tests
- Clustering logic tests
- Search result enrichment tests
- Build suggestion generation tests

#### clustering.py (Automatic Document Clustering)
**Purpose**: Group related documents by concept similarity

**Class**: `ClusteringEngine`

**Algorithm**: 

`find_best_cluster(doc_concepts, suggested_name, existing_clusters)`:
- Convert concept names to lowercase set
- For each cluster, compute Jaccard similarity
- Boost score if suggested name matches cluster name (+ 0.2)
- Return cluster if score ≥ 0.5 threshold, else None

`create_cluster(doc_id, name, concepts, skill_level, clusters)`:
- Auto-increment cluster_id
- Extract top 5 most common concept names
- Create Cluster object

`add_to_cluster(cluster_id, doc_id, clusters)`:
- Append doc_id to cluster's doc_ids
- Update doc_count

**Similarity Threshold**: 0.5 (can be tuned)

**Test Coverage Needs**:
- Jaccard similarity calculation tests
- Threshold edge case tests
- Cluster creation tests
- Name matching boost tests
- Empty cluster tests

#### analytics_service.py (Analytics & Insights - Phase 7.1)
**Purpose**: Generate comprehensive analytics and dashboards

**Class**: `AnalyticsService(db: Session)`

**Methods**:

1. `get_overview_stats(username)` → Dict
   - total_documents, total_clusters, total_concepts
   - documents_today, this_week, this_month
   - Uses SQLAlchemy aggregation

2. `get_time_series_data(days, username)` → Dict
   - Daily document counts for past N days
   - Fills missing dates with 0
   - Returns labels[], data[]

3. `get_cluster_distribution(username)` → Dict
   - Top 10 clusters by document count
   - Bar chart ready (labels, data)

4. `get_skill_level_distribution(username)` → Dict
   - Documents grouped by skill level
   - beginner, intermediate, advanced, unknown

5. `get_source_type_distribution(username)` → Dict
   - Documents grouped by source type
   - youtube, pdf, text, url, audio, image

6. `get_top_concepts(limit, username)` → List[Dict]
   - Most frequently occurring concepts
   - Returns concept + occurrence count

7. `get_recent_activity(limit, username)` → List[Dict]
   - Recent document additions
   - Returns doc_id, source_type, skill_level, cluster_id, created_at

8. `get_complete_analytics(username, time_period_days)` → Dict
   - All of above in single call
   - Used by dashboard

**Multi-tenancy**: All methods accept optional username to filter by user

**Test Coverage Needs**:
- Aggregation accuracy tests
- Time-series edge cases (gaps, empty periods)
- Distribution calculation tests
- Multi-user filtering tests
- Performance tests on large datasets

---

### 7. API & INITIALIZATION

#### main.py (FastAPI Application - 1243 lines)
**Purpose**: HTTP API server with authentication, file upload, search, generation

**Configuration**:
- STORAGE_PATH, VECTOR_DIM, SECRET_KEY, TOKEN_EXPIRE_MINUTES, ALLOWED_ORIGINS
- File upload limit: 50MB max
- Rate limiting: 3-5 req/min per endpoint

**Middleware**:
- CORS middleware (configurable origins)
- Request ID middleware (tracing)
- Rate limiting (slowapi)

**Authentication**:
- Custom JWT tokens (HMAC-SHA256 signature)
- Password hashing (PBKDF2)
- OAuth2 bearer scheme

**API Endpoints** (19 total):

**Auth** (3):
- `POST /users` - Register user (rate limit: 3/min)
- `POST /token` - Login (rate limit: 5/min)
- `GET /me` - Get current user info

**Upload** (4):
- `POST /upload_text` - Ingest raw text
- `POST /upload` - Upload from URL
- `POST /upload_file` - Upload file bytes
- `POST /upload_image` - Upload image with OCR

**Search & Retrieval** (4):
- `GET /clusters` - List all clusters
- `GET /search_full` - Semantic search
- `GET /documents/{doc_id}` - Retrieve document
- `DELETE /documents/{doc_id}` - Delete document

**AI Generation** (3):
- `POST /what_can_i_build` - Build suggestions
- `POST /generate` - RAG content generation
- `PUT /documents/{doc_id}/metadata` - Update metadata

**Cluster Management** (2):
- `PUT /clusters/{cluster_id}` - Update cluster
- `GET /export/cluster/{cluster_id}` - Export as JSON

**Export & Admin** (2):
- `GET /export/all` - Export all data
- `GET /health` - Health check + DB status
- `GET /analytics` - Analytics dashboard

**Startup Flow**:
1. Initialize database (create_all)
2. Try load from database
3. Fallback to file storage if DB fails
4. Create default test user (test/test123) if none exist
5. Mount static frontend files

**Error Handling**:
- HTTP 400/401/404/429 for client errors
- HTTP 500 for server errors
- Rate limit responses (429)

**Test Coverage Needs**:
- Auth flow tests (register, login, token refresh)
- Upload endpoint tests (each type)
- Search endpoint tests
- AI generation tests
- Concurrent request tests
- Rate limiting tests
- CORS tests
- Static file serving tests

#### dependencies.py (Dependency Injection)
**Purpose**: Factory functions for service singletons

**Singletons** (using @lru_cache):
- `get_repository()` - KnowledgeBankRepository
- `get_llm_provider()` - OpenAIProvider
- `get_concept_extractor()` - ConceptExtractor
- `get_build_suggester()` - BuildSuggester

**Services** (new instance per request):
- `get_document_service()` - DocumentService
- `get_search_service()` - SearchService
- `get_cluster_service()` - ClusterService
- `get_build_suggestion_service()` - BuildSuggestionService

**Purpose**: Ensures single LLM/repository instances while allowing fresh service instances

**Test Coverage Needs**:
- Singleton creation tests
- Service injection tests
- Configuration loading tests

---

## Critical Business Logic Modules

The following modules contain critical business logic that affects data integrity and user experience:

### 1. **db_repository.py** - Database Operations
- All document CRUD operations
- Concept extraction persistence
- Cluster relationships
- Critical for multi-user data isolation

### 2. **services.py** - Service Orchestration
- Document ingestion workflow
- Auto-clustering algorithm
- Search enrichment
- Determines how documents are organized

### 3. **clustering.py** - Document Grouping
- Jaccard similarity algorithm
- Cluster matching logic
- Critical for knowledge organization

### 4. **build_suggester.py** - AI Recommendations
- Knowledge summarization
- Project viability scoring
- Critical for user value proposition

### 5. **vector_store.py** - Semantic Search
- TF-IDF vectorization
- Similarity ranking
- Affects search quality

### 6. **ingest.py** - Content Processing
- Multimodal content extraction
- YouTube transcription
- Critical for content validity

---

## Data Persistence Modules

### Primary: **db_models.py + database.py**
- SQLAlchemy ORM models
- PostgreSQL/SQLite support
- Connection pooling, session management

### Secondary: **storage.py + db_storage_adapter.py**
- JSON file fallback
- Atomic writes for safety
- Migration bridge for backwards compatibility

### Tertiary: **image_processor.py**
- Image file storage (local filesystem)
- OCR text extraction

---

## AI/LLM Integration Modules

### LLM Communication:
- **llm_providers.py** - Provider abstraction (OpenAI, mock)
- **concept_extractor.py** - Concept extraction pipeline
- **build_suggester.py** - Project recommendation pipeline

### Content Generation:
- **ai_generation_real.py** - RAG-based response generation
- **ingest.py** - Transcription (YouTube, audio via OpenAI Whisper)

### Dependencies:
- OpenAI API key (OPENAI_API_KEY env var)
- Optional: yt-dlp, beautifulsoup4, pytesseract, ffmpeg

---

## External Integrations

1. **OpenAI API**
   - Concept extraction (gpt-5-nano)
   - Build suggestions (gpt-5-mini)
   - RAG generation (gpt-4, gpt-4o, gpt-4o-mini)
   - Audio transcription (whisper-1)

2. **YouTube (via yt-dlp)**
   - Video download and audio extraction

3. **Web Content (BeautifulSoup + requests)**
   - Article extraction
   - HTML parsing

4. **Image Processing (PIL + pytesseract + tesseract-ocr)**
   - Image OCR
   - Metadata extraction

5. **PostgreSQL/SQLite (SQLAlchemy)**
   - Primary data persistence
   - Connection pooling, migrations

---

## Test Coverage Assessment

### Well-Tested Areas (Likely):
- Authentication endpoints (simple logic)
- Upload endpoints (file handling)
- Basic CRUD operations
- Health check endpoint

### Under-Tested Areas (Likely Missing):
- **Vector store**: Search accuracy, filtering edge cases
- **LLM providers**: API error handling, retry logic, JSON parsing
- **Clustering**: Similarity algorithm, edge cases
- **Ingestion**: Each content type, large files, API failures
- **Analytics**: Aggregation correctness, multi-user filtering
- **Database**: Transactions, cascade deletes, query optimization
- **Concurrency**: Race conditions, lock behavior
- **Security**: Path traversal, injection, token validation
- **Integration**: End-to-end workflows, multi-step processes

### Integration Test Gaps:
- Document ingestion → clustering → search workflow
- User creation → upload → search → generate flow
- API rate limiting
- CORS handling
- Token expiration
- Database migration scenarios

