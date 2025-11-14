# CLAUDE.md - AI Assistant Guide for SyncBoard 3.0 Knowledge Bank

**Last Updated:** 2025-11-14
**Project Status:** Production-Ready (Phase 7.1 Complete)
**Repository:** daz2208/project-refactored

---

## 🎯 Project Overview

SyncBoard 3.0 is a **production-grade, AI-powered knowledge management system** built with FastAPI (backend) and Vanilla JavaScript (frontend). It automatically organizes, clusters, and searches documents using OpenAI-powered concept extraction and TF-IDF semantic search.

**Key Capabilities:**
- Multi-modal content ingestion (40+ file types: code, notebooks, Office files, PDFs, videos, images, e-books, archives)
- AI-powered concept extraction and auto-clustering
- Advanced semantic search with filters
- JWT authentication with rate limiting
- PostgreSQL database with SQLAlchemy ORM
- Comprehensive analytics dashboard
- Docker containerization with CI/CD pipeline

**Tech Stack:**
- **Backend:** FastAPI, PostgreSQL, SQLAlchemy, OpenAI GPT-4o-mini, scikit-learn, JWT
- **Frontend:** Vanilla JavaScript, Custom CSS (no frameworks)
- **Infrastructure:** Docker, Docker Compose, Alembic migrations, GitHub Actions CI/CD

---

## 📁 Codebase Structure

### High-Level Directory Layout

```
project-refactored/
├── .github/workflows/ci-cd.yml    # CI/CD pipeline
├── refactored/
│   ├── app.js                     # Frontend (root level copy)
│   ├── index.html                 # Frontend HTML (root level copy)
│   └── syncboard_backend/         # Main application directory
│       ├── backend/               # Backend Python code
│       │   ├── main.py            # FastAPI app entry (276 lines, refactored from 1,325)
│       │   ├── routers/           # API endpoints (7 modules)
│       │   ├── *.py               # Services, repositories, models
│       │   └── static/            # Frontend files (served by FastAPI)
│       ├── tests/                 # Test suite (12 modules, 116 tests)
│       ├── alembic/               # Database migrations
│       ├── scripts/               # Utility scripts
│       ├── requirements.txt       # Python dependencies
│       ├── Dockerfile             # Container definition
│       ├── docker-compose.yml     # Service orchestration
│       └── .env.example           # Environment template
└── *.md                           # Documentation (25 files)
```

### Backend Architecture (Clean Architecture Pattern)

```
┌─────────────────────────────────────────┐
│   Frontend (Vanilla JS)                 │
│   - backend/static/app.js (36 KB)       │
│   - backend/static/index.html (17 KB)   │
└───────────────┬─────────────────────────┘
                │ HTTP/REST API
┌───────────────▼─────────────────────────┐
│   API Layer (main.py + routers/)        │
│   - auth.py          (authentication)   │
│   - uploads.py       (14.8 KB)          │
│   - search.py        (6.5 KB)           │
│   - documents.py     (6 KB)             │
│   - clusters.py      (8.4 KB)           │
│   - build_suggestions.py                │
│   - analytics.py                        │
│   - ai_generation.py                    │
└───────────────┬─────────────────────────┘
                │ Dependency Injection
┌───────────────▼─────────────────────────┐
│   Service Layer                          │
│   - services.py (10.6 KB)               │
│   - analytics_service.py (9.7 KB)       │
│   - concept_extractor.py (AI)           │
│   - clustering.py (Jaccard similarity)  │
│   - build_suggester.py (AI projects)    │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│   Repository Layer                      │
│   - db_repository.py (330 lines)        │
│   - repository.py (305 lines, legacy)   │
│   - db_storage_adapter.py (adapter)     │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│   Data Layer                            │
│   - PostgreSQL (production)             │
│   - SQLite (development/testing)        │
│   - File storage (legacy fallback)      │
│   - Vector store (TF-IDF, in-memory)    │
└─────────────────────────────────────────┘
```

### Key Files by Purpose

**Core Application:**
- `backend/main.py` (276 lines) - FastAPI app initialization, middleware, router mounting
- `backend/dependencies.py` - Dependency injection setup, singleton instances
- `backend/constants.py` - Application constants and configuration

**Data Models (3 Layers):**
1. **Pydantic** (`backend/models.py`) - API request/response validation
2. **SQLAlchemy** (`backend/db_models.py`) - Database ORM models
3. **Storage** - Legacy file-based format

**Routers (Organized by Feature):**
- `routers/auth.py` - User registration, login, JWT tokens
- `routers/uploads.py` (14.8 KB) - Text, URL, file, image, YouTube uploads
- `routers/search.py` - Full-text + semantic search with filters
- `routers/documents.py` - CRUD operations for documents
- `routers/clusters.py` - Cluster management, export (JSON/Markdown)
- `routers/build_suggestions.py` - AI-powered project suggestions
- `routers/analytics.py` - Dashboard statistics and trends
- `routers/ai_generation.py` - AI content generation with RAG

**Business Logic:**
- `backend/services.py` - Service layer abstractions
- `backend/analytics_service.py` - Statistics, time-series, distributions
- `backend/concept_extractor.py` - OpenAI-powered concept extraction
- `backend/clustering.py` - Automatic topic clustering (Jaccard similarity)
- `backend/build_suggester.py` - AI project suggestions
- `backend/image_processor.py` - OCR with Tesseract
- `backend/llm_providers.py` - LLM abstraction layer (OpenAI, Anthropic, Ollama)

**Data Access:**
- `backend/db_repository.py` (330 lines) - PostgreSQL CRUD operations
- `backend/repository.py` (305 lines) - File-based repository (legacy)
- `backend/db_storage_adapter.py` - Adapter pattern for dual storage
- `backend/storage.py` - JSON file operations (atomic saves)
- `backend/vector_store.py` - TF-IDF semantic search

**Content Ingestion:**
- `backend/ingest.py` (46 KB!) - Multi-modal content processing:
  - **Phase 1:** Jupyter notebooks (.ipynb), 40+ programming languages
  - **Phase 2:** Excel (.xlsx), PowerPoint (.pptx)
  - **Phase 3:** EPUB e-books, subtitle files (SRT/VTT), ZIP archives
  - YouTube videos (Whisper transcription with audio compression)
  - PDFs (pypdf), Word docs (python-docx)
  - Web articles (BeautifulSoup)
  - Images (OCR with Tesseract)

**Security & Infrastructure:**
- `backend/auth.py` - JWT authentication, bcrypt password hashing
- `backend/sanitization.py` (11.6 KB) - Input validation, SQL/XSS/SSRF prevention
- `backend/security_middleware.py` (6.6 KB) - Security headers, HTTPS enforcement
- `backend/database.py` - Database configuration, connection pooling

**Testing (12 modules, 116 tests, 99.1% pass rate):**
- `tests/conftest.py` - Shared fixtures (db_session, cleanup_test_state)
- `tests/test_api_endpoints.py` (850+ lines) - E2E API tests
- `tests/test_services.py` - Service layer tests
- `tests/test_analytics.py` - Analytics calculations
- `tests/test_clustering.py` - Clustering algorithms
- `tests/test_db_repository.py` - Database operations
- `tests/test_vector_store.py` - TF-IDF search
- `tests/test_sanitization.py` (18.3 KB) - Security validation
- `tests/test_security.py` - Security headers
- `tests/test_ingestion_phase*.py` - Content ingestion (3 files)

---

## 🔄 Development Workflow

### Local Development Setup

```bash
# 1. Navigate to backend directory
cd refactored/syncboard_backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key

# 5. Initialize database
python -c "from backend.database import init_db; init_db()"

# 6. Run development server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 7. Access application
# Frontend: http://localhost:8000/
# API docs: http://localhost:8000/docs
```

### Docker Development

```bash
# Start all services (backend + PostgreSQL)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run tests in container
docker-compose exec backend pytest tests/ -v

# Stop services
docker-compose down
```

### Testing Workflow

```bash
# Run all tests
pytest tests/ -v

# Run specific module
pytest tests/test_sanitization.py -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific test
pytest tests/test_api_endpoints.py::test_upload_text -v
```

### Database Migration Workflow

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Git Workflow

**Branch Naming Convention:**
- Feature branches: `claude/description-sessionid`
- Example: `claude/claude-md-mhyvbdgu0nuz7b2o-01VWvrmL13YRvm1RJGVEe8Ye`

**Commit Message Style:**
```
# Good examples (from git history):
- "Add comprehensive end-to-end test report for Phases 1-3"
- "Implement Phase 3: Archives & E-Books support"
- "Refactor main.py into modular router architecture"
- "Add comprehensive input sanitization to prevent injection attacks"
- "CRITICAL SECURITY FIX: Replace vulnerable password hashing and JWT implementation"

# Pattern: Action verb + clear description
# Use "Add", "Implement", "Fix", "Refactor", "Update"
```

**Pull Request Process:**
1. Create feature branch from main
2. Make changes with comprehensive tests
3. Run full test suite: `pytest tests/ -v`
4. Commit with descriptive messages
5. Push to feature branch
6. Create PR with summary and test plan

---

## 🏗️ Architecture Patterns & Conventions

### 1. Clean Architecture Principles

**Always follow the layered approach:**
- API Layer (routers) → Service Layer (services) → Repository Layer → Data Layer
- **NEVER** access database directly from routers
- **ALWAYS** put business logic in services, not endpoints
- **ALWAYS** use dependency injection for testability

### 2. Repository Pattern

```python
# Good: Using repository pattern
class DatabaseKnowledgeBankRepository:
    def get_document(self, doc_id: int) -> Optional[str]:
        """Get document content by ID"""

    def save_document(self, doc_id: int, content: str):
        """Save document content"""

    def delete_document(self, doc_id: int):
        """Delete document"""
```

### 3. Dependency Injection Pattern

```python
# Good: FastAPI dependency injection
from backend.dependencies import get_db, get_current_user

@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Implementation
```

### 4. Service Layer Pattern

```python
# Good: Service encapsulates business logic
class ConceptExtractionService:
    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    async def extract(self, content: str) -> Dict:
        # Business logic here
```

### 5. Adapter Pattern

The codebase uses the Adapter pattern for dual storage support:
```python
# backend/db_storage_adapter.py
# Provides unified interface for both file and database storage
```

### 6. Strategy Pattern

```python
# backend/llm_providers.py
# Abstract LLM provider - supports OpenAI, Anthropic, Ollama
```

---

## 🔐 Security Guidelines

### Critical Security Rules

1. **NEVER commit secrets to git**
   - Use `.env` files (gitignored)
   - Use environment variables for all sensitive data
   - Check `.env.example` for required variables

2. **ALWAYS validate input**
   - Use `backend/sanitization.py` functions
   - Path traversal: `validate_file_path()`
   - SQL injection: Use SQLAlchemy ORM, never raw queries
   - XSS: HTML escape in responses
   - SSRF: `validate_url()`

3. **ALWAYS use authentication**
   - Protected endpoints: `Depends(get_current_user)`
   - JWT tokens with expiration
   - bcrypt for password hashing (bcrypt==4.0.1)

4. **Rate limiting is enforced**
   - Login: 5 requests/minute
   - Register: 3 requests/minute
   - Upload: 10 requests/minute
   - Search: 50 requests/minute

5. **CORS configuration**
   - Set `SYNCBOARD_ALLOWED_ORIGINS` in production
   - NEVER use wildcard (`*`) in production
   - Default: `http://localhost:3000,http://localhost:8000`

### Security Testing

All security features have comprehensive tests:
- `tests/test_sanitization.py` - 53 tests (100% pass)
- `tests/test_security.py` - Security headers, HTTPS enforcement
- Input validation for all attack vectors (SQL, XSS, SSRF, path traversal)

---

## 🧪 Testing Best Practices

### Test Structure

**Use pytest fixtures from conftest.py:**
```python
def test_analytics(db_session):
    """db_session provides in-memory SQLite database"""
    # Test implementation

def test_with_cleanup(cleanup_test_state):
    """cleanup_test_state clears global state after test"""
    # Test implementation
```

**Test organization:**
- One test file per module
- Descriptive test names: `test_search_with_filters_returns_filtered_results`
- Use mocks for external dependencies (OpenAI, YouTube, etc.)

### Test Configuration

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

### Environment Variables for Testing

```python
# conftest.py automatically sets:
os.environ['TESTING'] = 'true'
os.environ['SYNCBOARD_SECRET_KEY'] = 'test-secret-key-for-testing'
os.environ['OPENAI_API_KEY'] = 'sk-test-key'
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_sanitization.py -v

# With coverage
pytest tests/ --cov=backend --cov-report=html

# Stop on first failure
pytest tests/ -x
```

### Test Metrics

Current status (as of last run):
- **Total Tests:** 116
- **Pass Rate:** 99.1% (115 passed, 1 failed)
- **Execution Time:** 2.54 seconds
- **Known Issues:** 1 empty document edge case

---

## 📝 Naming Conventions

### Files
- Python modules: `snake_case.py`
- Test files: `test_*.py`
- Routers: `routers/feature_name.py`
- Services: `*_service.py`, `*_suggester.py`, `*_extractor.py`
- Repositories: `*_repository.py`, `*_adapter.py`

### Variables & Functions
- Variables: `snake_case`
- Functions: `snake_case()`
- Constants: `UPPER_SNAKE_CASE`
- Classes: `PascalCase`
- Private: `_leading_underscore`

### Database Models
- SQLAlchemy models: `DBModelName` (e.g., `DBUser`, `DBDocument`)
- Pydantic models: `ModelName` (e.g., `User`, `Document`)
- Table names: `lowercase_plural` (e.g., `users`, `documents`)

### API Endpoints
- RESTful pattern: `/resource/{id}`
- Use HTTP methods correctly: GET, POST, PUT, DELETE
- Group by feature in routers

---

## 🎨 Code Style Guidelines

### Python Style (PEP 8)

```python
# Good: Type hints, docstrings, clear structure
async def get_document(
    doc_id: int,
    db: Session = Depends(get_db)
) -> Optional[Document]:
    """
    Get document by ID.

    Args:
        doc_id: Document ID
        db: Database session

    Returns:
        Document if found, None otherwise
    """
    return await db_repo.get_document(doc_id)
```

### JavaScript Style (Standard JS)

```javascript
// Good: Consistent indentation, clear naming
async function uploadText() {
    const content = document.getElementById('textInput').value;

    try {
        const response = await fetch('/upload_text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({ content })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        displayResult(result);
    } catch (error) {
        showError(error.message);
    }
}
```

### Docstring Style (Google)

```python
def process_document(content: str, metadata: Dict) -> ProcessedDocument:
    """
    Process document content with metadata.

    Args:
        content: Document text content
        metadata: Dictionary with cluster, topic, skill_level

    Returns:
        ProcessedDocument with extracted concepts

    Raises:
        ValueError: If content is empty
        ProcessingError: If extraction fails
    """
```

---

## 🚨 Common Pitfalls & How to Avoid Them

### 1. Pydantic V2 Deprecation Warnings

**Issue:** Using Pydantic V1 validators
```python
# Old (deprecated):
@validator('username')
def validate_username(cls, v):
    ...
```

**Solution:** Migrate to V2 field validators when updating Pydantic:
```python
# New:
@field_validator('username')
@classmethod
def validate_username(cls, v):
    ...
```

### 2. Database Session Management

**Issue:** Not closing database sessions
```python
# Bad:
db = SessionLocal()
result = db.query(DBDocument).all()
# Session never closed!
```

**Solution:** Use dependency injection with automatic cleanup:
```python
# Good:
def endpoint(db: Session = Depends(get_db)):
    result = db.query(DBDocument).all()
    # Session automatically closed
```

### 3. Global State in Tests

**Issue:** Tests affecting each other due to shared state
```python
# Bad:
def test_1():
    documents[1] = "test"  # Modifies global state

def test_2():
    # documents[1] still exists from test_1!
```

**Solution:** Use cleanup fixture:
```python
# Good:
def test_1(cleanup_test_state):
    documents[1] = "test"
    # Automatically cleaned after test
```

### 4. CORS Configuration

**Issue:** Using wildcard origins in production
```python
# Bad for production:
ALLOWED_ORIGINS = ["*"]
```

**Solution:** Set specific origins:
```python
# Good:
ALLOWED_ORIGINS = os.getenv("SYNCBOARD_ALLOWED_ORIGINS",
                            "http://localhost:8000").split(",")
```

### 5. Hardcoded Secrets

**Issue:** Secrets in code
```python
# Bad:
SECRET_KEY = "my-secret-key"
OPENAI_API_KEY = "sk-1234567890"
```

**Solution:** Environment variables:
```python
# Good:
SECRET_KEY = os.getenv("SYNCBOARD_SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

---

## 🔧 Common Tasks & How to Do Them

### Adding a New API Endpoint

1. **Create/Update Router:**
```python
# backend/routers/my_feature.py
from fastapi import APIRouter, Depends
from backend.dependencies import get_current_user

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

@router.post("/action")
async def perform_action(
    data: MyRequest,
    current_user: User = Depends(get_current_user)
):
    # Implementation
    return {"result": "success"}
```

2. **Mount Router in main.py:**
```python
# backend/main.py
from backend.routers import my_feature

app.include_router(my_feature.router)
```

3. **Add Tests:**
```python
# tests/test_my_feature.py
def test_perform_action():
    response = client.post("/my-feature/action",
                          json={"data": "test"})
    assert response.status_code == 200
```

### Adding a New Database Model

1. **Create SQLAlchemy Model:**
```python
# backend/db_models.py
class DBMyModel(Base):
    __tablename__ = "my_models"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

2. **Create Pydantic Model:**
```python
# backend/models.py
class MyModel(BaseModel):
    id: int
    name: str
    created_at: datetime
```

3. **Create Migration:**
```bash
alembic revision --autogenerate -m "Add MyModel table"
alembic upgrade head
```

### Adding a New Content Ingestion Type

1. **Add to ingest.py:**
```python
# backend/ingest.py
async def process_new_type(file_bytes: bytes, filename: str) -> str:
    """Process new file type"""
    # Implementation
    return extracted_text

# Update ingest_file function:
elif filename.endswith('.newext'):
    return await process_new_type(file_bytes, filename)
```

2. **Add Tests:**
```python
# tests/test_ingestion_new.py
@pytest.mark.asyncio
async def test_new_type_ingestion():
    content = await process_new_type(test_bytes, "test.newext")
    assert len(content) > 0
```

### Adding Environment Variable

1. **Update .env.example:**
```bash
# New variable description
MY_NEW_VARIABLE=default_value
```

2. **Load in constants.py:**
```python
# backend/constants.py
MY_NEW_VARIABLE = os.getenv("MY_NEW_VARIABLE", "default")
```

3. **Document in README.md:**
```markdown
| MY_NEW_VARIABLE | `default` | Description of what it does |
```

---

## 📊 Project Metrics & Status

### Current Status (Phase 7.1 Complete)

**Development Progress:**
- ✅ Phase 1: Security Hardening
- ✅ Phase 2: Performance Optimization
- ✅ Phase 3: Architecture Refactoring
- ✅ Phase 4: Features & UX
- ✅ Phase 5: Testing & Observability
- ✅ Phase 6: Production Hardening (Database, Docker, CI/CD)
- ✅ Phase 6.5: Database Migration
- ✅ Phase 7.1: Analytics Dashboard

**Code Metrics:**
- **Backend Code:** ~7,300 lines (main backend + routers)
- **Test Code:** ~8,500+ lines (12 modules)
- **Frontend:** ~52 KB JavaScript + 17 KB HTML
- **Documentation:** 25 markdown files

**Refactoring Impact:**
- **Before:** `main.py` = 1,325 lines (monolithic)
- **After:** `main.py` = 276 lines + 7 focused routers
- **Reduction:** 79% in main file

**Test Metrics:**
- **Total Tests:** 116
- **Pass Rate:** 99.1%
- **Execution Time:** 2.54 seconds
- **Coverage:** Comprehensive (all critical paths)

### Database Schema

**Tables:** 5 core tables
- `users` - User accounts
- `clusters` - Topic clusters
- `documents` - Document metadata
- `concepts` - Extracted concepts
- `vector_documents` - Vector embeddings

**Indexes:** 15+ optimized indexes for query performance

**Connection Pool:** 5 base connections + 10 overflow

---

## 🎓 Learning Resources

### Understanding the Architecture

1. **Start here:** Read `README.md` for project overview
2. **Phase reports:** Review `FINAL_PROJECT_REPORT.md` for development history
3. **Code tour:** Start from `backend/main.py` → routers → services → repositories
4. **Test tour:** Read `tests/test_api_endpoints.py` for E2E examples

### Key Documentation Files

- `README.md` - Quick start, features, API documentation
- `FINAL_PROJECT_REPORT.md` - Complete project history and accomplishments
- `BUILD_STATUS.md` - Current status and roadmap
- `CODEBASE_IMPROVEMENT_REPORT.md` - All 42 improvements made
- `PHASE_3_MIGRATION_GUIDE.md` - Architecture migration guide
- `.env.example` - Environment configuration template

### API Documentation (Interactive)

Once server is running:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## ✅ Checklist for New Contributors

### Before Making Changes

- [ ] Read `README.md` for project overview
- [ ] Read this `CLAUDE.md` file completely
- [ ] Set up development environment (see "Development Workflow" section)
- [ ] Run tests to ensure everything works: `pytest tests/ -v`
- [ ] Review recent git history: `git log --oneline -20`

### When Making Changes

- [ ] Create feature branch with proper naming: `claude/description-sessionid`
- [ ] Follow architecture patterns (Clean Architecture, Repository Pattern)
- [ ] Add tests for new functionality
- [ ] Run test suite before committing
- [ ] Update documentation if needed
- [ ] Follow naming conventions
- [ ] Add type hints to Python code
- [ ] Validate security implications

### Before Submitting PR

- [ ] All tests pass: `pytest tests/ -v`
- [ ] No security vulnerabilities introduced
- [ ] Environment variables documented in `.env.example`
- [ ] API changes documented
- [ ] Commit messages are descriptive
- [ ] No secrets committed to git

---

## 🚀 Performance Considerations

### Vector Store (TF-IDF)
- **Current:** In-memory, loads on startup
- **Capacity:** Works well for ~10k-50k documents
- **Optimization:** Lazy loading, incremental updates
- **Future:** Consider external vector database for 100k+ documents

### Database Connection Pooling
- **Pool size:** 5 base + 10 overflow
- **Timeout:** 30 seconds
- **Recycling:** 1 hour connection lifetime

### Rate Limiting
- Configured per-endpoint in routers
- Uses SlowAPI with in-memory storage
- Consider Redis for distributed rate limiting

### Caching Strategy
- LRU cache for concept extraction results
- In-memory vector store cache
- Consider Redis for distributed caching

---

## 🐛 Known Issues & Workarounds

### 1. Empty Document Edge Case
**Issue:** One test fails for empty document handling
**Status:** Low priority, edge case
**Workaround:** Input validation prevents empty documents

### 2. Pydantic V2 Migration Pending
**Issue:** Using deprecated V1 validators
**Status:** Works fine, deprecation warnings
**Workaround:** Will migrate in future Pydantic upgrade

### 3. CORS Wildcard Warning
**Issue:** Warning when using wildcard origins
**Status:** Development convenience, not production
**Workaround:** Set specific origins in production

---

## 🔮 Future Enhancements (Phase 7.2+)

### Planned Features
- **Phase 7.2:** Duplicate detection
- **Phase 7.3:** Document relationships and linking
- **Phase 7.4:** Collaboration features (sharing, permissions)
- **Phase 7.5:** Advanced analytics (NLP insights)
- **Phase 8:** Cloud deployment (Kubernetes, scaling, Redis)

### Scalability Roadmap
- External vector database (Pinecone, Weaviate)
- Redis caching layer
- Load balancing
- Database read replicas
- CDN for static assets

---

## 📞 Getting Help

### Documentation
- **This file:** Architecture, conventions, workflows
- **README.md:** Quick start, features, API
- **Phase Reports:** Development history and decisions
- **API Docs:** http://localhost:8000/docs

### Testing & Debugging
- Run specific test: `pytest tests/test_file.py::test_name -v -s`
- Enable debug logging: Set `SYNCBOARD_LOG_LEVEL=DEBUG` in .env
- View request IDs: Check response headers for `X-Request-ID`

### Common Commands Reference

```bash
# Development
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Testing
pytest tests/ -v                          # All tests
pytest tests/test_sanitization.py -v     # Specific module
pytest tests/ -x                          # Stop on first failure
pytest tests/ --cov=backend              # With coverage

# Docker
docker-compose up -d                      # Start services
docker-compose logs -f backend            # View logs
docker-compose exec backend bash          # Shell into container
docker-compose down                       # Stop services

# Database
alembic upgrade head                      # Apply migrations
alembic revision --autogenerate -m "msg"  # Create migration
alembic history                           # View history
python -c "from backend.database import init_db; init_db()"  # Initialize

# Git
git log --oneline --graph -20            # View history
git status                               # Check status
git diff                                 # View changes
```

---

## 🎯 Summary: Key Principles for AI Assistants

1. **Follow Clean Architecture:** API → Service → Repository → Data
2. **Never skip tests:** Add tests for all new functionality
3. **Security first:** Validate all input, use authentication
4. **Use dependency injection:** Makes code testable
5. **Follow naming conventions:** Consistency is key
6. **Document everything:** Code comments, docstrings, markdown files
7. **Check git history:** Learn from past commits and PRs
8. **Run tests before committing:** Ensure 99%+ pass rate
9. **Use environment variables:** Never hardcode secrets
10. **Ask when unsure:** Review documentation, check tests for examples

---

**This is a production-ready codebase. Treat it with care, test thoroughly, and maintain the high quality standards established in Phases 1-7.1.**

**Last Updated:** 2025-11-14
**Version:** 1.0
**Maintainer:** AI Assistant Team
