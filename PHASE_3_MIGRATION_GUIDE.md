# Phase 3 Architecture Migration Guide

This document explains how to migrate `main.py` endpoints to use the new Phase 3 architecture with Repository Pattern, Service Layer, and Dependency Injection.

## Architecture Overview

### Before (Phase 2)
```python
# Global mutable state
documents: Dict[int, str] = {}
metadata: Dict[int, DocumentMetadata] = {}
clusters: Dict[int, Cluster] = {}

# Direct instantiation
concept_extractor = ConceptExtractor()
build_suggester = BuildSuggester()

# Business logic mixed in endpoints
@app.post("/upload_text")
async def upload_text(req: TextUpload, user: User = Depends(get_current_user)):
    # Extract concepts
    extraction = await concept_extractor.extract(req.content, "text")

    # Build metadata
    concepts = [Concept(...) for c in extraction.get("concepts", [])]
    metadata = DocumentMetadata(...)

    # Save document
    doc_id = len(documents)
    documents[doc_id] = req.content

    # Auto-cluster
    cluster_id = auto_cluster(doc_id, metadata)

    return {"document_id": doc_id, "cluster_id": cluster_id}
```

### After (Phase 3)
```python
# No global state - encapsulated in Repository
# Services handle business logic
# Dependency injection for loose coupling

@app.post("/upload_text")
async def upload_text(
    req: TextUpload,
    user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    # Service handles all business logic
    doc_id, cluster_id = await doc_service.ingest_text(req.content, "text")

    return {"document_id": doc_id, "cluster_id": cluster_id}
```

## Benefits

1. **Testability**: Services can be unit tested with mock dependencies
2. **Maintainability**: Business logic separated from HTTP concerns
3. **Thread Safety**: Repository uses async locks
4. **Flexibility**: Easy to swap implementations (e.g., switch from JSON to PostgreSQL)
5. **Decoupling**: No vendor lock-in with LLM provider abstraction

## Migration Steps

### Step 1: Import New Dependencies

```python
from backend.dependencies import (
    get_document_service,
    get_search_service,
    get_cluster_service,
    get_build_suggestion_service,
    get_repository
)
from backend.services import (
    DocumentService,
    SearchService,
    ClusterService,
    BuildSuggestionService
)
```

### Step 2: Remove Global State

Delete these global variables:
```python
# DELETE THIS:
documents: Dict[int, str] = {}
metadata: Dict[int, DocumentMetadata] = {}
clusters: Dict[int, Cluster] = {}
users: Dict[str, str] = {}
vector_store = VectorStore(...)
concept_extractor = ConceptExtractor()
build_suggester = BuildSuggester()
```

### Step 3: Migrate Endpoints

#### Example 1: Upload Text Endpoint

**Before:**
```python
@app.post("/upload_text")
async def upload_text(req: TextUpload, user: User = Depends(get_current_user)):
    # Extract concepts using AI
    extraction = await concept_extractor.extract(req.content, "text")

    # Build metadata
    concepts = [
        Concept(name=c["name"], relevance=c.get("relevance", 0.5))
        for c in extraction.get("concepts", [])
    ]

    metadata = DocumentMetadata(
        source_type="text",
        concepts=concepts,
        skill_level=extraction.get("skill_level", "unknown"),
        primary_topic=extraction.get("primary_topic", "uncategorized"),
        ingested_at=datetime.utcnow().isoformat(),
        cluster_id=None
    )

    # Save document
    doc_id = len(documents)
    documents[doc_id] = req.content
    metadata_dict[doc_id] = metadata

    # Add to vector store
    vector_store.add_document(req.content)

    # Auto-cluster
    cluster_id = auto_cluster_document(doc_id, metadata)
    metadata.cluster_id = cluster_id

    # Save to disk
    save_storage(STORAGE_PATH, documents, metadata_dict, clusters, users)

    return {"document_id": doc_id, "cluster_id": cluster_id}
```

**After:**
```python
@app.post("/upload_text")
async def upload_text(
    req: TextUpload,
    user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    doc_id, cluster_id = await doc_service.ingest_text(req.content, "text")
    return {"document_id": doc_id, "cluster_id": cluster_id}
```

#### Example 2: Search Endpoint

**Before:**
```python
@app.get("/search_full")
async def search_full_content(
    q: str,
    full_content: bool = False,
    cluster_id: int = None,
    top_k: int = 20,
    user: User = Depends(get_current_user)
):
    # Search logic mixed with data access
    allowed_doc_ids = None
    if cluster_id is not None:
        cluster = clusters.get(cluster_id)
        if cluster:
            allowed_doc_ids = cluster.document_ids

    # Vector search
    results = vector_store.search(q, top_k, allowed_doc_ids)

    # Build response
    enriched_results = []
    for doc_id, score, snippet in results:
        meta = metadata.get(doc_id)
        if not meta:
            continue

        content = documents[doc_id] if full_content else snippet

        enriched_results.append({
            "doc_id": doc_id,
            "score": score,
            "content": content,
            "metadata": meta.dict()
        })

    return {"results": enriched_results}
```

**After:**
```python
@app.get("/search_full")
async def search_full_content(
    q: str,
    full_content: bool = False,
    cluster_id: int = None,
    top_k: int = 20,
    user: User = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service)
):
    results = await search_service.search(
        query=q,
        top_k=top_k,
        cluster_id=cluster_id,
        full_content=full_content
    )

    return {"results": results}
```

#### Example 3: Build Suggestions Endpoint

**Before:**
```python
@app.post("/what_can_i_build")
async def what_can_i_build(
    req: BuildSuggestionRequest,
    user: User = Depends(get_current_user)
):
    # Access global state directly
    suggestions = await build_suggester.analyze_knowledge_bank(
        clusters=clusters,
        metadata=metadata,
        documents=documents,
        max_suggestions=req.max_suggestions
    )

    summary = {
        "total_docs": len(documents),
        "total_clusters": len(clusters)
    }

    return {
        "suggestions": [s.dict() for s in suggestions],
        "knowledge_summary": summary
    }
```

**After:**
```python
@app.post("/what_can_i_build")
async def what_can_i_build(
    req: BuildSuggestionRequest,
    user: User = Depends(get_current_user),
    suggestion_service: BuildSuggestionService = Depends(get_build_suggestion_service)
):
    result = await suggestion_service.generate_suggestions(req.max_suggestions)
    return result
```

#### Example 4: Clusters Endpoint

**Before:**
```python
@app.get("/clusters")
async def get_clusters(user: User = Depends(get_current_user)):
    cluster_list = []
    for cluster in clusters.values():
        cluster_list.append({
            "id": cluster.id,
            "name": cluster.name,
            "doc_count": len(cluster.document_ids),
            "primary_concepts": cluster.primary_concepts,
            "skill_level": cluster.skill_level
        })
    return {"clusters": cluster_list}
```

**After:**
```python
@app.get("/clusters")
async def get_clusters(
    user: User = Depends(get_current_user),
    cluster_service: ClusterService = Depends(get_cluster_service)
):
    clusters = await cluster_service.get_all_clusters()
    return {"clusters": clusters}
```

### Step 4: Update Authentication (Users)

The repository now handles user storage. Update authentication:

**Before:**
```python
@app.post("/users")
async def register_user(user: UserCreate):
    if username in users:
        raise HTTPException(400, "User exists")

    hashed_pw = hash_password(user.password)
    users[username] = hashed_pw

    save_storage(STORAGE_PATH, documents, metadata, clusters, users)
    return {"message": "User created"}
```

**After:**
```python
@app.post("/users")
async def register_user(
    user: UserCreate,
    repo: KnowledgeBankRepository = Depends(get_repository)
):
    existing = await repo.get_user(user.username)
    if existing:
        raise HTTPException(400, "User exists")

    hashed_pw = hash_password(user.password)
    await repo.add_user(user.username, hashed_pw)

    return {"message": "User created"}
```

## Testing the Migration

### Unit Testing Services

With the new architecture, you can easily unit test services:

```python
import pytest
from backend.services import DocumentService
from backend.llm_providers import MockLLMProvider
from backend.repository import KnowledgeBankRepository

@pytest.mark.asyncio
async def test_document_ingestion():
    # Create test dependencies
    repo = KnowledgeBankRepository(storage_path="test_storage.json", vector_dim=256)
    mock_provider = MockLLMProvider()
    extractor = ConceptExtractor(llm_provider=mock_provider)

    # Create service with mocked dependencies
    service = DocumentService(repository=repo, concept_extractor=extractor)

    # Test ingestion
    doc_id, cluster_id = await service.ingest_text("Test content", "text")

    assert doc_id >= 0
    assert cluster_id >= 0
```

## Rollout Strategy

To minimize risk, migrate endpoints incrementally:

1. **Phase 3a**: Migrate read-only endpoints (GET /clusters, GET /search_full)
2. **Phase 3b**: Migrate write endpoints (POST /upload_text, POST /upload)
3. **Phase 3c**: Migrate authentication endpoints
4. **Phase 3d**: Remove old global state completely

Each phase should be tested before proceeding to the next.

## Backwards Compatibility

The new architecture is designed to be backwards compatible:
- Repository initializes from existing `storage.json`
- ConceptExtractor/BuildSuggester default to OpenAIProvider
- Same data models used throughout

## Configuration

Set these environment variables:
```bash
# Existing variables (unchanged)
SYNCBOARD_SECRET_KEY=<your-secret-key>
OPENAI_API_KEY=<your-api-key>

# Storage configuration
SYNCBOARD_STORAGE_PATH=storage.json  # default
SYNCBOARD_VECTOR_DIM=256             # default
```

## Summary of Changes

| Component | Before | After |
|-----------|--------|-------|
| **State Management** | Global dictionaries | Repository class with locks |
| **Business Logic** | Mixed in endpoints | Service layer |
| **Dependencies** | Global instantiation | FastAPI dependency injection |
| **LLM Integration** | Direct OpenAI coupling | Provider abstraction |
| **Testing** | Hard to test | Easy with mocks |
| **Scalability** | Limited | Database-ready |

## Next Steps

1. Review this migration guide
2. Test new architecture with existing data
3. Migrate endpoints one at a time
4. Add unit tests for services
5. Consider database migration (PostgreSQL) for Phase 4
