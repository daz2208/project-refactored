# SyncBoard 3.0 - BUILD BLUEPRINT
## Complete System Architecture & Rebuild Plan

**Version:** 1.0
**Date:** 2025-11-14
**Status:** Ground-Up Rebuild Specification

---

## 🎯 EXECUTIVE SUMMARY

**What This System Does:**
SyncBoard 3.0 is an AI-powered knowledge management system that ingests multi-modal content (documents, videos, images, code), extracts concepts using AI, organizes content into clusters, and provides semantic search capabilities.

**Core Value Proposition:**
- Automatically organize any content type into meaningful topic clusters
- AI-powered concept extraction (no manual tagging needed)
- Semantic search across all your knowledge
- Build project suggestions based on what you know
- Track learning progress with analytics

---

## 📋 SYSTEM REQUIREMENTS

### Functional Requirements

**FR-1: Content Ingestion**
- Accept 40+ file types (code, Office docs, PDFs, videos, images, e-books, archives)
- Process YouTube videos with automatic transcription
- Extract text from images via OCR
- Handle web URLs and direct text input
- Batch upload support

**FR-2: AI Concept Extraction**
- Extract 3-10 key concepts per document using LLM
- Categorize concepts (language, framework, concept, tool)
- Assign confidence scores (0.0-1.0)
- Support multiple LLM providers (OpenAI, Anthropic, Ollama)

**FR-3: Automatic Clustering**
- Group related documents using Jaccard similarity
- Assign cluster names based on common concepts
- Support skill levels (beginner, intermediate, advanced)
- Allow manual cluster management

**FR-4: Search & Discovery**
- Full-text search across all documents
- Semantic search using TF-IDF vectors
- Filter by cluster, skill level, source type, date
- Saved searches functionality

**FR-5: User Management**
- JWT-based authentication
- Per-user document isolation
- Rate limiting on all endpoints
- Secure password hashing (bcrypt)

**FR-6: Advanced Features**
- Duplicate detection
- Document tagging system
- Document relationships (prerequisite, related, followup)
- Analytics dashboard (usage stats, trends)
- AI content generation with RAG
- Project build suggestions

### Non-Functional Requirements

**NFR-1: Performance**
- Search response time: < 500ms for 10k documents
- Upload processing: < 30s for typical documents
- Support 100+ concurrent users

**NFR-2: Security**
- OWASP Top 10 compliance
- Input sanitization (SQL injection, XSS, SSRF, path traversal)
- HTTPS enforcement in production
- CORS properly configured
- Security headers (CSP, X-Frame-Options, etc.)

**NFR-3: Scalability**
- Horizontal scaling with load balancer
- Database connection pooling
- Stateless API design
- Docker containerization

**NFR-4: Reliability**
- 99.5% uptime target
- Database backups every 24 hours
- Graceful error handling
- Health check endpoints

**NFR-5: Maintainability**
- 90%+ test coverage
- Clean Architecture pattern
- Comprehensive API documentation
- Deployment via CI/CD pipeline

---

## 🏗️ SYSTEM ARCHITECTURE

### Architecture Pattern: Clean Architecture (Layered)

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                       │
│  ┌──────────────┐              ┌──────────────┐            │
│  │  Frontend    │              │   API Docs   │            │
│  │ (Vanilla JS) │              │  (Swagger)   │            │
│  └──────────────┘              └──────────────┘            │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST
┌───────────────────────▼─────────────────────────────────────┐
│                      API LAYER (FastAPI)                     │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Router Modules (12 routers)                │    │
│  │  - auth         - uploads      - search            │    │
│  │  - documents    - clusters     - analytics         │    │
│  │  - duplicates   - tags         - relationships     │    │
│  │  - saved_searches - ai_generation - build_suggestions  │
│  └────────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                        │ Dependency Injection
┌───────────────────────▼─────────────────────────────────────┐
│                     SERVICE LAYER                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Business Logic Services                             │  │
│  │  - DocumentService      - SearchService              │  │
│  │  - ClusterService       - AnalyticsService           │  │
│  │  - ConceptExtractor     - DuplicateDetector          │  │
│  │  - BuildSuggester       - AIGenerationService        │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   REPOSITORY LAYER                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Data Access Abstraction                             │  │
│  │  - DatabaseRepository (SQLAlchemy ORM)               │  │
│  │  - VectorStore (TF-IDF, in-memory)                   │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                      DATA LAYER                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │ PostgreSQL │  │ File Store │  │  External  │           │
│  │  Database  │  │  (uploads) │  │  APIs      │           │
│  │            │  │            │  │  (OpenAI)  │           │
│  └────────────┘  └────────────┘  └────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- **Framework:** FastAPI 0.104+ (Python 3.11+)
- **Database:** PostgreSQL 14+ (production), SQLite (development)
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic
- **Authentication:** JWT (python-jose), bcrypt for passwords
- **AI/ML:** OpenAI GPT-4o-mini, scikit-learn (TF-IDF)
- **Rate Limiting:** SlowAPI
- **Testing:** pytest, pytest-asyncio

**Frontend:**
- **Core:** Vanilla JavaScript (ES6+)
- **No frameworks** (keep it simple and fast)
- **CSS:** Custom CSS with modern features
- **API Communication:** Fetch API

**Infrastructure:**
- **Containerization:** Docker, Docker Compose
- **CI/CD:** GitHub Actions
- **Process Manager:** Uvicorn (ASGI server)
- **Reverse Proxy:** Nginx (production)

**Content Processing:**
- **PDF:** pypdf
- **Office Docs:** python-docx, openpyxl, python-pptx
- **Video:** yt-dlp, whisper (transcription)
- **Images:** Pillow, pytesseract (OCR)
- **E-books:** ebooklib
- **Archives:** zipfile, tarfile
- **Code:** pygments (syntax highlighting)
- **Jupyter:** nbformat

---

## 📊 DATABASE SCHEMA

### Core Tables

**users**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_username (username)
);
```

**clusters**
```sql
CREATE TABLE clusters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    primary_concepts JSONB NOT NULL,  -- Array of concept names
    skill_level VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_skill_level (skill_level)
);
```

**documents**
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER UNIQUE NOT NULL,  -- Vector store ID
    owner_username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE,
    cluster_id INTEGER REFERENCES clusters(id) ON DELETE SET NULL,

    -- Source info
    source_type VARCHAR(50) NOT NULL,
    source_url VARCHAR(2048),
    filename VARCHAR(512),
    image_path VARCHAR(1024),

    -- Metadata
    content_length INTEGER,
    skill_level VARCHAR(50),

    -- Timestamps
    ingested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    INDEX idx_doc_id (doc_id),
    INDEX idx_owner (owner_username),
    INDEX idx_cluster (cluster_id),
    INDEX idx_source_type (source_type),
    INDEX idx_skill_level (skill_level),
    INDEX idx_ingested_at (ingested_at)
);
```

**concepts**
```sql
CREATE TABLE concepts (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50),  -- language, framework, concept, tool
    confidence FLOAT,

    INDEX idx_document (document_id),
    INDEX idx_name (name),
    INDEX idx_category (category)
);
```

**vector_documents**
```sql
CREATE TABLE vector_documents (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER UNIQUE NOT NULL,
    content TEXT NOT NULL,  -- Full document text

    INDEX idx_doc_id (doc_id)
);
```

### Advanced Feature Tables

**tags**
```sql
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    color VARCHAR(7),  -- Hex color code
    owner_username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_name (name),
    INDEX idx_owner (owner_username)
);
```

**document_tags**
```sql
CREATE TABLE document_tags (
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (document_id, tag_id),
    INDEX idx_document (document_id),
    INDEX idx_tag (tag_id)
);
```

**document_relationships**
```sql
CREATE TABLE document_relationships (
    id SERIAL PRIMARY KEY,
    source_doc_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    target_doc_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,  -- prerequisite, related, followup
    strength FLOAT,  -- 0.0-1.0
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_source (source_doc_id),
    INDEX idx_target (target_doc_id),
    INDEX idx_type (relationship_type),
    UNIQUE (source_doc_id, target_doc_id, relationship_type)
);
```

**saved_searches**
```sql
CREATE TABLE saved_searches (
    id SERIAL PRIMARY KEY,
    owner_username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    query TEXT NOT NULL,
    filters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP,

    INDEX idx_owner (owner_username)
);
```

---

## 🔌 API DESIGN

### REST Endpoints (38 Total)

#### Authentication (3 endpoints)
```
POST   /users              Register new user
POST   /token              Login (get JWT token)
GET    /users/me           Get current user info
```

#### Content Upload (5 endpoints)
```
POST   /upload_text        Upload plain text
POST   /upload_url         Upload from URL
POST   /upload_file        Upload document file
POST   /upload_image       Upload image (with OCR)
POST   /upload             YouTube URL upload
```

#### Search (1 endpoint)
```
GET    /search_full        Search with filters
    Query params:
    - q: search query (required)
    - cluster_id: filter by cluster
    - skill_level: filter by skill level
    - source_type: filter by source type
    - start_date, end_date: date range
```

#### Documents (6 endpoints)
```
GET    /documents/{id}                     Get document
DELETE /documents/{id}                     Delete document
PUT    /documents/{id}/metadata            Update metadata
GET    /documents/{id}/tags                Get document tags
POST   /documents/{id}/tags/{tag_id}       Add tag to document
DELETE /documents/{id}/tags/{tag_id}       Remove tag from document
```

#### Clusters (2 endpoints)
```
GET    /clusters                   List all clusters
PUT    /clusters/{id}              Update cluster name
```

#### Export (2 endpoints)
```
GET    /export/cluster/{id}        Export cluster (JSON/Markdown)
GET    /export/all                 Export all data
```

#### Analytics (1 endpoint)
```
GET    /analytics                  Get dashboard stats
    Query params:
    - period: day, week, month, all
```

#### AI Features (2 endpoints)
```
POST   /generate                   Generate content with RAG
POST   /what_can_i_build           Get project suggestions
```

#### Duplicates (3 endpoints)
```
GET    /duplicates                         Find duplicate docs
GET    /duplicates/{id1}/{id2}             Compare two docs
POST   /duplicates/merge                   Merge duplicates
```

#### Tags (3 endpoints)
```
POST   /tags                       Create tag
GET    /tags                       List all tags
DELETE /tags/{id}                  Delete tag
```

#### Saved Searches (4 endpoints)
```
POST   /saved-searches             Save search
GET    /saved-searches             List saved searches
DELETE /saved-searches/{id}        Delete saved search
POST   /saved-searches/{id}/use    Execute saved search
```

#### Relationships (2 endpoints)
```
POST   /documents/{source_id}/relationships        Create relationship
DELETE /documents/{source_id}/relationships/{target_id}  Delete relationship
GET    /documents/{id}/relationships               Get relationships
```

#### System (1 endpoint)
```
GET    /health                     Health check
```

---

## 🔐 SECURITY ARCHITECTURE

### Authentication & Authorization

**JWT Token Structure:**
```json
{
  "sub": "username",
  "exp": 1234567890,
  "type": "access"
}
```

**Token Flow:**
1. User registers: `POST /users` → User created
2. User logs in: `POST /token` → JWT token returned
3. User accesses protected endpoint: `Authorization: Bearer <token>`
4. Token validated on every request

**Password Security:**
- Use bcrypt (cost factor: 12)
- Never store plain text passwords
- Minimum length: 8 characters
- No maximum length (bcrypt handles hashing)

### Input Validation & Sanitization

**Validation Rules (sanitization.py):**

1. **SQL Injection Prevention**
   - Never use raw SQL strings
   - Always use SQLAlchemy ORM
   - Parameterized queries only

2. **XSS Prevention**
   - HTML escape all user inputs in responses
   - Content-Security-Policy headers
   - No inline JavaScript in responses

3. **SSRF Prevention**
   - Whitelist allowed URL schemes (http, https)
   - Block private IP ranges (127.0.0.0/8, 10.0.0.0/8, 192.168.0.0/16)
   - Timeout on external requests (30s max)

4. **Path Traversal Prevention**
   - Validate all file paths
   - Block ".." sequences
   - Use absolute paths only
   - Restrict to designated upload directory

5. **Command Injection Prevention**
   - Never use shell=True in subprocess
   - Whitelist allowed commands
   - Validate all parameters

**Rate Limiting:**
```python
/token        → 5 requests/minute    # Login
/users        → 3 requests/minute    # Registration
/upload_*     → 10 requests/minute   # Uploads
/search_full  → 50 requests/minute   # Search
/generate     → 5 requests/minute    # AI generation
```

### Security Headers

```python
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

### CORS Configuration

**Development:**
```python
ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8000"]
```

**Production:**
```python
ALLOWED_ORIGINS = ["https://yourdomain.com"]
# NEVER use "*" in production
```

---

## 🧪 TESTING STRATEGY

### Test Coverage Targets

- **Unit Tests:** 90% coverage
- **Integration Tests:** 80% coverage
- **E2E Tests:** Critical paths only
- **Overall Target:** 85%+ coverage

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_auth.py
│   ├── test_sanitization.py
│   ├── test_concept_extractor.py
│   ├── test_clustering.py
│   ├── test_vector_store.py
│   └── test_services.py
├── integration/
│   ├── test_db_repository.py
│   ├── test_api_endpoints.py
│   ├── test_security.py
│   └── test_analytics.py
└── e2e/
    ├── test_ingestion_flow.py
    ├── test_search_flow.py
    └── test_user_workflow.py
```

### Pytest Fixtures (conftest.py)

```python
@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def auth_headers(test_client):
    """Authenticated request headers."""
    # Register and login test user
    test_client.post("/users", json={
        "username": "testuser",
        "password": "testpass123"
    })
    response = test_client.post("/token", data={
        "username": "testuser",
        "password": "testpass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def cleanup_test_state():
    """Clean up global state after each test."""
    yield
    # Clear any global caches, singletons, etc.
```

### Test Naming Convention

```python
# Pattern: test_<function>_<scenario>_<expected_result>

def test_upload_text_valid_content_returns_document_id():
    """Upload valid text should return document ID."""

def test_upload_text_empty_content_returns_400():
    """Upload empty text should return 400 error."""

def test_search_with_filters_returns_filtered_results():
    """Search with cluster filter should return only matching docs."""
```

### Mock External Dependencies

```python
# Mock OpenAI API calls
@patch('backend.concept_extractor.openai.ChatCompletion.create')
def test_concept_extraction(mock_openai):
    mock_openai.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "concepts": [
                        {"name": "Python", "category": "language", "confidence": 0.9}
                    ]
                })
            }
        }]
    }
    # Test logic here
```

---

## 🚀 DEPLOYMENT ARCHITECTURE

### Docker Containers

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://syncboard:syncboard@db:5432/syncboard
      - SYNCBOARD_SECRET_KEY=${SYNCBOARD_SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped

  db:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=syncboard
      - POSTGRES_USER=syncboard
      - POSTGRES_PASSWORD=syncboard
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

### CI/CD Pipeline (GitHub Actions)

**.github/workflows/ci-cd.yml:**
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=backend --cov-report=xml
      - uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install flake8 black
      - run: flake8 backend/
      - run: black --check backend/

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install bandit safety
      - run: bandit -r backend/
      - run: safety check

  deploy:
    needs: [test, lint, security]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: docker build -t syncboard:latest .
      - run: docker push syncboard:latest
      # Deploy to your hosting platform
```

### Environment Variables

**Production .env file:**
```bash
# Security (REQUIRED)
SYNCBOARD_SECRET_KEY=<generate-with-openssl-rand-hex-32>
SYNCBOARD_ALLOWED_ORIGINS=https://yourdomain.com

# Database (REQUIRED)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# AI Services (REQUIRED)
OPENAI_API_KEY=sk-your-actual-key-here

# Optional LLM Providers
ANTHROPIC_API_KEY=sk-ant-your-key
OLLAMA_BASE_URL=http://localhost:11434

# Application Settings
SYNCBOARD_ENVIRONMENT=production
SYNCBOARD_LOG_LEVEL=INFO

# File Upload Limits
MAX_UPLOAD_SIZE=50MB
UPLOAD_DIR=/app/uploads
```

---

## 📁 PROJECT STRUCTURE

```
syncboard-v3/
├── .github/
│   └── workflows/
│       └── ci-cd.yml                 # CI/CD pipeline
│
├── backend/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app initialization (300 lines MAX)
│   │
│   ├── routers/                      # API endpoints (modular)
│   │   ├── __init__.py
│   │   ├── auth.py                   # /users, /token
│   │   ├── uploads.py                # /upload_*
│   │   ├── search.py                 # /search_full
│   │   ├── documents.py              # /documents/*
│   │   ├── clusters.py               # /clusters/*
│   │   ├── analytics.py              # /analytics
│   │   ├── ai_generation.py          # /generate, /what_can_i_build
│   │   ├── duplicates.py             # /duplicates/*
│   │   ├── tags.py                   # /tags/*
│   │   ├── saved_searches.py         # /saved-searches/*
│   │   └── relationships.py          # /documents/*/relationships
│   │
│   ├── services/                     # Business logic
│   │   ├── __init__.py
│   │   ├── document_service.py       # Document operations
│   │   ├── search_service.py         # Search logic
│   │   ├── cluster_service.py        # Clustering algorithms
│   │   ├── analytics_service.py      # Statistics & metrics
│   │   ├── concept_extractor.py      # LLM concept extraction
│   │   ├── duplicate_detector.py     # Duplicate detection
│   │   └── build_suggester.py        # Project suggestions
│   │
│   ├── repositories/                 # Data access layer
│   │   ├── __init__.py
│   │   ├── database_repository.py    # Main repository (SQLAlchemy)
│   │   └── vector_store.py           # TF-IDF vector store
│   │
│   ├── models/                       # Data models
│   │   ├── __init__.py
│   │   ├── pydantic_models.py        # API validation models
│   │   └── db_models.py              # SQLAlchemy ORM models
│   │
│   ├── core/                         # Core utilities
│   │   ├── __init__.py
│   │   ├── auth.py                   # JWT, password hashing
│   │   ├── database.py               # DB connection, sessions
│   │   ├── config.py                 # Configuration management
│   │   ├── dependencies.py           # FastAPI dependencies
│   │   ├── security.py               # Security middleware
│   │   └── sanitization.py           # Input validation
│   │
│   ├── ingest/                       # Content processing
│   │   ├── __init__.py
│   │   ├── text_processor.py         # Text, URLs
│   │   ├── file_processor.py         # PDFs, Office docs
│   │   ├── media_processor.py        # Images, videos
│   │   ├── code_processor.py         # Source code, Jupyter
│   │   └── archive_processor.py      # ZIP, TAR, e-books
│   │
│   └── static/                       # Frontend files
│       ├── index.html
│       ├── app.js
│       └── styles.css
│
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── unit/
│   │   ├── test_auth.py
│   │   ├── test_sanitization.py
│   │   ├── test_concept_extractor.py
│   │   ├── test_clustering.py
│   │   └── test_vector_store.py
│   ├── integration/
│   │   ├── test_db_repository.py
│   │   ├── test_api_endpoints.py
│   │   └── test_security.py
│   └── e2e/
│       └── test_workflows.py
│
├── alembic/                          # Database migrations
│   ├── versions/
│   └── env.py
│
├── docs/                             # Documentation
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
│
├── scripts/                          # Utility scripts
│   ├── init_db.py
│   └── backup_db.sh
│
├── .env.example                      # Environment template
├── .gitignore
├── alembic.ini                       # Alembic config
├── docker-compose.yml                # Local development
├── Dockerfile                        # Container definition
├── pytest.ini                        # Pytest configuration
├── requirements.txt                  # Python dependencies
├── README.md                         # Project overview
└── BUILD_BLUEPRINT.md               # This document
```

---

## 🔨 PHASE-BY-PHASE REBUILD PLAN

### Phase 1: Foundation (Week 1)

**Objective:** Set up core infrastructure and basic functionality

**Tasks:**
1. ✅ Initialize project structure
2. ✅ Set up FastAPI app with basic configuration
3. ✅ Implement database models (users, documents, clusters, concepts)
4. ✅ Set up Alembic migrations
5. ✅ Implement JWT authentication (register, login)
6. ✅ Write tests for auth (10 tests minimum)
7. ✅ Set up Docker Compose with PostgreSQL

**Deliverables:**
- Users can register and log in
- Database schema created
- 10+ passing tests
- Docker environment works

**Success Criteria:**
```bash
pytest tests/unit/test_auth.py -v
# 10 passed

docker-compose up
# Services start successfully
```

---

### Phase 2: Content Ingestion (Week 2)

**Objective:** Implement multi-modal content ingestion

**Tasks:**
1. ✅ Implement text upload endpoint
2. ✅ Implement URL scraping (BeautifulSoup)
3. ✅ Implement file upload (PDF, Word, Excel)
4. ✅ Implement image upload with OCR
5. ✅ Implement YouTube transcription
6. ✅ Add input sanitization (security)
7. ✅ Write tests for all ingestion types (20 tests)

**Deliverables:**
- All 5 upload endpoints working
- Security validation on all inputs
- 20+ passing tests

**Success Criteria:**
```bash
curl -X POST http://localhost:8000/upload_text \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"content": "Test document"}'
# Returns: {"doc_id": 0, "status": "success"}

pytest tests/unit/test_ingest.py -v
# 20 passed
```

---

### Phase 3: AI Concept Extraction (Week 3)

**Objective:** Implement LLM-powered concept extraction

**Tasks:**
1. ✅ Implement ConceptExtractor service
2. ✅ Integrate OpenAI GPT-4o-mini
3. ✅ Add LLM provider abstraction (OpenAI, Anthropic, Ollama)
4. ✅ Implement concept storage in database
5. ✅ Add retry logic and error handling
6. ✅ Write tests with mocked LLM calls (15 tests)

**Deliverables:**
- Concept extraction working for all content types
- Multi-provider support
- 15+ passing tests (with mocks)

**Success Criteria:**
```bash
# Upload should extract concepts automatically
curl -X POST http://localhost:8000/upload_text \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"content": "Python is a programming language"}'

# Returns:
{
  "doc_id": 0,
  "concepts": [
    {"name": "Python", "category": "language", "confidence": 0.95},
    {"name": "Programming", "category": "concept", "confidence": 0.85}
  ]
}

pytest tests/unit/test_concept_extractor.py -v
# 15 passed
```

---

### Phase 4: Clustering & Search (Week 4)

**Objective:** Implement automatic clustering and semantic search

**Tasks:**
1. ✅ Implement Jaccard similarity clustering
2. ✅ Implement TF-IDF vector store
3. ✅ Add automatic cluster creation
4. ✅ Implement search endpoint with filters
5. ✅ Add cluster management endpoints
6. ✅ Write tests for clustering and search (25 tests)

**Deliverables:**
- Automatic clustering working
- Semantic search with filters
- 25+ passing tests

**Success Criteria:**
```bash
# Search should return relevant results
curl "http://localhost:8000/search_full?q=python&cluster_id=1" \
  -H "Authorization: Bearer $TOKEN"

# Returns ranked, filtered results

pytest tests/unit/test_clustering.py tests/unit/test_vector_store.py -v
# 25 passed
```

---

### Phase 5: Advanced Features (Week 5)

**Objective:** Implement Phase 7.2-7.5 features

**Tasks:**
1. ✅ Implement duplicate detection
2. ✅ Implement tagging system
3. ✅ Implement saved searches
4. ✅ Implement document relationships
5. ✅ Write tests for advanced features (20 tests)

**Deliverables:**
- All 4 advanced features working
- 20+ passing tests

**Success Criteria:**
```bash
# Duplicate detection works
curl "http://localhost:8000/duplicates?threshold=0.85" \
  -H "Authorization: Bearer $TOKEN"
# Returns list of potential duplicates

pytest tests/integration/test_advanced_features.py -v
# 20 passed
```

---

### Phase 6: Analytics & AI Generation (Week 6)

**Objective:** Add analytics dashboard and AI generation

**Tasks:**
1. ✅ Implement AnalyticsService
2. ✅ Add analytics endpoint (stats, trends, distributions)
3. ✅ Implement AI content generation with RAG
4. ✅ Implement build suggestion service
5. ✅ Write tests for analytics and AI (15 tests)

**Deliverables:**
- Analytics dashboard data available
- AI generation working with context
- 15+ passing tests

**Success Criteria:**
```bash
# Analytics returns dashboard data
curl "http://localhost:8000/analytics?period=month" \
  -H "Authorization: Bearer $TOKEN"

# Returns:
{
  "total_documents": 150,
  "clusters": 12,
  "recent_uploads": [...]
}

pytest tests/integration/test_analytics.py -v
# 15 passed
```

---

### Phase 7: Frontend (Week 7)

**Objective:** Build complete frontend UI

**Tasks:**
1. ✅ Create login/register page
2. ✅ Create upload interface (all 5 types)
3. ✅ Create search interface with filters
4. ✅ Create document viewer
5. ✅ Create cluster explorer
6. ✅ Create analytics dashboard
7. ✅ Add error handling and loading states

**Deliverables:**
- Complete working frontend
- All features accessible via UI
- Responsive design

**Success Criteria:**
```bash
# Open browser to http://localhost:8000
# Can perform full workflow:
# 1. Register/Login
# 2. Upload content
# 3. Search and filter
# 4. View analytics
# All without errors
```

---

### Phase 8: Security Hardening (Week 8)

**Objective:** Implement comprehensive security measures

**Tasks:**
1. ✅ Implement all input sanitization (SQL, XSS, SSRF, path traversal)
2. ✅ Add rate limiting to all endpoints
3. ✅ Implement security headers
4. ✅ Add CORS configuration
5. ✅ Implement HTTPS enforcement
6. ✅ Write comprehensive security tests (30 tests)

**Deliverables:**
- OWASP Top 10 compliance
- 30+ passing security tests

**Success Criteria:**
```bash
pytest tests/integration/test_security.py -v
# 30 passed

# Security scan passes
bandit -r backend/
# No high-severity issues
```

---

### Phase 9: Performance & Optimization (Week 9)

**Objective:** Optimize for performance and scalability

**Tasks:**
1. ✅ Add database connection pooling
2. ✅ Implement caching for concept extraction
3. ✅ Optimize search queries (indexes, pagination)
4. ✅ Add lazy loading for large result sets
5. ✅ Profile and optimize slow endpoints
6. ✅ Write performance tests

**Deliverables:**
- Search < 500ms for 10k documents
- Upload processing < 30s
- Database queries optimized

**Success Criteria:**
```bash
# Load test passes
locust -f tests/performance/locustfile.py --headless \
  --users 100 --spawn-rate 10 -t 60s

# 95th percentile response time < 1s
```

---

### Phase 10: Production Deployment (Week 10)

**Objective:** Deploy to production with CI/CD

**Tasks:**
1. ✅ Set up GitHub Actions CI/CD pipeline
2. ✅ Configure production environment
3. ✅ Set up monitoring (health checks, logs)
4. ✅ Implement automated backups
5. ✅ Write deployment documentation
6. ✅ Perform production smoke tests

**Deliverables:**
- Application deployed and accessible
- CI/CD pipeline working
- Monitoring and backups configured

**Success Criteria:**
```bash
# CI/CD pipeline passes
git push origin main
# GitHub Actions: All checks passed ✓

# Production health check passes
curl https://syncboard.yourdomain.com/health
# {"status": "healthy", "database_connected": true}

# Uptime > 99%
```

---

## 📊 SUCCESS METRICS

### Development Metrics

**Code Quality:**
- Test coverage: > 85%
- Linting: 0 errors (flake8, black)
- Security scan: 0 high-severity issues (bandit)
- Type hints: > 80% coverage

**Performance:**
- API response time (95th percentile): < 1s
- Search response time: < 500ms
- Upload processing: < 30s per file
- Database query time: < 100ms

**Reliability:**
- Test pass rate: > 95%
- CI/CD success rate: > 90%
- Uptime: > 99.5%

### User Metrics

**Adoption:**
- Active users: Track daily/monthly active users
- Documents uploaded: Track growth rate
- Search queries: Track engagement

**Satisfaction:**
- Upload success rate: > 95%
- Search relevance: User feedback
- Error rate: < 1% of requests

---

## 🚨 CRITICAL SUCCESS FACTORS

### Must-Haves (Non-Negotiable)

1. **Security First**
   - All inputs sanitized
   - Authentication on all protected endpoints
   - No secrets in code (environment variables only)
   - HTTPS in production

2. **Test Coverage**
   - Minimum 85% code coverage
   - All critical paths tested
   - Tests run on every commit

3. **Clean Architecture**
   - Layered design (API → Service → Repository → Data)
   - No business logic in routers
   - Dependency injection throughout
   - Single Responsibility Principle

4. **Performance**
   - Search < 500ms
   - API calls < 1s (95th percentile)
   - Handle 100 concurrent users

5. **Documentation**
   - API documentation (Swagger)
   - Deployment guide
   - Development setup guide
   - Code comments for complex logic

### Anti-Patterns to Avoid

❌ **Monolithic main.py** (> 500 lines)
✅ Use modular routers (< 300 lines each)

❌ **Business logic in routers**
✅ Put logic in service layer

❌ **Direct database access from routers**
✅ Use repository pattern

❌ **Hardcoded secrets**
✅ Environment variables only

❌ **No tests or < 50% coverage**
✅ Maintain > 85% coverage

❌ **Mixing concerns (file + database storage)**
✅ Single storage backend per deployment

❌ **Skipping input validation**
✅ Validate and sanitize everything

---

## 🔄 DEVELOPMENT WORKFLOW

### Daily Development Cycle

```bash
# 1. Start day: Pull latest changes
git pull origin main

# 2. Create feature branch
git checkout -b feature/add-duplicate-detection

# 3. Write tests first (TDD)
# tests/unit/test_duplicate_detection.py

# 4. Implement feature
# backend/services/duplicate_detector.py

# 5. Run tests locally
pytest tests/ -v
# Ensure > 85% coverage

# 6. Run linting
black backend/
flake8 backend/

# 7. Run security scan
bandit -r backend/

# 8. Commit with clear message
git commit -m "Add duplicate detection service with Jaccard similarity"

# 9. Push and create PR
git push origin feature/add-duplicate-detection

# 10. CI/CD runs automatically
# Wait for checks to pass

# 11. Code review
# Address feedback

# 12. Merge to main
# Automatic deployment to staging
```

### Code Review Checklist

**Functionality:**
- ✅ Feature works as intended
- ✅ Edge cases handled
- ✅ Error handling in place

**Tests:**
- ✅ New code has tests
- ✅ All tests pass
- ✅ Coverage not decreased

**Code Quality:**
- ✅ Follows project structure
- ✅ No code duplication
- ✅ Clear variable names
- ✅ Comments where needed

**Security:**
- ✅ Input validated
- ✅ No secrets in code
- ✅ SQL injection prevented
- ✅ XSS prevented

**Performance:**
- ✅ No N+1 queries
- ✅ Efficient algorithms
- ✅ Indexes on database queries

---

## 🎓 KEY LEARNINGS FROM PREVIOUS ATTEMPTS

### What Went Wrong Before

1. **Incremental git pushes caused sync issues**
   - Multiple pushes with incomplete features
   - Confusion about what's actually on GitHub
   - Missing dependencies between commits

2. **Mixed storage backends**
   - Both file storage and database active
   - Tests written for wrong storage type
   - Hard to maintain consistency

3. **Datetime handling inconsistencies**
   - Mixed string and datetime object usage
   - SQLAlchemy 2.0 compatibility issues
   - Test fixtures using wrong types

4. **Monolithic architecture attempts**
   - main.py grew to 1,325 lines
   - Hard to maintain and test
   - Difficult to understand

5. **Test suite rot**
   - Tests not kept up to date with code changes
   - 74% pass rate not acceptable
   - Some tests testing wrong implementation

### What To Do Differently

1. **Complete features before pushing**
   - Finish entire feature + tests
   - Verify everything works
   - ONE commit per complete feature

2. **Pick ONE storage backend**
   - Database only (no file storage fallback)
   - Remove legacy code completely
   - All tests use same storage

3. **Strict type consistency**
   - datetime objects in Python
   - ISO strings only for JSON API
   - Clear conversion at boundaries

4. **Enforce architecture from day 1**
   - Router files < 300 lines each
   - Service layer mandatory
   - No shortcuts

5. **Test suite health is critical**
   - Maintain > 95% pass rate always
   - Fix broken tests immediately
   - Delete obsolete tests

---

## 📚 REFERENCE DOCUMENTATION

### Essential Reading

**FastAPI:**
- https://fastapi.tiangolo.com/
- https://fastapi.tiangolo.com/tutorial/dependencies/

**SQLAlchemy 2.0:**
- https://docs.sqlalchemy.org/en/20/
- https://docs.sqlalchemy.org/en/20/orm/quickstart.html

**Pydantic V2:**
- https://docs.pydantic.dev/latest/
- https://docs.pydantic.dev/latest/migration/

**Testing:**
- https://docs.pytest.org/
- https://fastapi.tiangolo.com/tutorial/testing/

**Security:**
- https://owasp.org/www-project-top-ten/
- https://cheatsheetseries.owasp.org/

### Code Examples

**Clean Router Example:**
```python
# backend/routers/documents.py

from fastapi import APIRouter, Depends, HTTPException
from backend.core.dependencies import get_current_user, get_document_service
from backend.models.pydantic_models import Document

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    current_user: str = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
) -> Document:
    """Get document by ID."""
    doc = await doc_service.get_document(doc_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
```

**Clean Service Example:**
```python
# backend/services/document_service.py

class DocumentService:
    def __init__(self, repository: DatabaseRepository):
        self.repo = repository

    async def get_document(self, doc_id: int, user: str) -> Optional[Document]:
        """Get document if user owns it."""
        doc = await self.repo.get_document(doc_id)
        if doc and doc.owner == user:
            return doc
        return None
```

**Clean Repository Example:**
```python
# backend/repositories/database_repository.py

class DatabaseRepository:
    def __init__(self, db: Session):
        self.db = db

    async def get_document(self, doc_id: int) -> Optional[DBDocument]:
        """Get document from database."""
        return self.db.query(DBDocument).filter_by(doc_id=doc_id).first()
```

---

## ✅ FINAL CHECKLIST

### Before Starting Rebuild

- [ ] Read this entire blueprint document
- [ ] Understand the architecture pattern
- [ ] Set up development environment
- [ ] Install all dependencies
- [ ] Create .env file with required variables

### Phase Completion Checklist

Use this for EACH phase:

- [ ] All tasks in phase completed
- [ ] Tests written and passing (> 95%)
- [ ] Code linted (black, flake8)
- [ ] Security scan passed (bandit)
- [ ] Documentation updated
- [ ] Feature demonstrated working
- [ ] Code reviewed
- [ ] ONE commit pushed to git
- [ ] Phase report written

### Production Readiness Checklist

Before deploying to production:

- [ ] All 10 phases complete
- [ ] Test coverage > 85%
- [ ] All tests passing (> 95%)
- [ ] Security audit passed
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] CI/CD pipeline working
- [ ] Monitoring configured
- [ ] Backups configured
- [ ] Production environment variables set
- [ ] SSL certificates configured
- [ ] Domain configured
- [ ] Smoke tests passed in production

---

## 🎯 CONCLUSION

This blueprint provides a complete, step-by-step plan to build SyncBoard 3.0 correctly from the ground up. Key principles:

1. **Clean Architecture** - Layered design, clear separation of concerns
2. **Security First** - OWASP Top 10 compliance, comprehensive validation
3. **Test-Driven** - 85%+ coverage, tests written first
4. **Modular Design** - Small, focused files (< 300 lines)
5. **Phase-by-Phase** - Complete one phase before starting next
6. **One Storage Backend** - Database only, no mixed approaches
7. **Performance** - < 500ms search, < 1s API responses
8. **Production Ready** - Docker, CI/CD, monitoring from day 1

**Estimated Timeline:** 10 weeks (full-time development)

**Estimated Effort:**
- Development: 300 hours
- Testing: 100 hours
- Documentation: 40 hours
- **Total: 440 hours**

**Success Criteria:**
- ✅ All 289 tests passing (> 95%)
- ✅ 85%+ code coverage
- ✅ All 38 endpoints working
- ✅ < 500ms search performance
- ✅ Production deployment successful
- ✅ Zero high-severity security issues

---

**This blueprint is the COMPLETE guide to rebuilding SyncBoard 3.0 the right way. Follow it step-by-step, don't skip phases, and you'll have a production-ready, maintainable, secure system.**

**Document Version:** 1.0
**Last Updated:** 2025-11-14
**Status:** Ready for Implementation
