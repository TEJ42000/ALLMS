# 📄 Text Extraction Service

## Overview

The Text Extraction Service provides unified text extraction from all course material file types. This enables LLM-powered functionality like quizzes, summaries, study guides, and semantic search.

**Location**: `app/services/text_extractor.py`

## ⚠️ Important: Use This Service for All Document Processing!

When building features that handle documents (uploads, processing, indexing), **always use this service** to extract text. This ensures:

1. **Consistent text extraction** across all file types
2. **Proper handling** of edge cases (fake DOCX files, slide archives disguised as PDFs)
3. **OCR support** for images
4. **Centralized error handling**

## Supported File Types

| File Type | Extension(s) | Extraction Method | Notes |
|-----------|--------------|-------------------|-------|
| **PDF** | `.pdf` | PyMuPDF (fitz) | Real PDFs with embedded text |
| **Slide Archive** | `.pdf` | Custom ZIP parser | ZIP files disguised as PDFs containing JPEG slides + text |
| **Images** | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff` | Tesseract OCR | Requires tesseract installed |
| **Word Documents** | `.docx` | python-docx | Falls back to text if not a real DOCX |
| **Markdown** | `.md` | Direct read | UTF-8 with fallback |
| **Plain Text** | `.txt` | Direct read | UTF-8 with fallback |
| **HTML** | `.html`, `.htm` | BeautifulSoup | Scripts/styles removed |
| **JSON** | `.json` | JSON parser | Extracts string values |

## Quick Start

### Single File Extraction

```python
from pathlib import Path
from app.services.text_extractor import extract_text

# Extract text from any supported file
result = extract_text(Path("Materials/Course_Materials/lecture.pdf"))

if result.success:
    print(f"Extracted {len(result.text)} characters")
    print(f"File type: {result.file_type}")
    print(f"Pages: {len(result.pages) if result.pages else 'N/A'}")
else:
    print(f"Extraction failed: {result.error}")
```

### Batch Extraction

```python
from pathlib import Path
from app.services.text_extractor import extract_all_from_folder, get_extraction_summary

# Extract from all files in a folder
results = extract_all_from_folder(Path("Materials/Course_Materials/LLS"), recursive=True)

# Get summary statistics
summary = get_extraction_summary(results)
print(f"Extracted {summary['successful']}/{summary['total_files']} files")
print(f"Total characters: {summary['total_characters']}")
```

### Detect File Type

```python
from pathlib import Path
from app.services.text_extractor import detect_file_type

file_type = detect_file_type(Path("Materials/some_file.pdf"))
# Returns: 'pdf', 'slide_archive', 'image', 'docx', 'markdown', 'text', 'html', 'json', or 'unknown'
```

## ExtractionResult Object

Every extraction returns an `ExtractionResult` dataclass:

```python
@dataclass
class ExtractionResult:
    file_path: str          # Path to the file
    file_type: str          # Detected file type
    text: str               # Extracted text content
    success: bool           # Whether extraction succeeded
    error: Optional[str]    # Error message if failed
    metadata: Dict          # Additional metadata (page count, dimensions, etc.)
    pages: Optional[List]   # Page-by-page content for multi-page documents
```

## API Endpoints

### Extract Single File
```
GET /api/admin/courses/materials/extract/{file_path}
```

**Example:**
```bash
curl "http://localhost:8000/api/admin/courses/materials/extract/Course_Materials/LLS/Lectures/lecture.pdf"
```

**Response:**
```json
{
  "file_path": "Materials/Course_Materials/LLS/Lectures/lecture.pdf",
  "file_type": "slide_archive",
  "success": true,
  "text": "--- Page 1 ---\nContent...",
  "text_length": 18088,
  "metadata": {"num_pages": 60},
  "pages": [{"page_number": 1, "text": "...", "char_count": 34}, ...]
}
```

### Batch Extract Folder
```
GET /api/admin/courses/materials/extract-batch?folder={path}&recursive={true|false}
```

**Example:**
```bash
curl "http://localhost:8000/api/admin/courses/materials/extract-batch?folder=Syllabus&recursive=true"
```

## File Upload Integration

When implementing file upload functionality, follow this pattern:

```python
from pathlib import Path
from app.services.text_extractor import extract_text, detect_file_type

async def process_uploaded_file(file_path: Path):
    """Process an uploaded file and extract its text for indexing."""
    
    # 1. Detect file type
    file_type = detect_file_type(file_path)
    
    if file_type == 'unknown':
        return {"error": "Unsupported file type"}
    
    # 2. Extract text
    result = extract_text(file_path)
    
    if not result.success:
        return {"error": result.error}
    
    # 3. Store extracted text for LLM operations
    # TODO: Save to Firestore or indexing service
    
    return {
        "file_type": result.file_type,
        "text_length": len(result.text),
        "pages": len(result.pages) if result.pages else None,
        "ready_for_llm": True
    }
```

## Dependencies

Add these to `requirements.txt`:

```
PyMuPDF>=1.23.0          # PDF text extraction
python-docx>=1.1.0       # DOCX text extraction  
pytesseract>=0.3.10      # OCR for images
Pillow>=10.0.0           # Image processing for OCR
beautifulsoup4>=4.12.0   # HTML parsing
```

**System dependency (for OCR):**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
apt-get install tesseract-ocr

# Windows
# Download installer from https://github.com/UB-Mannheim/tesseract/wiki
```

## Testing

Run the test suite:
```bash
pytest tests/test_text_extractor.py -v
```

## Related Services

- **Slide Archive Service** (`app/services/slide_archive.py`): Handles ZIP-based slide archives
- **Files API Service** (`app/services/files_api_service.py`): Uploads to Anthropic for LLM processing
- **Materials Scanner** (`app/services/materials_scanner.py`): Scans folder structure

## Future Enhancements

See GitHub issues for planned improvements:
- [ ] Firestore caching for extracted text
- [ ] Admin UI for extraction status
- [ ] Background extraction job queue

