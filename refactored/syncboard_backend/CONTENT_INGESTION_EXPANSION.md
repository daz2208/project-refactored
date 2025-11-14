# Content Ingestion Expansion - Proposed File Types

**Current Status:** 2025-11-14
**Purpose:** Expand SyncBoard's content ingestion to support more file formats

---

## Currently Supported Formats ✅

### Video & Audio (Whisper Transcription)
- ✅ **YouTube** videos (with audio compression for large files)
- ✅ **TikTok** videos
- ✅ **Audio files**: .mp3, .wav, .m4a, .ogg, .flac

### Documents (Text Extraction)
- ✅ **PDF** documents (pypdf)
- ✅ **Word** documents (.docx via python-docx)
- ✅ **Plain text**: .txt, .md, .csv, .json

### Web Content
- ✅ **Web articles** (BeautifulSoup HTML extraction)

### Images
- ✅ **Image OCR** (pytesseract for text extraction from screenshots/scans)

---

## Proposed Additions

### 🎯 Priority 1: Office Documents (High Value, Easy Implementation)

#### Excel Spreadsheets
**Files:** `.xlsx`, `.xls`, `.ods` (OpenOffice Calc)
**Use Case:** Extract data tables, formulas, notes from financial reports, datasets
**Library:** `openpyxl` (xlsx), `xlrd` (xls), `odfpy` (ods)
**Complexity:** ⭐⭐ Low-Medium

**Implementation:**
```python
def extract_excel_text(content_bytes: bytes, filename: str) -> str:
    """Extract text from Excel spreadsheet."""
    from openpyxl import load_workbook
    import io

    wb = load_workbook(io.BytesIO(content_bytes))
    text_parts = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        text_parts.append(f"=== Sheet: {sheet_name} ===\n")

        # Extract cell values
        for row in sheet.iter_rows(values_only=True):
            row_text = " | ".join(str(cell) if cell else "" for cell in row)
            if row_text.strip(" |"):
                text_parts.append(row_text)

    return f"EXCEL SPREADSHEET: {filename}\n\n" + "\n".join(text_parts)
```

**Value:**
- Financial reports, budget spreadsheets
- Data analysis results
- Product roadmaps in spreadsheets
- Research data tables

---

#### PowerPoint Presentations
**Files:** `.pptx`, `.ppt`, `.odp` (OpenOffice Impress)
**Use Case:** Extract slides, speaker notes from presentations, lectures
**Library:** `python-pptx` (pptx), `odfpy` (odp)
**Complexity:** ⭐⭐ Low-Medium

**Implementation:**
```python
def extract_powerpoint_text(content_bytes: bytes, filename: str) -> str:
    """Extract text from PowerPoint presentation."""
    from pptx import Presentation
    import io

    prs = Presentation(io.BytesIO(content_bytes))
    text_parts = []

    for i, slide in enumerate(prs.slides, 1):
        text_parts.append(f"--- Slide {i} ---")

        # Extract text from shapes
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                text_parts.append(shape.text)

        # Extract speaker notes
        if slide.has_notes_slide:
            notes_frame = slide.notes_slide.notes_text_frame
            if notes_frame.text:
                text_parts.append(f"[Speaker Notes: {notes_frame.text}]")

    return f"POWERPOINT PRESENTATION ({len(prs.slides)} slides)\n\n" + "\n\n".join(text_parts)
```

**Value:**
- Conference presentations
- Educational lectures
- Product pitch decks
- Training materials

---

### 🔥 Priority 2: Code & Technical Files (Developer-Focused)

#### Jupyter Notebooks
**Files:** `.ipynb`
**Use Case:** Extract code, markdown, and output from data science notebooks
**Library:** Built-in `json` module
**Complexity:** ⭐ Very Low (JSON parsing)

**Implementation:**
```python
def extract_jupyter_notebook(content_bytes: bytes, filename: str) -> str:
    """Extract content from Jupyter notebook."""
    import json

    notebook = json.loads(content_bytes.decode('utf-8'))
    text_parts = [f"JUPYTER NOTEBOOK: {filename}\n"]

    for i, cell in enumerate(notebook.get('cells', []), 1):
        cell_type = cell.get('cell_type', 'unknown')
        source = ''.join(cell.get('source', []))

        if cell_type == 'code':
            text_parts.append(f"[Code Cell {i}]\n{source}")

            # Extract outputs if present
            outputs = cell.get('outputs', [])
            for output in outputs:
                if 'text' in output:
                    text_parts.append(f"[Output]\n{''.join(output['text'])}")

        elif cell_type == 'markdown':
            text_parts.append(f"[Markdown {i}]\n{source}")

    return "\n\n".join(text_parts)
```

**Value:** ⭐⭐⭐⭐⭐ Very High
- Machine learning experiments
- Data analysis workflows
- Educational notebooks
- Research code + documentation

---

#### Code Files
**Files:** `.py`, `.js`, `.java`, `.cpp`, `.go`, `.rs`, `.tsx`, `.jsx`, etc.
**Use Case:** Index code repositories for learning, documentation
**Library:** None needed (text files with syntax awareness)
**Complexity:** ⭐ Very Low

**Implementation:**
```python
CODE_EXTENSIONS = {
    '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
    '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.h': 'Header',
    '.go': 'Go', '.rs': 'Rust', '.rb': 'Ruby', '.php': 'PHP',
    '.swift': 'Swift', '.kt': 'Kotlin', '.scala': 'Scala',
    '.sql': 'SQL', '.sh': 'Shell Script', '.yaml': 'YAML',
}

def ingest_code_file(filename: str, content_bytes: bytes) -> str:
    """Process source code file with metadata."""
    ext = Path(filename).suffix.lower()
    language = CODE_EXTENSIONS.get(ext, 'Unknown')

    try:
        code = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        code = content_bytes.decode('latin-1', errors='ignore')

    # Extract docstrings/comments (simple heuristic)
    lines = code.split('\n')
    loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

    return f"""SOURCE CODE: {filename}
Language: {language}
Lines of Code: {loc}

CODE:
{code}
"""
```

**Value:** ⭐⭐⭐⭐ High
- Code learning resources
- Tutorial code examples
- Open source project exploration
- Personal code library

---

#### LaTeX Documents
**Files:** `.tex`
**Use Case:** Academic papers, mathematical documents
**Library:** `pylatexenc` (optional, or just extract as text)
**Complexity:** ⭐⭐ Low-Medium

**Value:** ⭐⭐⭐ Medium (Academic users)

---

### 📦 Priority 3: Archives & Containers

#### ZIP Archives
**Files:** `.zip`
**Use Case:** Extract and process all files within archive
**Library:** Built-in `zipfile`
**Complexity:** ⭐⭐⭐ Medium (recursive processing)

**Implementation:**
```python
def ingest_zip_archive(content_bytes: bytes, filename: str) -> str:
    """Extract and process ZIP archive contents."""
    import zipfile
    import io

    zip_file = zipfile.ZipFile(io.BytesIO(content_bytes))
    text_parts = [f"ZIP ARCHIVE: {filename}\nContains {len(zip_file.namelist())} files\n"]

    for file_info in zip_file.infolist():
        if file_info.is_dir():
            continue

        # Skip large files (> 10MB per file)
        if file_info.file_size > 10 * 1024 * 1024:
            text_parts.append(f"⚠️  Skipped (too large): {file_info.filename}")
            continue

        try:
            file_content = zip_file.read(file_info.filename)
            # Recursively process supported file types
            extracted_text = ingest_upload_file(file_info.filename, file_content)
            text_parts.append(f"\n=== {file_info.filename} ===\n{extracted_text}")
        except Exception as e:
            text_parts.append(f"⚠️  Failed: {file_info.filename} - {e}")

    return "\n\n".join(text_parts)
```

**Value:** ⭐⭐⭐⭐ High
- Code projects (download GitHub zip)
- Document collections
- Course materials bundles
- Backup archives

---

### 📚 Priority 4: E-Books & Specialized Formats

#### EPUB Books
**Files:** `.epub`
**Use Case:** Digital books, technical ebooks
**Library:** `ebooklib`
**Complexity:** ⭐⭐⭐ Medium

**Implementation:**
```python
def extract_epub_text(content_bytes: bytes, filename: str) -> str:
    """Extract text from EPUB book."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    import io

    book = epub.read_epub(io.BytesIO(content_bytes))
    text_parts = []

    # Extract metadata
    title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else filename
    author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else 'Unknown'

    text_parts.append(f"EPUB BOOK: {title}\nAuthor: {author}\n")

    # Extract chapters
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            if text:
                text_parts.append(text)

    return "\n\n".join(text_parts)
```

**Value:** ⭐⭐⭐⭐ High
- Technical ebooks
- Educational materials
- Reference books
- Novel study notes

---

#### Subtitle Files
**Files:** `.srt`, `.vtt`, `.ass`
**Use Case:** Video transcripts, language learning
**Library:** `pysrt` (srt), built-in parsing (vtt)
**Complexity:** ⭐ Very Low

**Implementation:**
```python
def extract_subtitles(content_bytes: bytes, filename: str) -> str:
    """Extract text from subtitle files."""
    ext = Path(filename).suffix.lower()

    if ext == '.srt':
        import pysrt
        import io
        subs = pysrt.open(io.BytesIO(content_bytes), encoding='utf-8')
        text = "\n".join([sub.text for sub in subs])
        return f"SUBTITLE FILE: {filename}\n\n{text}"

    elif ext == '.vtt':
        # WebVTT format (simple parsing)
        text = content_bytes.decode('utf-8')
        lines = [l for l in text.split('\n') if l.strip() and not l.startswith('WEBVTT') and '-->' not in l]
        return f"SUBTITLE FILE: {filename}\n\n" + "\n".join(lines)
```

**Value:** ⭐⭐⭐ Medium
- Video transcripts
- Language learning
- Accessibility content

---

### 🌐 Priority 5: Cloud & API Integrations

#### Google Drive Files
**API:** Google Drive API
**Files:** Google Docs, Sheets, Slides
**Complexity:** ⭐⭐⭐⭐ High (OAuth, API setup)

**Value:** ⭐⭐⭐⭐⭐ Very High (collaboration tools)

---

#### Notion Pages
**API:** Notion API
**Complexity:** ⭐⭐⭐⭐ High
**Value:** ⭐⭐⭐⭐ High (popular note-taking)

---

#### GitHub Repositories
**API:** GitHub API
**Use Case:** Clone and index entire repos
**Complexity:** ⭐⭐⭐⭐ High
**Value:** ⭐⭐⭐⭐⭐ Very High (code learning)

**Implementation Concept:**
```python
def ingest_github_repo(repo_url: str) -> str:
    """Clone and index GitHub repository."""
    import requests
    import base64

    # Parse repo URL: https://github.com/user/repo
    parts = repo_url.rstrip('/').split('/')
    owner, repo = parts[-2], parts[-1]

    # Fetch repo tree via API
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
    response = requests.get(api_url)
    tree = response.json()

    text_parts = [f"GITHUB REPOSITORY: {owner}/{repo}\n"]

    # Process each file
    for item in tree.get('tree', []):
        if item['type'] == 'blob' and item['size'] < 1024*1024:  # < 1MB
            # Fetch file content
            file_response = requests.get(item['url'])
            content = base64.b64decode(file_response.json()['content'])

            # Process file based on extension
            extracted = ingest_upload_file(item['path'], content)
            text_parts.append(f"\n=== {item['path']} ===\n{extracted}")

    return "\n\n".join(text_parts)
```

---

## Implementation Priority Matrix

| File Type | Value | Complexity | Dependencies | Priority |
|-----------|-------|------------|--------------|----------|
| **Excel** | ⭐⭐⭐⭐ | ⭐⭐ | openpyxl | **HIGH** |
| **PowerPoint** | ⭐⭐⭐⭐ | ⭐⭐ | python-pptx | **HIGH** |
| **Jupyter** | ⭐⭐⭐⭐⭐ | ⭐ | None | **HIGH** |
| **Code Files** | ⭐⭐⭐⭐ | ⭐ | None | **HIGH** |
| **ZIP Archives** | ⭐⭐⭐⭐ | ⭐⭐⭐ | None (built-in) | **MEDIUM** |
| **EPUB** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ebooklib | **MEDIUM** |
| **Subtitles** | ⭐⭐⭐ | ⭐ | pysrt | **MEDIUM** |
| **LaTeX** | ⭐⭐⭐ | ⭐⭐ | pylatexenc | **LOW** |
| **Google Drive** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | google-api | **LOW** (complex) |
| **GitHub Repos** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | requests | **LOW** (complex) |

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 hours)
1. ✅ **Jupyter Notebooks** (`.ipynb`) - JSON parsing, no new deps
2. ✅ **Code Files** (`.py`, `.js`, etc.) - Text files, no new deps
3. ✅ **YAML/TOML** (`.yaml`, `.toml`) - Config files

### Phase 2: Office Documents (2-3 hours)
4. ✅ **Excel** (`.xlsx`) - `pip install openpyxl`
5. ✅ **PowerPoint** (`.pptx`) - `pip install python-pptx`

### Phase 3: Archives & Books (3-4 hours)
6. ✅ **ZIP Archives** (`.zip`) - Built-in zipfile
7. ✅ **EPUB Books** (`.epub`) - `pip install ebooklib`
8. ✅ **Subtitles** (`.srt`, `.vtt`) - `pip install pysrt`

### Phase 4: Cloud Integrations (1-2 weeks)
9. 🔄 **Google Drive** - OAuth setup, API integration
10. 🔄 **GitHub Repositories** - API integration, recursive processing
11. 🔄 **Notion** - API integration

---

## Updated Dependencies

```txt
# Current dependencies
yt-dlp
pypdf
beautifulsoup4
python-docx

# Phase 1: No new deps needed
# (JSON, text files)

# Phase 2: Office documents
openpyxl         # Excel
python-pptx      # PowerPoint

# Phase 3: Books & archives
ebooklib         # EPUB books
pysrt            # Subtitle files
# zipfile (built-in)

# Phase 4: Cloud APIs
google-api-python-client   # Google Drive
google-auth-httplib2
google-auth-oauthlib
PyGithub                   # GitHub API
notion-client              # Notion API
```

---

## Security Considerations

### File Size Limits
- **Single file max:** 50MB (current limit)
- **ZIP archive max:** 100MB total, 10MB per file
- **GitHub repo max:** 500 files, 1MB per file

### Malicious File Protection
1. **Sandboxed processing:** Process files in temporary directories
2. **File type validation:** Verify magic bytes, not just extensions
3. **Timeout limits:** 60s per file processing
4. **Resource limits:** Memory limit for large files
5. **Archive bomb protection:** Limit ZIP extraction depth/size

### Input Validation
```python
# Add to sanitization.py
def validate_file_upload(filename: str, content_bytes: bytes, max_size: int = MAX_UPLOAD_SIZE_BYTES):
    """Validate uploaded file before processing."""
    # Check size
    if len(content_bytes) > max_size:
        raise HTTPException(400, f"File too large. Max: {max_size/(1024*1024)}MB")

    # Verify file extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type not supported: {ext}")

    # Check magic bytes (prevent extension spoofing)
    magic = content_bytes[:8]
    if not verify_magic_bytes(ext, magic):
        raise HTTPException(400, "File content doesn't match extension")
```

---

## Testing Strategy

### Unit Tests
```python
# tests/test_ingestion_expanded.py

def test_jupyter_notebook_extraction():
    """Test Jupyter notebook content extraction."""
    with open('tests/fixtures/sample.ipynb', 'rb') as f:
        content = f.read()

    result = extract_jupyter_notebook(content, 'sample.ipynb')
    assert 'JUPYTER NOTEBOOK' in result
    assert '[Code Cell' in result
    assert '[Markdown' in result

def test_excel_extraction():
    """Test Excel spreadsheet extraction."""
    # Create sample Excel file
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws['A1'] = 'Hello'
    ws['B1'] = 'World'

    import io
    buffer = io.BytesIO()
    wb.save(buffer)

    result = extract_excel_text(buffer.getvalue(), 'test.xlsx')
    assert 'Hello' in result
    assert 'World' in result

def test_zip_archive_extraction():
    """Test ZIP archive recursive extraction."""
    # Create sample ZIP with multiple files
    import zipfile, io
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('file1.txt', 'Content 1')
        zf.writestr('file2.md', '# Header')

    result = ingest_zip_archive(zip_buffer.getvalue(), 'test.zip')
    assert 'file1.txt' in result
    assert 'Content 1' in result
    assert '# Header' in result
```

---

## Performance Metrics

### Expected Processing Times (on average hardware)
- **Jupyter Notebook** (1MB): ~0.1s (JSON parse)
- **Code File** (100KB): ~0.05s (text read)
- **Excel** (5MB, 100 rows): ~2s (openpyxl)
- **PowerPoint** (10MB, 50 slides): ~5s (python-pptx)
- **ZIP Archive** (20MB, 100 files): ~30s (recursive)
- **EPUB Book** (2MB, 300 pages): ~10s (HTML parsing)
- **GitHub Repo** (500 files): ~60s (API calls)

---

## User-Facing Changes

### API Endpoint Updates

No changes needed! Existing endpoints already support new file types:

```python
# POST /upload_file
# Already handles any file extension - just add to supported list

ALLOWED_EXTENSIONS = {
    # Current
    '.txt', '.md', '.csv', '.json',
    '.pdf', '.docx',
    '.mp3', '.wav', '.m4a', '.ogg', '.flac',

    # New - Phase 1
    '.ipynb', '.py', '.js', '.java', '.go', '.rs',
    '.yaml', '.yml', '.toml',

    # New - Phase 2
    '.xlsx', '.xls', '.pptx', '.ppt',

    # New - Phase 3
    '.zip', '.epub', '.srt', '.vtt'
}
```

### Frontend Changes

Update file upload picker to show new supported formats:

```javascript
// Before
accept=".pdf,.docx,.txt,.md,.mp3,.wav"

// After
accept=".pdf,.docx,.txt,.md,.mp3,.wav,.xlsx,.pptx,.ipynb,.py,.js,.zip,.epub"
```

---

## Example Usage

### Jupyter Notebook
```bash
curl -X POST http://localhost:8000/upload_file \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "filename": "data_analysis.ipynb",
    "content": "<base64_encoded_notebook>",
    "description": "Machine learning experiment results"
  }'
```

**Result:**
- Extracts code cells, markdown, and outputs
- Auto-clusters with other ML/data science content
- Searchable by concepts: "pandas", "scikit-learn", "regression"

### GitHub Repository
```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "url": "https://github.com/fastapi/fastapi",
    "description": "FastAPI framework source code"
  }'
```

**Result:**
- Clones entire repo (up to 500 files)
- Processes `.py`, `.md`, `.rst` files
- Auto-clusters by modules
- Concepts: "FastAPI", "Pydantic", "ASGI", "routing"

---

## ROI Analysis

### Development Time Investment
- **Phase 1** (Quick Wins): 2 hours → Jupyter + Code files
- **Phase 2** (Office): 3 hours → Excel + PowerPoint
- **Phase 3** (Archives): 4 hours → ZIP + EPUB
- **Total MVP**: ~9 hours of development

### User Value
- **Before**: 5 supported file types (PDF, DOCX, TXT, MP3, images)
- **After Phase 1**: 15+ types (adds Jupyter, all code files)
- **After Phase 2**: 20+ types (adds Office suite)
- **After Phase 3**: 25+ types (adds archives, ebooks)

### Use Case Expansion
- **Current**: Documents and media
- **Phase 1**: Developers (code, notebooks)
- **Phase 2**: Business users (Excel, PowerPoint)
- **Phase 3**: Researchers (EPUB, archives)

---

## Next Steps

**Option A: Implement Quick Wins (Recommended)**
1. Add Jupyter notebook support (`.ipynb`)
2. Add code file support (`.py`, `.js`, etc.)
3. Test with sample files
4. Deploy and gather user feedback

**Option B: Comprehensive Update**
1. Implement all Phases 1-3
2. Add comprehensive tests
3. Update documentation
4. Deploy full feature set

**Option C: Start with Office Suite**
1. Focus on Excel and PowerPoint first
2. High business user value
3. Moderate complexity

---

**Which direction would you like to explore first?**

Let me know and I can start implementing immediately! 🚀
