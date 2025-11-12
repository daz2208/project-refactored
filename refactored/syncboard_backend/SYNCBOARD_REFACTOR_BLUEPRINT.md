# SyncBoard Refactor Blueprint
## Complete Step-by-Step Build Plan

**Project:** Knowledge Bank with Auto-Clustering & Build Suggestions  
**Current Version:** 2.0 (Board-based)  
**Target Version:** 3.0 (Knowledge-first)  
**Estimated Time:** 2-3 days of focused work  
**Date Created:** November 12, 2025

---

## Table of Contents

1. [Project Goals](#project-goals)
2. [What Changes](#what-changes)
3. [What Stays](#what-stays)
4. [Phase 1: Remove Board System](#phase-1-remove-board-system)
5. [Phase 2: Add Concept Extraction](#phase-2-add-concept-extraction)
6. [Phase 3: Add Clustering System](#phase-3-add-clustering-system)
7. [Phase 4: Add Image Ingestion](#phase-4-add-image-ingestion)
8. [Phase 5: Full Content Search](#phase-5-full-content-search)
9. [Phase 6: Build Suggestion System](#phase-6-build-suggestion-system)
10. [Phase 7: Frontend Rebuild](#phase-7-frontend-rebuild)
11. [Phase 8: Testing & Validation](#phase-8-testing--validation)
12. [API Cost Analysis](#api-cost-analysis)
13. [File Structure](#file-structure)
14. [Success Criteria](#success-criteria)

---

## Project Goals

### Primary Objectives
1. Remove worthless board system
2. Auto-extract concepts from all ingested content
3. Cluster similar content together automatically
4. Store FULL content (not snippets)
5. Add image ingestion with OCR
6. Build "What Can I Build?" analysis feature
7. Use GPT-5 nano for ingestion (cheap)
8. Use GPT-5 mini for generation (affordable + good)

### User Experience Goal
**Before:** "I have to organize content into boards manually"  
**After:** "I dump everything in, AI organizes it, tells me what I can build"

---

## What Changes

### Major Removals
- All board CRUD operations
- Board-document associations
- Board UI components
- Board validation logic
- `board_id` from upload requests

### Major Additions
- Concept extraction engine (GPT-5 nano)
- Clustering system (auto-groups similar content)
- Image ingestion pipeline (OCR + metadata)
- Full content storage (not snippets)
- Build suggestion engine (GPT-5 mini)
- Knowledge bank interface

### Modified Components
- Upload endpoints (no board_id)
- Search (returns full content)
- Storage (documents + concepts + clusters)
- Vector store (cluster-aware)
- AI generation (uses GPT-5 mini)

---

## What Stays

### Keep These Files/Features
- `ingest.py` - multimodal ingestion (YouTube, PDF, audio, web)
- `ai_generation_real.py` - AI with RAG (will modify to use GPT-5 mini)
- `vector_store.py` - TF-IDF search (will enhance)
- Authentication system (JWT, users)
- Storage system (will simplify)

### Keep These Dependencies
- FastAPI
- OpenAI API (for GPT-5 models)
- Anthropic API (optional fallback)
- yt-dlp (YouTube)
- pypdf (PDFs)
- BeautifulSoup (web scraping)
- python-docx (Word docs)

---

## Phase 1: Remove Board System

### Step 1.1: Modify `backend/models.py`

**Remove these classes:**
```python
class Board(BaseModel)
class BoardCreate(BaseModel)
```

**Modify these classes:**
```python
# OLD
class DocumentUpload(BaseModel):
    board_id: int
    url: HttpUrl

# NEW
class DocumentUpload(BaseModel):
    url: HttpUrl
```

```python
# OLD
class TextUpload(BaseModel):
    board_id: int
    content: str

# NEW
class TextUpload(BaseModel):
    content: str
```

```python
# OLD
class FileBytesUpload(BaseModel):
    board_id: int
    filename: str
    content: str

# NEW
class FileBytesUpload(BaseModel):
    filename: str
    content: str
```

**Add new classes:**
```python
class Concept(BaseModel):
    """Extracted concept/topic from content."""
    name: str
    category: str  # e.g., "technology", "skill", "tool"
    confidence: float  # 0.0 to 1.0

class DocumentMetadata(BaseModel):
    """Metadata for ingested document."""
    doc_id: int
    owner: str
    source_type: str  # "youtube", "pdf", "text", "url", "audio", "image"
    source_url: Optional[str] = None
    filename: Optional[str] = None
    concepts: List[Concept] = []
    skill_level: str  # "beginner", "intermediate", "advanced"
    cluster_id: Optional[int] = None
    ingested_at: str  # ISO timestamp
    content_length: int

class Cluster(BaseModel):
    """Group of related documents."""
    id: int
    name: str  # e.g., "Docker & Containerization"
    primary_concepts: List[str]
    doc_ids: List[int]
    skill_level: str
    doc_count: int

class BuildSuggestion(BaseModel):
    """AI-generated project suggestion."""
    title: str
    description: str
    feasibility: str  # "high", "medium", "low"
    effort_estimate: str  # "1 day", "1 week", etc.
    required_skills: List[str]
    missing_knowledge: List[str]
    relevant_clusters: List[int]
    starter_steps: List[str]
    file_structure: Optional[str] = None
```

### Step 1.2: Modify `backend/storage.py`

**OLD function signature:**
```python
def load_storage(path: str, vector_store: VectorStore) -> Tuple[Dict[int, Board], Dict[int, str], Dict[str, str]]
```

**NEW function signature:**
```python
def load_storage(path: str, vector_store: VectorStore) -> Tuple[Dict[int, str], Dict[int, DocumentMetadata], Dict[int, Cluster], Dict[str, str]]
```

**Returns:**
- `documents`: Dict[int, str] - doc_id → full content
- `metadata`: Dict[int, DocumentMetadata] - doc_id → metadata
- `clusters`: Dict[int, Cluster] - cluster_id → cluster
- `users`: Dict[str, str] - username → hashed password

**OLD save function:**
```python
def save_storage(path: str, boards: Dict[int, Board], documents: Dict[int, str], users: Dict[str, str])
```

**NEW save function:**
```python
def save_storage(
    path: str,
    documents: Dict[int, str],
    metadata: Dict[int, DocumentMetadata],
    clusters: Dict[int, Cluster],
    users: Dict[str, str]
)
```

**Storage JSON structure:**
```json
{
  "documents": [
    "full text content of doc 0",
    "full text content of doc 1"
  ],
  "metadata": [
    {
      "doc_id": 0,
      "owner": "daz",
      "source_type": "youtube",
      "source_url": "https://youtube.com/watch?v=...",
      "concepts": [
        {"name": "Docker", "category": "tool", "confidence": 0.95},
        {"name": "containerization", "category": "concept", "confidence": 0.89}
      ],
      "skill_level": "intermediate",
      "cluster_id": 1,
      "ingested_at": "2025-11-12T10:30:00Z",
      "content_length": 15000
    }
  ],
  "clusters": [
    {
      "id": 1,
      "name": "Docker & Containerization",
      "primary_concepts": ["Docker", "containerization", "deployment"],
      "doc_ids": [0, 3, 7],
      "skill_level": "intermediate",
      "doc_count": 3
    }
  ],
  "users": {
    "daz": "hashed_password_here"
  }
}
```

### Step 1.3: Modify `backend/main.py`

**Remove these endpoints:**
```python
@app.post("/boards")  # DELETE THIS
@app.get("/boards")   # DELETE THIS
@app.get("/boards/{board_id}")  # DELETE THIS
@app.delete("/boards/{board_id}")  # DELETE THIS
```

**Update global state variables:**
```python
# OLD
boards: Dict[int, Board] = {}
documents: Dict[int, str] = {}
users: Dict[str, str] = {}

# NEW
documents: Dict[int, str] = {}
metadata: Dict[int, DocumentMetadata] = {}
clusters: Dict[int, Cluster] = {}
users: Dict[str, str] = {}
```

**Update startup event:**
```python
@app.on_event("startup")
async def startup_event():
    global documents, metadata, clusters, users
    documents, metadata, clusters, users = load_storage(STORAGE_PATH, vector_store)
    logger.info(f"Loaded {len(documents)} documents, {len(clusters)} clusters, {len(users)} users")
```

**Modify upload endpoints (remove board validation):**
```python
# OLD
@app.post("/upload_text")
async def upload_text_content(
    req: TextUpload,
    current_user: User = Depends(get_current_user)
):
    # Validate board exists
    board = boards.get(req.board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    if board.owner != current_user.username:
        raise HTTPException(status_code=403, detail="Access forbidden")
    # ... rest

# NEW
@app.post("/upload_text")
async def upload_text_content(
    req: TextUpload,
    current_user: User = Depends(get_current_user)
):
    # No board validation - just validate content
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    # Extract concepts, cluster, store
    # ... (see Phase 2)
```

---

## Phase 2: Add Concept Extraction

### Step 2.1: Create `backend/concept_extractor.py`

**New file:** `backend/concept_extractor.py`

```python
"""
Concept extraction using GPT-5 nano.
Analyzes content and extracts topics, concepts, skills, and metadata.
"""

import os
import json
import logging
from typing import List, Dict
from openai import OpenAI

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

class ConceptExtractor:
    """Extract concepts from content using GPT-5 nano."""
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-5-nano"
    
    async def extract(self, content: str, source_type: str) -> Dict:
        """
        Extract concepts from content.
        
        Args:
            content: Full text content
            source_type: "youtube", "pdf", "text", "url", "audio", "image"
        
        Returns:
            {
                "concepts": [
                    {"name": "Docker", "category": "tool", "confidence": 0.95},
                    {"name": "Python", "category": "language", "confidence": 0.88}
                ],
                "skill_level": "intermediate",
                "primary_topic": "containerization",
                "suggested_cluster": "Docker & Deployment"
            }
        """
        
        # Truncate content for concept extraction (first 2000 chars)
        sample = content[:2000] if len(content) > 2000 else content
        
        prompt = f"""Analyze this {source_type} content and extract structured information.

CONTENT:
{sample}

Return ONLY valid JSON (no markdown, no explanation) with this structure:
{{
  "concepts": [
    {{"name": "concept name", "category": "tool|skill|language|framework|concept|domain", "confidence": 0.0-1.0}}
  ],
  "skill_level": "beginner|intermediate|advanced",
  "primary_topic": "main topic in 2-4 words",
  "suggested_cluster": "cluster name for grouping similar content"
}}

Extract 3-10 concepts. Be specific. Use lowercase for names."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a concept extraction system. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            
            logger.info(f"Extracted {len(result.get('concepts', []))} concepts from {source_type}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Raw response: {result_text}")
            # Return minimal fallback
            return {
                "concepts": [],
                "skill_level": "unknown",
                "primary_topic": "uncategorized",
                "suggested_cluster": "General"
            }
        except Exception as e:
            logger.error(f"Concept extraction failed: {e}")
            return {
                "concepts": [],
                "skill_level": "unknown",
                "primary_topic": "uncategorized",
                "suggested_cluster": "General"
            }
```

### Step 2.2: Integrate into Upload Flow

**Modify `backend/main.py` upload endpoints:**

```python
from .concept_extractor import ConceptExtractor

# Initialize at startup
concept_extractor = ConceptExtractor()

@app.post("/upload_text")
async def upload_text_content(
    req: TextUpload,
    current_user: User = Depends(get_current_user)
):
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    async with storage_lock:
        # 1. Extract concepts
        extraction = await concept_extractor.extract(req.content, "text")
        
        # 2. Add to vector store
        doc_id = vector_store.add_document(req.content)
        documents[doc_id] = req.content
        
        # 3. Create metadata
        meta = DocumentMetadata(
            doc_id=doc_id,
            owner=current_user.username,
            source_type="text",
            concepts=[Concept(**c) for c in extraction.get("concepts", [])],
            skill_level=extraction.get("skill_level", "unknown"),
            cluster_id=None,  # Will be assigned by clustering
            ingested_at=datetime.utcnow().isoformat(),
            content_length=len(req.content)
        )
        metadata[doc_id] = meta
        
        # 4. Find or create cluster (see Phase 3)
        cluster_id = await find_or_create_cluster(
            doc_id=doc_id,
            suggested_cluster=extraction.get("suggested_cluster"),
            concepts=extraction.get("concepts", [])
        )
        metadata[doc_id].cluster_id = cluster_id
        
        # 5. Save
        save_storage(STORAGE_PATH, documents, metadata, clusters, users)
        
        logger.info(
            f"User {current_user.username} uploaded text as doc {doc_id} "
            f"(cluster: {cluster_id}, concepts: {len(extraction.get('concepts', []))})"
        )
        
        return {
            "document_id": doc_id,
            "cluster_id": cluster_id,
            "concepts": extraction.get("concepts", [])
        }
```

---

## Phase 3: Add Clustering System

### Step 3.1: Create `backend/clustering.py`

**New file:** `backend/clustering.py`

```python
"""
Automatic clustering of documents by similarity.
Groups related content together based on concepts and topics.
"""

import logging
from typing import List, Dict, Optional, Tuple
from collections import Counter
from .models import Cluster, DocumentMetadata, Concept

logger = logging.getLogger(__name__)

class ClusteringEngine:
    """Manages document clustering."""
    
    def __init__(self):
        self.similarity_threshold = 0.5  # How similar to join existing cluster
    
    def find_best_cluster(
        self,
        doc_concepts: List[Dict],
        suggested_name: str,
        existing_clusters: Dict[int, Cluster]
    ) -> Optional[int]:
        """
        Find best matching cluster for new document.
        
        Args:
            doc_concepts: Concepts from new document
            suggested_name: AI's suggested cluster name
            existing_clusters: Current clusters
        
        Returns:
            cluster_id if match found, None if should create new
        """
        if not existing_clusters:
            return None
        
        doc_concept_names = {c["name"].lower() for c in doc_concepts}
        
        best_match = None
        best_score = 0.0
        
        for cluster_id, cluster in existing_clusters.items():
            # Compare concepts
            cluster_concepts = {c.lower() for c in cluster.primary_concepts}
            
            if not doc_concept_names or not cluster_concepts:
                continue
            
            # Jaccard similarity
            intersection = len(doc_concept_names & cluster_concepts)
            union = len(doc_concept_names | cluster_concepts)
            similarity = intersection / union if union > 0 else 0
            
            # Boost if suggested name matches
            if suggested_name.lower() in cluster.name.lower():
                similarity += 0.2
            
            if similarity > best_score:
                best_score = similarity
                best_match = cluster_id
        
        # Only return match if above threshold
        if best_score >= self.similarity_threshold:
            logger.info(f"Found matching cluster {best_match} (similarity: {best_score:.2f})")
            return best_match
        
        return None
    
    def create_cluster(
        self,
        doc_id: int,
        name: str,
        concepts: List[Dict],
        skill_level: str,
        existing_clusters: Dict[int, Cluster]
    ) -> int:
        """Create new cluster."""
        cluster_id = max(existing_clusters.keys()) + 1 if existing_clusters else 0
        
        # Extract most common concepts (up to 5)
        concept_names = [c["name"] for c in concepts]
        primary = [name for name, _ in Counter(concept_names).most_common(5)]
        
        cluster = Cluster(
            id=cluster_id,
            name=name,
            primary_concepts=primary,
            doc_ids=[doc_id],
            skill_level=skill_level,
            doc_count=1
        )
        
        existing_clusters[cluster_id] = cluster
        logger.info(f"Created new cluster {cluster_id}: {name}")
        
        return cluster_id
    
    def add_to_cluster(
        self,
        cluster_id: int,
        doc_id: int,
        clusters: Dict[int, Cluster]
    ):
        """Add document to existing cluster."""
        if cluster_id not in clusters:
            logger.error(f"Cluster {cluster_id} not found")
            return
        
        cluster = clusters[cluster_id]
        if doc_id not in cluster.doc_ids:
            cluster.doc_ids.append(doc_id)
            cluster.doc_count = len(cluster.doc_ids)
            logger.info(f"Added doc {doc_id} to cluster {cluster_id} ({cluster.name})")
```

### Step 3.2: Integrate Clustering into Main

**Add to `backend/main.py`:**

```python
from .clustering import ClusteringEngine

clustering_engine = ClusteringEngine()

async def find_or_create_cluster(
    doc_id: int,
    suggested_cluster: str,
    concepts: List[Dict]
) -> int:
    """Find best cluster or create new one."""
    
    # Get document metadata
    meta = metadata[doc_id]
    
    # Try to find existing cluster
    cluster_id = clustering_engine.find_best_cluster(
        doc_concepts=concepts,
        suggested_name=suggested_cluster,
        existing_clusters=clusters
    )
    
    if cluster_id is not None:
        # Add to existing cluster
        clustering_engine.add_to_cluster(cluster_id, doc_id, clusters)
        return cluster_id
    
    # Create new cluster
    cluster_id = clustering_engine.create_cluster(
        doc_id=doc_id,
        name=suggested_cluster,
        concepts=concepts,
        skill_level=meta.skill_level,
        existing_clusters=clusters
    )
    
    return cluster_id
```

---

## Phase 4: Add Image Ingestion

### Step 4.1: Add OCR Dependencies

**Update `backend/requirements.txt`:**
```
# ... existing dependencies ...
pytesseract
Pillow
```

**System dependencies needed:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract
```

### Step 4.2: Create `backend/image_processor.py`

**New file:** `backend/image_processor.py`

```python
"""
Image processing and OCR for visual content ingestion.
"""

import base64
import logging
from io import BytesIO
from typing import Dict, Optional
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Process images for ingestion."""
    
    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_bytes: Raw image bytes
        
        Returns:
            Extracted text or empty string
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Extract text
            text = pytesseract.image_to_string(image)
            
            logger.info(f"Extracted {len(text)} characters from image")
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
    
    def get_image_metadata(self, image_bytes: bytes) -> Dict:
        """
        Extract image metadata.
        
        Returns:
            {
                "width": int,
                "height": int,
                "format": str,
                "mode": str,
                "size_bytes": int
            }
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            
            return {
                "width": image.width,
                "height": image.height,
                "format": image.format or "unknown",
                "mode": image.mode,
                "size_bytes": len(image_bytes)
            }
        except Exception as e:
            logger.error(f"Failed to get image metadata: {e}")
            return {}
    
    def store_image(self, image_bytes: bytes, doc_id: int) -> str:
        """
        Store image file to disk.
        
        Args:
            image_bytes: Raw image bytes
            doc_id: Document ID
        
        Returns:
            File path where image was saved
        """
        import os
        
        # Create images directory if doesn't exist
        images_dir = "stored_images"
        os.makedirs(images_dir, exist_ok=True)
        
        # Save image
        filepath = os.path.join(images_dir, f"doc_{doc_id}.png")
        
        try:
            image = Image.open(BytesIO(image_bytes))
            image.save(filepath, "PNG")
            logger.info(f"Saved image to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return ""
```

### Step 4.3: Add Image Upload Endpoint

**Add to `backend/models.py`:**
```python
class ImageUpload(BaseModel):
    """Schema for uploading images."""
    filename: str
    content: str  # base64 encoded image
    description: Optional[str] = None  # User's optional description
```

**Add to `backend/main.py`:**
```python
from .image_processor import ImageProcessor

image_processor = ImageProcessor()

@app.post("/upload_image")
async def upload_image(
    req: ImageUpload,
    current_user: User = Depends(get_current_user)
):
    """Upload and process image with OCR."""
    
    try:
        # Decode base64
        image_bytes = base64.b64decode(req.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}")
    
    async with storage_lock:
        # 1. Extract text via OCR
        extracted_text = image_processor.extract_text_from_image(image_bytes)
        
        # 2. Get image metadata
        img_meta = image_processor.get_image_metadata(image_bytes)
        
        # 3. Combine user description + OCR text
        full_content = ""
        if req.description:
            full_content += f"Description: {req.description}\n\n"
        if extracted_text:
            full_content += f"Extracted text: {extracted_text}\n\n"
        full_content += f"Image metadata: {img_meta}"
        
        # 4. Add to vector store
        doc_id = vector_store.add_document(full_content)
        documents[doc_id] = full_content
        
        # 5. Save physical image file
        image_path = image_processor.store_image(image_bytes, doc_id)
        
        # 6. Extract concepts (from OCR text + description)
        extraction = await concept_extractor.extract(full_content, "image")
        
        # 7. Create metadata
        meta = DocumentMetadata(
            doc_id=doc_id,
            owner=current_user.username,
            source_type="image",
            filename=req.filename,
            concepts=[Concept(**c) for c in extraction.get("concepts", [])],
            skill_level=extraction.get("skill_level", "unknown"),
            cluster_id=None,
            ingested_at=datetime.utcnow().isoformat(),
            content_length=len(full_content)
        )
        
        # Store image path in metadata (add to model if needed)
        meta.image_path = image_path
        
        metadata[doc_id] = meta
        
        # 8. Cluster
        cluster_id = await find_or_create_cluster(
            doc_id=doc_id,
            suggested_cluster=extraction.get("suggested_cluster", "Images"),
            concepts=extraction.get("concepts", [])
        )
        metadata[doc_id].cluster_id = cluster_id
        
        # 9. Save
        save_storage(STORAGE_PATH, documents, metadata, clusters, users)
        
        logger.info(
            f"User {current_user.username} uploaded image {req.filename} as doc {doc_id} "
            f"(OCR: {len(extracted_text)} chars, cluster: {cluster_id})"
        )
        
        return {
            "document_id": doc_id,
            "cluster_id": cluster_id,
            "ocr_text_length": len(extracted_text),
            "image_path": image_path,
            "concepts": extraction.get("concepts", [])
        }
```

---

## Phase 5: Full Content Search

### Step 5.1: Modify Vector Store Search

**Update `backend/vector_store.py`:**

```python
def search(
    self,
    query: str,
    top_k: int = 10,  # Increased default
    allowed_doc_ids: List[int] | None = None,
    return_full_content: bool = True  # NEW PARAMETER
) -> List[Tuple[int, float, str]]:
    """
    Return documents semantically similar to the query.
    
    Args:
        query: User query text
        top_k: Number of results to return
        allowed_doc_ids: Optional doc ID filter
        return_full_content: If True, return full content not snippets
    
    Returns:
        List of (document_id, similarity_score, content)
        where content is either full text or snippet
    """
    if self.vectorizer is None or self.doc_matrix is None:
        return []
    
    q_vec = self.vectorizer.transform([query])
    scores = cosine_similarity(self.doc_matrix, q_vec).flatten()
    
    candidates: List[Tuple[int, float]] = []
    for idx, score in enumerate(scores):
        doc_id = self.doc_ids[idx]
        if allowed_doc_ids is not None and doc_id not in allowed_doc_ids:
            continue
        candidates.append((idx, float(score)))
    
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    results: List[Tuple[int, float, str]] = []
    for row_idx, score in candidates[:top_k]:
        doc_id = self.doc_ids[row_idx]
        text = self.docs[doc_id]
        
        if return_full_content:
            content = text  # FULL CONTENT
        else:
            # Snippet (old behavior)
            content = text[:100] + ("..." if len(text) > 100 else "")
        
        results.append((doc_id, score, content))
    
    return results
```

### Step 5.2: Add Full Content Search Endpoint

**Add to `backend/main.py`:**

```python
@app.get("/search_full")
async def search_full_content(
    q: str,
    top_k: int = 10,
    cluster_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Search and return FULL content (not snippets).
    
    Args:
        q: Search query
        top_k: Number of results (1-50)
        cluster_id: Optional cluster filter
    
    Returns:
        {
            "results": [
                {
                    "doc_id": int,
                    "score": float,
                    "content": str (FULL),
                    "metadata": DocumentMetadata,
                    "cluster": Cluster
                }
            ],
            "grouped_by_cluster": {cluster_id: [doc_ids]}
        }
    """
    if top_k < 1 or top_k > 50:
        top_k = 10
    
    # Get user's documents
    user_doc_ids = [
        doc_id for doc_id, meta in metadata.items()
        if meta.owner == current_user.username
    ]
    
    if not user_doc_ids:
        return {"results": [], "grouped_by_cluster": {}}
    
    # Filter by cluster if specified
    if cluster_id is not None:
        user_doc_ids = [
            doc_id for doc_id in user_doc_ids
            if metadata[doc_id].cluster_id == cluster_id
        ]
    
    # Search with full content
    search_results = vector_store.search(
        query=q,
        top_k=top_k,
        allowed_doc_ids=user_doc_ids,
        return_full_content=True  # FULL CONTENT
    )
    
    # Build response with metadata
    results = []
    cluster_groups = {}
    
    for doc_id, score, content in search_results:
        meta = metadata[doc_id]
        cluster = clusters.get(meta.cluster_id) if meta.cluster_id else None
        
        results.append({
            "doc_id": doc_id,
            "score": score,
            "content": content,
            "metadata": meta.dict(),
            "cluster": cluster.dict() if cluster else None
        })
        
        # Group by cluster
        if meta.cluster_id:
            if meta.cluster_id not in cluster_groups:
                cluster_groups[meta.cluster_id] = []
            cluster_groups[meta.cluster_id].append(doc_id)
    
    return {
        "results": results,
        "grouped_by_cluster": cluster_groups
    }
```

---

## Phase 6: Build Suggestion System

### Step 6.1: Create `backend/build_suggester.py`

**New file:** `backend/build_suggester.py`

```python
"""
AI-powered build suggestion system using GPT-5 mini.
Analyzes knowledge bank and suggests viable projects.
"""

import os
import json
import logging
from typing import List, Dict
from openai import OpenAI
from .models import Cluster, DocumentMetadata, BuildSuggestion

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

class BuildSuggester:
    """Generate project suggestions from knowledge bank."""
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-5-mini"
    
    async def analyze_knowledge_bank(
        self,
        clusters: Dict[int, Cluster],
        metadata: Dict[int, DocumentMetadata],
        documents: Dict[int, str],
        max_suggestions: int = 5
    ) -> List[BuildSuggestion]:
        """
        Analyze user's knowledge and suggest builds.
        
        Args:
            clusters: User's content clusters
            metadata: Document metadata
            documents: Full document content
            max_suggestions: Number of suggestions to return
        
        Returns:
            List of BuildSuggestion objects
        """
        
        # Build knowledge summary
        knowledge_summary = self._summarize_knowledge(clusters, metadata)
        
        prompt = f"""You are analyzing a user's knowledge bank to suggest viable project builds.

KNOWLEDGE BANK SUMMARY:
{knowledge_summary}

Based on this knowledge, suggest {max_suggestions} specific, actionable projects the user could build RIGHT NOW.

For each project, provide:
1. Title (short, specific)
2. Description (2-3 sentences, what it does)
3. Feasibility (high/medium/low based on knowledge completeness)
4. Effort estimate (realistic: "2 hours", "1 day", "3 days", "1 week", etc.)
5. Required skills (list specific skills from their knowledge)
6. Missing knowledge (gaps they'd need to fill, be honest)
7. Relevant clusters (which cluster IDs to reference)
8. Starter steps (3-5 concrete first steps)
9. File structure (basic project structure)

Return ONLY valid JSON array (no markdown):
[
  {{
    "title": "Project Name",
    "description": "What it does...",
    "feasibility": "high",
    "effort_estimate": "2 days",
    "required_skills": ["skill1", "skill2"],
    "missing_knowledge": ["gap1", "gap2"],
    "relevant_clusters": [1, 3],
    "starter_steps": ["step 1", "step 2", "step 3"],
    "file_structure": "project/\\n  src/\\n  tests/\\n  README.md"
  }}
]

Be specific. Reference actual content from their knowledge. Prioritize projects they can START TODAY."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a project advisor. Return only valid JSON arrays of build suggestions."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean markdown if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            suggestions_data = json.loads(result_text)
            
            # Convert to BuildSuggestion objects
            suggestions = []
            for data in suggestions_data[:max_suggestions]:
                suggestions.append(BuildSuggestion(**data))
            
            logger.info(f"Generated {len(suggestions)} build suggestions")
            return suggestions
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Raw response: {result_text}")
            return []
        except Exception as e:
            logger.error(f"Build suggestion failed: {e}")
            return []
    
    def _summarize_knowledge(
        self,
        clusters: Dict[int, Cluster],
        metadata: Dict[int, DocumentMetadata]
    ) -> str:
        """Create text summary of knowledge bank."""
        
        if not clusters:
            return "Empty knowledge bank"
        
        lines = []
        
        for cluster_id, cluster in clusters.items():
            lines.append(f"\nCLUSTER {cluster_id}: {cluster.name}")
            lines.append(f"  - Documents: {cluster.doc_count}")
            lines.append(f"  - Skill level: {cluster.skill_level}")
            lines.append(f"  - Primary concepts: {', '.join(cluster.primary_concepts[:5])}")
            
            # Sample doc concepts from this cluster
            cluster_docs = [
                meta for meta in metadata.values()
                if meta.cluster_id == cluster_id
            ][:3]  # First 3 docs
            
            if cluster_docs:
                lines.append(f"  - Sample concepts:")
                for meta in cluster_docs:
                    concept_names = [c.name for c in meta.concepts[:3]]
                    lines.append(f"    • {meta.source_type}: {', '.join(concept_names)}")
        
        return "\n".join(lines)
```

### Step 6.2: Add "What Can I Build?" Endpoint

**Add to `backend/main.py`:**

```python
from .build_suggester import BuildSuggester

build_suggester = BuildSuggester()

@app.post("/what_can_i_build")
async def what_can_i_build(
    max_suggestions: int = 5,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze user's knowledge bank and suggest viable projects.
    
    Args:
        max_suggestions: Number of suggestions (1-10)
    
    Returns:
        {
            "suggestions": [BuildSuggestion],
            "knowledge_summary": {
                "total_docs": int,
                "total_clusters": int,
                "clusters": [Cluster]
            }
        }
    """
    if max_suggestions < 1 or max_suggestions > 10:
        max_suggestions = 5
    
    # Filter to user's content
    user_clusters = {
        cid: cluster for cid, cluster in clusters.items()
        if any(metadata[did].owner == current_user.username for did in cluster.doc_ids)
    }
    
    user_metadata = {
        did: meta for did, meta in metadata.items()
        if meta.owner == current_user.username
    }
    
    user_documents = {
        did: doc for did, doc in documents.items()
        if did in user_metadata
    }
    
    if not user_clusters:
        return {
            "suggestions": [],
            "knowledge_summary": {
                "total_docs": 0,
                "total_clusters": 0,
                "clusters": []
            }
        }
    
    # Generate suggestions
    suggestions = await build_suggester.analyze_knowledge_bank(
        clusters=user_clusters,
        metadata=user_metadata,
        documents=user_documents,
        max_suggestions=max_suggestions
    )
    
    return {
        "suggestions": [s.dict() for s in suggestions],
        "knowledge_summary": {
            "total_docs": len(user_documents),
            "total_clusters": len(user_clusters),
            "clusters": [c.dict() for c in user_clusters.values()]
        }
    }
```

---

## Phase 7: Frontend Rebuild

### Step 7.1: Update `static/index.html`

**Remove board sections, add new sections:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Bank</title>
    <style>
        /* Modern, clean styling */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: #111;
            padding: 20px;
            border-bottom: 2px solid #333;
            margin-bottom: 30px;
        }
        
        h1 {
            color: #00d4ff;
            font-size: 2rem;
        }
        
        .auth-section {
            background: #1a1a1a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 20px;
        }
        
        .sidebar {
            background: #1a1a1a;
            padding: 20px;
            border-radius: 8px;
        }
        
        .content-area {
            background: #1a1a1a;
            padding: 20px;
            border-radius: 8px;
        }
        
        .cluster-card {
            background: #2a2a2a;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            border-left: 4px solid #00d4ff;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .cluster-card:hover {
            background: #333;
            transform: translateX(5px);
        }
        
        .upload-section {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        button {
            background: #00d4ff;
            color: #000;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        button:hover {
            background: #00b8e6;
            transform: translateY(-2px);
        }
        
        button.secondary {
            background: #333;
            color: #e0e0e0;
        }
        
        button.secondary:hover {
            background: #444;
        }
        
        input, textarea {
            width: 100%;
            padding: 10px;
            background: #333;
            border: 1px solid #444;
            border-radius: 4px;
            color: #e0e0e0;
            margin-bottom: 10px;
        }
        
        .build-suggestion {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #00ff88;
        }
        
        .feasibility-high { border-left-color: #00ff88; }
        .feasibility-medium { border-left-color: #ffaa00; }
        .feasibility-low { border-left-color: #ff4444; }
        
        .search-result {
            background: #2a2a2a;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            border-left: 3px solid #666;
        }
        
        .concepts-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        
        .concept-tag {
            background: #00d4ff22;
            color: #00d4ff;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
        }
        
        .hidden { display: none; }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>💡 Knowledge Bank</h1>
            <p>Ingest → Organize → Build</p>
        </div>
    </header>
    
    <div class="container">
        <!-- Auth Section -->
        <div class="auth-section" id="authSection">
            <h2>Login / Register</h2>
            <input type="text" id="username" placeholder="Username">
            <input type="password" id="password" placeholder="Password">
            <button onclick="login()">Login</button>
            <button class="secondary" onclick="register()">Register</button>
        </div>
        
        <!-- Main Content (hidden until logged in) -->
        <div id="mainContent" class="hidden">
            
            <!-- Upload Section -->
            <div class="upload-section">
                <h2>📥 Ingest Content</h2>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
                    <button onclick="showUploadType('text')">Text</button>
                    <button onclick="showUploadType('url')">URL</button>
                    <button onclick="showUploadType('file')">File</button>
                    <button onclick="showUploadType('image')">Image</button>
                </div>
                
                <div id="uploadForms" style="margin-top: 20px;">
                    <!-- Dynamic upload forms here -->
                </div>
            </div>
            
            <div class="main-grid">
                <!-- Sidebar: Clusters -->
                <div class="sidebar">
                    <h2>📁 Clusters</h2>
                    <div id="clustersList">
                        <!-- Clusters populated here -->
                    </div>
                    
                    <button onclick="loadClusters()" style="width: 100%; margin-top: 20px;">
                        Refresh Clusters
                    </button>
                </div>
                
                <!-- Content Area -->
                <div class="content-area">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                        <h2>🔍 Search & Explore</h2>
                        <button onclick="whatCanIBuild()">What Can I Build?</button>
                    </div>
                    
                    <input type="text" id="searchQuery" placeholder="Search your knowledge...">
                    <button onclick="searchKnowledge()">Search</button>
                    
                    <div id="resultsArea" style="margin-top: 20px;">
                        <!-- Search results or build suggestions here -->
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="app.js"></script>
</body>
</html>
```

### Step 7.2: Rebuild `static/app.js`

**Complete rewrite:**

```javascript
const API_BASE = 'http://localhost:8000';
let token = null;

// ============================================================================
// AUTH
// ============================================================================

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    const res = await fetch(`${API_BASE}/token`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    });
    
    if (res.ok) {
        const data = await res.json();
        token = data.access_token;
        document.getElementById('authSection').classList.add('hidden');
        document.getElementById('mainContent').classList.remove('hidden');
        loadClusters();
    } else {
        alert('Login failed');
    }
}

async function register() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    const res = await fetch(`${API_BASE}/users`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    });
    
    if (res.ok) {
        alert('Registered! Now login.');
    } else {
        alert('Registration failed');
    }
}

// ============================================================================
// UPLOADS
// ============================================================================

function showUploadType(type) {
    const forms = document.getElementById('uploadForms');
    
    if (type === 'text') {
        forms.innerHTML = `
            <textarea id="textContent" rows="8" placeholder="Paste your content..."></textarea>
            <button onclick="uploadText()">Upload Text</button>
        `;
    } else if (type === 'url') {
        forms.innerHTML = `
            <input type="text" id="urlInput" placeholder="https://youtube.com/...">
            <button onclick="uploadUrl()">Upload URL</button>
        `;
    } else if (type === 'file') {
        forms.innerHTML = `
            <input type="file" id="fileInput">
            <button onclick="uploadFile()">Upload File</button>
        `;
    } else if (type === 'image') {
        forms.innerHTML = `
            <input type="file" id="imageInput" accept="image/*">
            <input type="text" id="imageDesc" placeholder="Optional description">
            <button onclick="uploadImage()">Upload Image</button>
        `;
    }
}

async function uploadText() {
    const content = document.getElementById('textContent').value;
    
    const res = await fetch(`${API_BASE}/upload_text`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({content})
    });
    
    if (res.ok) {
        const data = await res.json();
        alert(`Uploaded! Doc ID: ${data.document_id}, Cluster: ${data.cluster_id}`);
        loadClusters();
    } else {
        alert('Upload failed');
    }
}

async function uploadUrl() {
    const url = document.getElementById('urlInput').value;
    
    const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({url})
    });
    
    if (res.ok) {
        alert('URL upload started (may take 30-120 seconds for video)');
        loadClusters();
    } else {
        alert('Upload failed');
    }
}

async function uploadFile() {
    const file = document.getElementById('fileInput').files[0];
    const base64 = await fileToBase64(file);
    
    const res = await fetch(`${API_BASE}/upload_file`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            filename: file.name,
            content: base64
        })
    });
    
    if (res.ok) {
        alert('File uploaded!');
        loadClusters();
    } else {
        alert('Upload failed');
    }
}

async function uploadImage() {
    const file = document.getElementById('imageInput').files[0];
    const description = document.getElementById('imageDesc').value;
    const base64 = await fileToBase64(file);
    
    const res = await fetch(`${API_BASE}/upload_image`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            filename: file.name,
            content: base64,
            description: description || null
        })
    });
    
    if (res.ok) {
        const data = await res.json();
        alert(`Image uploaded! OCR extracted ${data.ocr_text_length} characters`);
        loadClusters();
    } else {
        alert('Upload failed');
    }
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// ============================================================================
// CLUSTERS
// ============================================================================

async function loadClusters() {
    const res = await fetch(`${API_BASE}/clusters`, {
        headers: {'Authorization': `Bearer ${token}`}
    });
    
    if (res.ok) {
        const data = await res.json();
        displayClusters(data.clusters);
    }
}

function displayClusters(clusters) {
    const list = document.getElementById('clustersList');
    
    if (clusters.length === 0) {
        list.innerHTML = '<p style="color: #666;">No clusters yet. Upload some content!</p>';
        return;
    }
    
    list.innerHTML = clusters.map(c => `
        <div class="cluster-card" onclick="loadCluster(${c.id})">
            <h3>${c.name}</h3>
            <p>${c.doc_count} documents • ${c.skill_level}</p>
            <div class="concepts-list">
                ${c.primary_concepts.slice(0, 3).map(concept => 
                    `<span class="concept-tag">${concept}</span>`
                ).join('')}
            </div>
        </div>
    `).join('');
}

async function loadCluster(clusterId) {
    const query = document.getElementById('searchQuery').value || '*';
    
    const res = await fetch(
        `${API_BASE}/search_full?q=${encodeURIComponent(query)}&cluster_id=${clusterId}&top_k=20`,
        {headers: {'Authorization': `Bearer ${token}`}}
    );
    
    if (res.ok) {
        const data = await res.json();
        displaySearchResults(data.results);
    }
}

// ============================================================================
// SEARCH
// ============================================================================

async function searchKnowledge() {
    const query = document.getElementById('searchQuery').value;
    
    const res = await fetch(
        `${API_BASE}/search_full?q=${encodeURIComponent(query)}&top_k=20`,
        {headers: {'Authorization': `Bearer ${token}`}}
    );
    
    if (res.ok) {
        const data = await res.json();
        displaySearchResults(data.results);
    }
}

function displaySearchResults(results) {
    const area = document.getElementById('resultsArea');
    
    if (results.length === 0) {
        area.innerHTML = '<p style="color: #666;">No results found</p>';
        return;
    }
    
    area.innerHTML = `<h3>Search Results (${results.length})</h3>` +
        results.map(r => `
            <div class="search-result">
                <div style="display: flex; justify-content: space-between;">
                    <strong>Doc ${r.doc_id}</strong>
                    <span style="color: #888;">Score: ${r.score.toFixed(3)}</span>
                </div>
                <p style="font-size: 0.9rem; color: #aaa; margin: 5px 0;">
                    ${r.metadata.source_type} • 
                    Cluster: ${r.cluster?.name || 'None'} • 
                    ${r.metadata.skill_level}
                </p>
                <div class="concepts-list">
                    ${r.metadata.concepts.slice(0, 5).map(c => 
                        `<span class="concept-tag">${c.name}</span>`
                    ).join('')}
                </div>
                <details style="margin-top: 10px;">
                    <summary style="cursor: pointer; color: #00d4ff;">View Full Content</summary>
                    <pre style="background: #111; padding: 10px; border-radius: 4px; margin-top: 10px; white-space: pre-wrap; max-height: 400px; overflow-y: auto;">${r.content}</pre>
                </details>
            </div>
        `).join('');
}

// ============================================================================
// BUILD SUGGESTIONS
// ============================================================================

async function whatCanIBuild() {
    const res = await fetch(`${API_BASE}/what_can_i_build`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({max_suggestions: 5})
    });
    
    if (res.ok) {
        const data = await res.json();
        displayBuildSuggestions(data.suggestions, data.knowledge_summary);
    } else {
        alert('Failed to generate suggestions');
    }
}

function displayBuildSuggestions(suggestions, summary) {
    const area = document.getElementById('resultsArea');
    
    if (suggestions.length === 0) {
        area.innerHTML = `
            <p style="color: #666;">
                Not enough knowledge yet to suggest builds. 
                Upload more content (${summary.total_docs} docs so far).
            </p>
        `;
        return;
    }
    
    area.innerHTML = `
        <h3>💡 Build Suggestions</h3>
        <p style="color: #aaa; margin-bottom: 20px;">
            Based on ${summary.total_docs} documents across ${summary.total_clusters} clusters
        </p>
    ` + suggestions.map((s, i) => `
        <div class="build-suggestion feasibility-${s.feasibility}">
            <h3>${i + 1}. ${s.title}</h3>
            <p style="margin: 10px 0;">${s.description}</p>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 15px 0;">
                <div>
                    <strong>Feasibility:</strong> 
                    <span class="concept-tag">${s.feasibility}</span>
                </div>
                <div>
                    <strong>Effort:</strong> ${s.effort_estimate}
                </div>
            </div>
            
            <div style="margin: 15px 0;">
                <strong>Required Skills:</strong>
                <div class="concepts-list">
                    ${s.required_skills.map(skill => 
                        `<span class="concept-tag">${skill}</span>`
                    ).join('')}
                </div>
            </div>
            
            ${s.missing_knowledge.length > 0 ? `
                <div style="margin: 15px 0;">
                    <strong style="color: #ffaa00;">Missing Knowledge:</strong>
                    <ul style="margin-left: 20px; color: #aaa;">
                        ${s.missing_knowledge.map(gap => `<li>${gap}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            <details style="margin-top: 15px;">
                <summary style="cursor: pointer; color: #00d4ff; font-weight: 600;">
                    View Starter Steps & File Structure
                </summary>
                <div style="background: #111; padding: 15px; border-radius: 4px; margin-top: 10px;">
                    <h4>First Steps:</h4>
                    <ol style="margin-left: 20px;">
                        ${s.starter_steps.map(step => `<li>${step}</li>`).join('')}
                    </ol>
                    
                    ${s.file_structure ? `
                        <h4 style="margin-top: 15px;">File Structure:</h4>
                        <pre style="background: #0a0a0a; padding: 10px; border-radius: 4px;">${s.file_structure}</pre>
                    ` : ''}
                </div>
            </details>
            
            <button onclick="startBuild(${i})" style="margin-top: 15px;">
                Start This Project
            </button>
        </div>
    `).join('');
}

function startBuild(index) {
    alert('Project starter functionality coming soon!\n\nFor now, use the steps shown above to begin building.');
}

// ============================================================================
// INIT
// ============================================================================

// Check if already logged in
if (localStorage.getItem('token')) {
    token = localStorage.getItem('token');
    document.getElementById('authSection').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    loadClusters();
}

// Save token on successful login
const originalLogin = login;
login = async function() {
    await originalLogin();
    if (token) {
        localStorage.setItem('token', token);
    }
};
```

### Step 7.3: Add Clusters Endpoint

**Add to `backend/main.py`:**

```python
@app.get("/clusters")
async def get_clusters(
    current_user: User = Depends(get_current_user)
):
    """Get user's clusters."""
    
    user_clusters = []
    
    for cluster_id, cluster in clusters.items():
        # Check if any docs in cluster belong to user
        has_user_docs = any(
            metadata.get(doc_id) and metadata[doc_id].owner == current_user.username
            for doc_id in cluster.doc_ids
        )
        
        if has_user_docs:
            user_clusters.append(cluster.dict())
    
    return {
        "clusters": user_clusters,
        "total": len(user_clusters)
    }
```

---

## Phase 8: Testing & Validation

### Step 8.1: Manual Test Checklist

**Authentication:**
- [ ] Register new user
- [ ] Login with credentials
- [ ] Token persists across page refresh

**Text Upload:**
- [ ] Upload plain text
- [ ] Concepts extracted
- [ ] Assigned to cluster
- [ ] Searchable

**URL Upload:**
- [ ] Web article uploads
- [ ] Content extracted
- [ ] Concepts extracted
- [ ] Clustered

**YouTube Upload:**
- [ ] Video transcribed (30-120s wait)
- [ ] Transcript searchable
- [ ] Concepts extracted

**PDF Upload:**
- [ ] Text extracted
- [ ] Concepts extracted
- [ ] Full content stored

**Image Upload:**
- [ ] OCR extracts text
- [ ] Image stored to disk
- [ ] Searchable by OCR text
- [ ] Can view image later

**Clustering:**
- [ ] Similar content grouped together
- [ ] New cluster created when needed
- [ ] Cluster concepts accurate
- [ ] Cluster names meaningful

**Search:**
- [ ] Returns full content
- [ ] Grouped by cluster
- [ ] Ranked by relevance
- [ ] Filter by cluster works

**Build Suggestions:**
- [ ] Analyzes knowledge accurately
- [ ] Suggestions are realistic
- [ ] Feasibility scores make sense
- [ ] Starter steps are actionable
- [ ] Missing knowledge identified

### Step 8.2: API Cost Validation

**Run 100 test ingestions:**
```bash
# Expected costs:
# 100 ingestions @ $0.00018 each = $0.018
# 10 build analyses @ $0.0006 each = $0.006
# Total: ~$0.024
```

**Monitor via OpenAI dashboard:**
- Verify GPT-5 nano being used
- Check actual token counts
- Confirm costs match estimates

### Step 8.3: Performance Testing

**Load testing:**
- Upload 100 documents
- Measure clustering time
- Verify search speed
- Check build analysis time (should be <5 seconds)

**Storage size:**
- 100 docs × 10KB avg = 1MB
- JSON storage should remain <5MB for 1000 docs

---

## API Cost Analysis

### Per-Operation Costs

**Ingestion (GPT-5 nano):**
- Average: 2000 input + 200 output tokens
- Cost: $0.00018 per ingestion
- 1000 ingestions: $0.18

**Build Analysis (GPT-5 mini):**
- Average: 2000 input + 500 output tokens
- Cost: $0.00060 per analysis
- 100 analyses: $0.06

**AI Generation/RAG (GPT-5 mini):**
- Average: 3000 input + 500 output tokens
- Cost: $0.00095 per generation
- 1000 generations: $0.95

### Monthly Cost Projections

**Light User (10 ingestions, 5 analyses, 20 generations/month):**
- Ingestions: $0.002
- Analyses: $0.003
- Generations: $0.019
- **Total: $0.024/month**

**Medium User (100 ingestions, 20 analyses, 200 generations/month):**
- Ingestions: $0.018
- Analyses: $0.012
- Generations: $0.190
- **Total: $0.220/month**

**Heavy User (1000 ingestions, 100 analyses, 2000 generations/month):**
- Ingestions: $0.180
- Analyses: $0.060
- Generations: $1.900
- **Total: $2.140/month**

**Comparison to old system (GPT-4o):**
- Old cost (1000 generations): $7.00
- New cost (1000 generations): $0.95
- **Savings: 86%**

---

## File Structure

### Final Project Structure

```
syncboard_project/
├── .env                                # API keys
├── README.md                          # Updated docs
├── BLUEPRINT.md                       # This file
├── backend/
│   ├── __init__.py
│   ├── main.py                       # ✅ MODIFIED: Removed boards, added new endpoints
│   ├── models.py                     # ✅ MODIFIED: New models (Concept, Cluster, BuildSuggestion)
│   ├── storage.py                    # ✅ MODIFIED: Simplified storage
│   ├── vector_store.py               # ✅ MODIFIED: Full content search
│   ├── ingest.py                     # ✅ KEEP: Existing ingestion
│   ├── ai_generation_real.py         # ✅ MODIFIED: Switch to GPT-5 mini
│   ├── concept_extractor.py          # ✨ NEW: GPT-5 nano concept extraction
│   ├── clustering.py                 # ✨ NEW: Auto-clustering engine
│   ├── image_processor.py            # ✨ NEW: OCR and image handling
│   ├── build_suggester.py            # ✨ NEW: GPT-5 mini build analysis
│   ├── requirements.txt              # ✅ UPDATED: Add pytesseract, Pillow
│   └── stored_images/                # ✨ NEW: Image storage directory
└── static/
    ├── index.html                     # ✅ REBUILT: New UI
    └── app.js                         # ✅ REBUILT: New frontend logic
```

### Files Modified Summary

**Major Changes:**
- `main.py`: -300 lines (boards removed), +200 lines (new endpoints)
- `models.py`: -50 lines (boards), +150 lines (new models)
- `storage.py`: Complete rewrite (~100 lines)
- `index.html`: Complete rebuild (~250 lines)
- `app.js`: Complete rebuild (~400 lines)

**New Files:**
- `concept_extractor.py`: ~150 lines
- `clustering.py`: ~200 lines
- `image_processor.py`: ~120 lines
- `build_suggester.py`: ~180 lines

**Total Code:**
- Before: ~1200 lines
- After: ~1800 lines
- Net increase: +600 lines

---

## Success Criteria

### Must Have (MVP)
- [ ] All board code removed
- [ ] Concept extraction on every ingestion
- [ ] Auto-clustering working
- [ ] Image ingestion with OCR
- [ ] Full content search (not snippets)
- [ ] "What Can I Build?" analysis
- [ ] GPT-5 nano for ingestion
- [ ] GPT-5 mini for generation

### Should Have
- [ ] Cluster merging (if two clusters become similar)
- [ ] Manual cluster renaming
- [ ] Export cluster as markdown
- [ ] Cost tracking dashboard
- [ ] Batch ingestion (multiple files)

### Nice to Have
- [ ] Visual cluster graph
- [ ] Image gallery view
- [ ] Code generation from build suggestions
- [ ] Project templates library
- [ ] Share knowledge publicly

---

## Timeline Estimate

### Day 1: Core Refactoring (6-8 hours)
- Remove board system (2 hours)
- Add concept extraction (2 hours)
- Add clustering system (2-3 hours)
- Update storage (1 hour)

### Day 2: Features (6-8 hours)
- Image ingestion + OCR (3 hours)
- Full content search (1 hour)
- Build suggestion system (3 hours)
- Testing & fixes (1 hour)

### Day 3: Frontend (4-6 hours)
- Rebuild HTML (2 hours)
- Rebuild JavaScript (2-3 hours)
- Polish & testing (1 hour)

**Total: 16-22 hours** (2-3 focused days)

---

## Next Steps After Blueprint Review

1. **Review this blueprint** - Does it match your vision?
2. **Approve or request changes** - Any sections need modification?
3. **Start Phase 1** - Begin removing board system
4. **Iterate** - Build phase by phase, test as we go

Ready to start building?

---

**Blueprint Version:** 1.0  
**Created:** November 12, 2025  
**Status:** Awaiting approval  
**Estimated Completion:** 2-3 days focused work
