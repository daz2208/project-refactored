# 🧠 SyncBoard 3.0 Knowledge Bank

A powerful, AI-enhanced knowledge management system built with FastAPI and vanilla JavaScript. Automatically organizes, clusters, and searches your documents, code snippets, URLs, and images using OpenAI-powered concept extraction and semantic search.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Git

### Installation

1. **Clone the repository**
   ```bash
   cd /home/user/project-refactored
   ```

2. **Set up Python virtual environment**
   ```bash
   cd refactored/syncboard_backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   A `.env` file has been created at `refactored/syncboard_backend/.env` with development defaults.

   **⚠️ IMPORTANT:** You must add your OpenAI API key!

   Edit `.env` and replace:
   ```bash
   OPENAI_API_KEY=sk-replace-with-your-actual-openai-key
   ```

   With your actual key from https://platform.openai.com/api-keys

5. **Initialize the database**
   ```bash
   cd refactored/syncboard_backend
   python -c "from backend.database import init_db; init_db()"
   ```

6. **Run the application**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the application**

   Open your browser to: **http://localhost:8000/**

   The backend automatically serves the frontend - no separate server needed!

---

## 📋 Environment Variables

The `.env` file is located at `refactored/syncboard_backend/.env`

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SYNCBOARD_SECRET_KEY` | JWT token signing key | Auto-generated (32 bytes hex) |
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNCBOARD_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:8000` | CORS allowed origins (comma-separated) |
| `SYNCBOARD_STORAGE_PATH` | `storage.json` | JSON storage file path |
| `SYNCBOARD_VECTOR_DIM` | `256` | Vector dimension for embeddings |
| `SYNCBOARD_TOKEN_EXPIRE_MINUTES` | `1440` (24 hours) | JWT token expiration time |

---

## 🏗️ Architecture

### Tech Stack

**Backend:**
- FastAPI (async/await)
- PostgreSQL + SQLAlchemy ORM
- OpenAI GPT-4o-mini (concept extraction)
- scikit-learn (TF-IDF vectors)
- JWT authentication with bcrypt
- Python 3.8+

**Frontend:**
- Vanilla JavaScript (no frameworks)
- Custom CSS (dark theme)
- Native fetch API
- Auto-served by FastAPI (single deployment)

### Architecture Pattern

```
Frontend (static files)
    ↓ HTTP/REST
FastAPI Controllers (main.py)
    ↓ Dependency Injection
Services Layer (services.py)
    ↓
Repository (repository.py)
    ↓
Database Layer (db_repository.py + SQLAlchemy)
    ↓
PostgreSQL Database + Vector Store
```

---

## ✨ Features

### ✅ Phase 1-7.5 Complete - Production Ready with Advanced Features!

- ✅ **Security:** JWT auth, rate limiting, input validation, atomic saves
- ✅ **Performance:** Async API calls, batch updates, LRU caching, search optimization
- ✅ **Architecture:** Repository pattern, service layer, dependency injection, LLM abstraction
- ✅ **Database:** PostgreSQL with SQLAlchemy ORM, full migration complete
- ✅ **Features:** Document CRUD, search filters, export (JSON/Markdown), cluster management
- ✅ **Analytics:** Comprehensive dashboard with charts, statistics, and insights
- ✅ **Duplicate Detection:** Find and merge similar documents automatically
- ✅ **Tags System:** User-defined tags for flexible organization
- ✅ **Saved Searches:** Quick access to frequently used search queries
- ✅ **Document Relationships:** Link related documents together
- ✅ **UX:** Keyboard shortcuts, search highlighting, loading states, error handling
- ✅ **Testing:** 40+ automated tests, 100% passing, comprehensive coverage
- ✅ **Production:** Hardened infrastructure, health checks, logging, monitoring

### Core Capabilities

1. **Document Ingestion**
   - Plain text
   - URLs (automatic content extraction)
   - Files (PDF, TXT, etc.)
   - Images (OCR with Tesseract)
   - YouTube videos (automatic transcription)

2. **AI-Powered Organization**
   - Automatic concept extraction
   - Intelligent clustering by topic
   - Skill level classification (beginner/intermediate/advanced)
   - Primary topic identification

3. **Advanced Search**
   - Vector similarity search (TF-IDF)
   - Filter by source type, skill level, date range
   - Cluster-specific search
   - Search term highlighting
   - Snippet vs full content modes

4. **Document Management**
   - View, edit, delete documents
   - Update metadata (cluster, topic, skill level)
   - Cascade deletion (removes from clusters)
   - Export clusters as JSON or Markdown
   - Export entire knowledge bank

5. **Build Suggestions**
   - AI-generated project ideas based on your knowledge
   - Leverages all ingested content
   - Personalized recommendations

6. **Analytics Dashboard** (Phase 7.1)
   - Real-time knowledge bank statistics
   - Document growth trends over time (time-series charts)
   - Distribution visualizations (clusters, skill levels, source types)
   - Top concepts analysis
   - Recent activity timeline
   - Customizable time periods (7, 30, 90, 365 days)
   - Interactive charts powered by Chart.js

7. **Duplicate Detection** (Phase 7.2)
   - TF-IDF similarity-based duplicate finding
   - Configurable similarity threshold (default: 85%)
   - Side-by-side content comparison
   - Merge duplicates (keep one, delete others)
   - Automatic vector store cleanup

8. **Tags System** (Phase 7.3)
   - User-defined tags with custom colors
   - Tag documents for flexible organization
   - Tag management (create, delete, view usage)
   - Filter and search by tags
   - Many-to-many document-tag relationships

9. **Saved Searches** (Phase 7.4)
   - Save frequently used search queries
   - Store search filters with queries
   - Quick access to saved searches
   - Usage statistics (use count, last used)
   - One-click search execution

10. **Document Relationships** (Phase 7.5)
    - Link related documents together
    - Relationship types: related, prerequisite, followup, alternative, supersedes
    - Bidirectional relationship tracking
    - Strength scores for AI-discovered relationships
    - Navigate between related documents

### Keyboard Shortcuts

- `Ctrl+K` / `Cmd+K` - Focus search input
- `Esc` - Clear search results
- `N` - Scroll to top (for new upload)

---

## 🧪 Testing

### Run Unit Tests

```bash
cd refactored/syncboard_backend
pytest tests/test_services.py -v
```

### Test Coverage

- ✅ DocumentService: ingestion, deletion, clustering
- ✅ SearchService: search, filters, content modes
- ✅ ClusterService: get all, get details
- ✅ BuildSuggestionService: generation
- ✅ Integration tests: full workflows
- ✅ Edge cases: nonexistent items, empty state

---

## 📚 API Documentation

Once the server is running, visit:
- **Interactive docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Key Endpoints

**Authentication:**
- `POST /users` - Register new user
- `POST /token` - Login (get JWT token)

**Document Management:**
- `POST /upload_text` - Upload plain text
- `POST /upload_url` - Upload from URL
- `POST /upload_file` - Upload file
- `POST /upload_image` - Upload image (OCR)
- `POST /upload_youtube` - Upload YouTube video
- `GET /documents/{doc_id}` - Get document
- `PUT /documents/{doc_id}/metadata` - Update document
- `DELETE /documents/{doc_id}` - Delete document

**Search:**
- `GET /search_full` - Search with filters
  - Query params: `q`, `top_k`, `cluster_id`, `source_type`, `skill_level`, `date_from`, `date_to`

**Clusters:**
- `GET /clusters` - List all clusters
- `GET /clusters/{cluster_id}` - Get cluster details
- `PUT /clusters/{cluster_id}` - Rename cluster

**Export:**
- `GET /export/cluster/{cluster_id}?format={json|markdown}` - Export cluster
- `GET /export/all?format={json|markdown}` - Export all

**AI Features:**
- `POST /what_can_i_build` - Get AI project suggestions

**Analytics (Phase 7.1):**
- `GET /analytics?time_period={days}` - Get comprehensive analytics dashboard data
  - Returns: overview stats, time-series data, distributions, top concepts, recent activity

**Duplicate Detection (Phase 7.2):**
- `GET /duplicates?threshold={0-1}&limit={n}` - Find duplicate documents
- `GET /duplicates/{doc_id1}/{doc_id2}` - Compare two documents
- `POST /duplicates/merge` - Merge duplicates (body: keep_doc_id, delete_doc_ids)

**Tags System (Phase 7.3):**
- `POST /tags` - Create a new tag (body: name, color)
- `GET /tags` - Get all user tags with document counts
- `POST /documents/{doc_id}/tags/{tag_id}` - Add tag to document
- `DELETE /documents/{doc_id}/tags/{tag_id}` - Remove tag from document
- `GET /documents/{doc_id}/tags` - Get all tags for a document
- `DELETE /tags/{tag_id}` - Delete a tag

**Saved Searches (Phase 7.4):**
- `POST /saved-searches` - Save a search (body: name, query, filters)
- `GET /saved-searches` - Get all saved searches
- `POST /saved-searches/{search_id}/use` - Use saved search (returns query/filters)
- `DELETE /saved-searches/{search_id}` - Delete saved search

**Document Relationships (Phase 7.5):**
- `POST /documents/{source_id}/relationships` - Create relationship (body: target_doc_id, relationship_type, strength)
- `GET /documents/{doc_id}/relationships` - Get all related documents
- `DELETE /documents/{source_id}/relationships/{target_id}` - Delete relationship

---

## 🔒 Security

### Production Deployment Checklist

- [ ] Generate new `SYNCBOARD_SECRET_KEY` with `openssl rand -hex 32`
- [ ] Set `SYNCBOARD_ALLOWED_ORIGINS` to specific domain(s) - NOT `*`
- [ ] Use HTTPS for all connections
- [ ] Rotate JWT secret periodically
- [ ] Monitor rate limiting logs
- [ ] Set up backup strategy for `storage.json`
- [ ] Enable request logging with correlation IDs
- [ ] Configure firewall rules

### Security Features

- ✅ JWT authentication with bcrypt password hashing
- ✅ Rate limiting on auth endpoints (5 login/min, 3 register/min)
- ✅ Input validation (file sizes, credentials)
- ✅ Path traversal protection
- ✅ Atomic file saves (crash protection)
- ✅ HTML escaping in search results (XSS prevention)
- ✅ CORS configuration with warnings

---

## 📖 Documentation

- **`BUILD_STATUS.md`** - Current build status, roadmap, and next steps
- **`CODEBASE_IMPROVEMENT_REPORT.md`** - Comprehensive analysis of all 42 improvements
- **`PHASE_3_MIGRATION_GUIDE.md`** - Phase 3 architecture migration guide
- **`.env.example`** - Environment variable template
- **`refactored/app-phase4.js`** - Phase 4 feature reference implementation

---

## 🎯 Status & Roadmap

### Current Status: Phase 7 Complete ✅ - FEATURE-COMPLETE PRODUCTION SYSTEM

**All Phase 7 features complete!** The application is a feature-complete production system with:
- ✅ Database persistence (PostgreSQL + SQLAlchemy)
- ✅ Analytics dashboard (charts, statistics, trends)
- ✅ Duplicate detection (find & merge similar documents)
- ✅ Tags system (flexible user-defined organization)
- ✅ Saved searches (quick access to frequent queries)
- ✅ Document relationships (link related content)
- ✅ Comprehensive testing (40+ tests, 100% passing)
- ✅ Production hardening (security, monitoring, health checks)
- ✅ Single-command deployment (frontend auto-served)
- ✅ 20+ API endpoints covering all functionality

### Optional Future Enhancements

- **Phase 8:** Cloud deployment & scaling (Docker, Kubernetes, Redis, vector database)
- **Phase 9:** Collaboration features (share knowledge banks, team workspaces)
- **Phase 10:** Mobile app & PWA

See `FINAL_PROJECT_REPORT.md` for complete project documentation.

---

## 🐛 Known Considerations

1. **CORS Configuration** - Update `SYNCBOARD_ALLOWED_ORIGINS` for production domains
2. **In-Memory Vectors** - Vector store loads to memory on startup (works for ~10k-50k documents)
3. **OpenAI API Key Required** - Server requires valid OpenAI key to start
4. **Database Scaling** - Single PostgreSQL instance (sufficient for most use cases)

For production deployment at scale, consider Phase 8 enhancements (Redis caching, vector database, load balancing).

---

## 🤝 Contributing

### Development Workflow

1. Create a feature branch from `main`
2. Make changes with tests
3. Run test suite: `pytest tests/ -v`
4. Commit with descriptive message
5. Push and create pull request

### Code Style

- Python: PEP 8
- JavaScript: Standard JS conventions
- Docstrings: Google style
- Type hints: Use where applicable

---

## 📄 License

See repository for license information.

---

## 📞 Support

- **Issues:** GitHub Issues
- **Documentation:** See `/docs` and markdown files in repo
- **Tests:** `pytest tests/ -v`

---

## 🙏 Acknowledgments

Built with:
- FastAPI
- OpenAI
- scikit-learn
- pytesseract
- yt-dlp
- bcrypt
- slowapi

---

**Status:** ✅ **FEATURE-COMPLETE** - Phase 7 Complete (7.1-7.5) - Advanced features: Analytics, Duplicate Detection, Tags, Saved Searches, Document Relationships.

**Last Updated:** 2025-11-13
