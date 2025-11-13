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

5. **Run the backend**
   ```bash
   cd backend
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Open the frontend**

   Open `refactored/index.html` in your browser, or serve it with:
   ```bash
   # In the refactored/ directory
   python -m http.server 3000
   ```

   Then visit: http://localhost:3000

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
- OpenAI GPT-4o-mini (concept extraction)
- scikit-learn (TF-IDF vectors)
- JWT authentication with bcrypt
- Python 3.8+

**Frontend:**
- Vanilla JavaScript (no frameworks)
- Custom CSS (dark theme)
- Native fetch API

### Architecture Pattern

```
Frontend (app.js)
    ↓ HTTP/REST
FastAPI Controllers (main.py)
    ↓ Dependency Injection
Services Layer (services.py)
    ↓
Repository (repository.py)
    ↓
Storage & Vectors (storage.py, vector_store.py)
```

---

## ✨ Features

### ✅ Phase 1-4 Complete (27/42 improvements)

- ✅ **Security:** JWT auth, rate limiting, input validation, atomic saves
- ✅ **Performance:** Async API calls, batch updates, LRU caching, search optimization
- ✅ **Architecture:** Repository pattern, service layer, dependency injection, LLM abstraction
- ✅ **Features:** Document CRUD, search filters, export (JSON/Markdown), cluster management
- ✅ **UX:** Keyboard shortcuts, search highlighting, loading states, error handling
- ✅ **Testing:** Comprehensive unit tests for service layer

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

## 🎯 Roadmap

### Current Status: Phase 4 Complete ✅

**Progress:** 27/42 improvements (64%)

### Next: Phase 5 - Testing & Observability (Recommended)

- End-to-end API tests
- Request ID tracing
- Structured logging
- Enhanced health checks

### Future Phases

- **Phase 6:** UX improvements (progress indicators, themes, undo)
- **Phase 7:** Advanced features (analytics, collaboration, duplicate detection)
- **Phase 8:** Scalability (PostgreSQL, Qdrant, Redis, Celery)

See `BUILD_STATUS.md` for detailed roadmap.

---

## 🐛 Known Limitations

1. **CORS Wildcard** - Configure `SYNCBOARD_ALLOWED_ORIGINS` for production
2. **Single JSON File** - Works well for <50 concurrent users, <10k documents
3. **In-Memory Vectors** - Limited to ~10k-50k documents
4. **No Database Migrations** - Manual schema change handling
5. **Missing OpenAI Key** - Server crashes on startup (by design)

See `CODEBASE_IMPROVEMENT_REPORT.md` for complete technical debt analysis.

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

**Status:** Production-ready with comprehensive feature set. Phase 5 recommended for enhanced observability.

**Last Updated:** 2025-11-12
