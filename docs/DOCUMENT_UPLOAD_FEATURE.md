# Document Upload Feature

## Overview

The Document Upload feature allows administrators to upload new documents (PDFs, Word documents, images, text files) directly to course materials through the admin interface. Files are automatically stored in the appropriate Materials folder structure, text is extracted for LLM processing, and metadata is tracked in Firestore.

## Features

### Supported File Types

| Type | Extensions | Extraction Method |
|------|-----------|-------------------|
| PDF | `.pdf` | PyMuPDF |
| Word | `.docx` | python-docx |
| PowerPoint | `.pptx` | python-pptx (future) |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp` | Tesseract OCR |
| Text | `.txt`, `.md` | Direct read |
| HTML | `.html`, `.htm` | BeautifulSoup |

### File Size Limit

- Maximum file size: **50MB** per file
- Configurable in `app/services/document_upload_service.py`

### Storage Structure

Files are stored in the existing Materials hierarchy:

```
Materials/
├── Syllabus/{course_id}/           # Tier 1
├── Course_Materials/{course_id}/   # Tier 2
│   ├── Lectures/
│   ├── Readings/
│   └── Cases/
└── Supplementary_Sources/{course_id}/  # Tier 3
```

## Architecture

### Backend Components

#### 1. Document Upload Service (`app/services/document_upload_service.py`)

Main service handling file uploads:

- **File Validation**: Checks file type, size, and extension
- **Storage Path Generation**: Creates appropriate folder paths
- **File Storage**: Saves files to disk
- **Text Extraction**: Automatically extracts text using TextExtractor
- **Metadata Storage**: Stores upload metadata in Firestore

Key Functions:
- `validate_file()` - Validates uploaded files
- `generate_storage_path()` - Generates storage paths
- `upload_document()` - Main upload function
- `store_material_metadata()` - Stores metadata in Firestore

#### 2. API Endpoints (`app/routes/admin_courses.py`)

**POST `/api/admin/courses/{course_id}/materials/upload`**
- Upload a document to course materials
- Accepts multipart/form-data
- Returns: UploadResponse with material metadata

**GET `/api/admin/courses/{course_id}/materials/uploads`**
- List all uploaded materials for a course
- Optional filters: tier, week_number
- Returns: MaterialListResponse with list of materials

**GET `/api/admin/courses/{course_id}/materials/uploads/{material_id}`**
- Get details of a specific uploaded material
- Returns: UploadedMaterial object

**DELETE `/api/admin/courses/{course_id}/materials/uploads/{material_id}`**
- Delete an uploaded material (file and metadata)
- Returns: 204 No Content

**GET `/api/admin/courses/{course_id}/materials/uploads/{material_id}/text`**
- Get extracted text from an uploaded material
- Returns: JSON with extracted text and metadata

**GET `/api/admin/upload-config`**
- Get upload configuration (supported types, size limits, etc.)
- Returns: Configuration object

#### 3. Data Model (`app/models/course_models.py`)

```python
class UploadedMaterial(BaseModel):
    id: str                          # UUID
    filename: str                    # Original filename
    storagePath: str                 # Path in Materials/
    tier: str                        # 'syllabus', 'course_materials', 'supplementary'
    category: Optional[str]          # 'lecture', 'reading', 'case', etc.
    fileType: str                    # 'pdf', 'docx', 'image', etc.
    fileSize: int                    # Bytes
    mimeType: str
    uploadedAt: datetime
    uploadedBy: Optional[str]        # User ID when auth is implemented
    
    # Text extraction
    textExtracted: bool = False
    extractedText: Optional[str]     # Stored text
    textLength: Optional[int]
    extractionError: Optional[str]
    
    # Metadata
    title: Optional[str]             # Display title
    description: Optional[str]
    weekNumber: Optional[int]        # Link to specific week
```

### Frontend Components

#### 1. Admin UI (`templates/admin/courses.html`)

- **Upload Button**: Opens upload modal
- **Upload Modal**: Drag-and-drop file upload interface
- **Uploaded Materials List**: Displays all uploaded materials
- **Material Actions**: View text, preview, delete

#### 2. Upload JavaScript (`app/static/js/upload.js`)

Key Functions:
- `openUploadModal()` - Opens upload modal
- `handleFileSelect()` - Handles file selection
- `handleDrop()` - Handles drag-and-drop
- `submitUpload()` - Uploads files to server
- `loadUploadedMaterials()` - Loads and displays uploaded materials
- `deleteMaterial()` - Deletes a material

#### 3. Styles (`app/static/css/admin.css`)

- File drop zone styling
- Progress bar
- Material list cards
- Badges for tier, category, extraction status

## Usage

### Admin Interface

1. **Navigate to Course Details**
   - Go to Admin Portal → Courses
   - Click on a course to view details

2. **Upload Files**
   - Click "📤 Upload Files" button in Materials section
   - Drag & drop files or click to browse
   - Select material tier (Syllabus, Course Materials, or Supplementary)
   - For Course Materials, optionally select category (Lecture, Reading, Case)
   - Optionally link to a specific week number
   - Add description (optional)
   - Choose whether to extract text automatically
   - Click "📤 Upload Files"

3. **View Uploaded Materials**
   - Uploaded materials appear in "Uploaded Materials" section
   - Shows filename, tier, category, week, extraction status
   - Click 📄 to view extracted text
   - Click 👁️ to preview file
   - Click 🗑️ to delete material

### API Usage

#### Upload a File

```bash
curl -X POST \
  "http://localhost:8080/api/admin/courses/LLS-2025-2026/materials/upload" \
  -F "file=@document.pdf" \
  -F "tier=course_materials" \
  -F "category=lecture" \
  -F "week_number=1" \
  -F "description=Week 1 lecture slides" \
  -F "extract_text=true"
```

#### List Uploaded Materials

```bash
curl "http://localhost:8080/api/admin/courses/LLS-2025-2026/materials/uploads"
```

#### Get Material Text

```bash
curl "http://localhost:8080/api/admin/courses/LLS-2025-2026/materials/uploads/{material_id}/text"
```

#### Delete Material

```bash
curl -X DELETE \
  "http://localhost:8080/api/admin/courses/LLS-2025-2026/materials/uploads/{material_id}"
```

## Firestore Structure

Uploaded materials are stored in a subcollection:

```
courses/{course_id}/uploadedMaterials/{material_id}
```

Each document contains the UploadedMaterial model fields.

## Text Extraction

Text extraction is performed automatically on upload using the Text Extraction Service (`app/services/text_extractor.py`).

### Extraction Process

1. File is saved to disk
2. File type is detected
3. Appropriate extraction method is used:
   - PDF: PyMuPDF
   - DOCX: python-docx
   - Images: Tesseract OCR
   - Text: Direct read
   - HTML: BeautifulSoup
4. Extracted text is stored in Firestore
5. Extraction status and errors are tracked

### Extraction Status

- `textExtracted: true` - Text successfully extracted
- `textExtracted: false` - Extraction failed or not attempted
- `extractionError` - Error message if extraction failed

## Error Handling

### File Validation Errors

- File too large (>50MB)
- Unsupported file type
- Empty file
- Missing file extension

### Storage Errors

- Disk write failure
- Permission issues
- Invalid path

### Extraction Errors

- Corrupted file
- Unsupported format
- OCR failure
- Missing dependencies

## Security Considerations

1. **File Type Validation**: Only allowed file types can be uploaded
2. **File Size Limit**: Prevents large file uploads
3. **Path Validation**: Prevents directory traversal attacks
4. **Authentication**: TODO - Add user authentication (Phase 5)
5. **Authorization**: TODO - Add role-based access control

## Future Enhancements

### Phase 1 (Current)
- ✅ File upload API
- ✅ Admin UI with drag-and-drop
- ✅ Text extraction
- ✅ Metadata storage
- ✅ Material management (view, delete)

### Phase 2 (Future)
- [ ] Batch upload progress tracking
- [ ] Background extraction for large files
- [ ] External storage for large extracted text (Cloud Storage)
- [ ] Material versioning
- [ ] Material tags and search
- [ ] Duplicate detection

### Phase 3 (Future)
- [ ] User authentication and authorization
- [ ] Upload history and audit log
- [ ] Material sharing between courses
- [ ] Automatic material categorization using AI
- [ ] Material recommendations

## Testing

### Manual Testing

1. **Upload PDF**
   - Upload a PDF file
   - Verify file is saved to correct folder
   - Verify text is extracted
   - Verify metadata is stored

2. **Upload DOCX**
   - Upload a Word document
   - Verify text extraction
   - Verify metadata

3. **Upload Image**
   - Upload an image with text
   - Verify OCR extraction
   - Check extraction quality

4. **Upload Multiple Files**
   - Upload multiple files at once
   - Verify all files are processed
   - Check progress indicator

5. **Delete Material**
   - Delete an uploaded material
   - Verify file is removed from disk
   - Verify metadata is removed from Firestore

### Automated Testing

Run tests:
```bash
pytest tests/ -v
```

All 141 tests should pass (2 pre-existing failures in text extraction tests).

## Troubleshooting

### Upload Fails

- Check file size (<50MB)
- Check file type is supported
- Check disk space
- Check file permissions

### Text Extraction Fails

- Check file is not corrupted
- Check dependencies are installed (PyMuPDF, python-docx, pytesseract)
- Check Tesseract is installed for OCR
- View extraction error in material details

### Materials Not Showing

- Refresh the page
- Check Firestore connection
- Check course ID is correct
- Check browser console for errors

## Dependencies

- `python-multipart>=0.0.6` - For file uploads
- `PyMuPDF>=1.23.0` - PDF text extraction
- `python-docx>=1.1.0` - DOCX text extraction
- `pytesseract>=0.3.10` - OCR for images
- `Pillow>=10.0.0` - Image processing
- `beautifulsoup4>=4.12.0` - HTML parsing

## Related Documentation

- [Text Extraction Service](TEXT-EXTRACTION-SERVICE.md)
- [Multi-Course Architecture](MULTI_COURSE_ARCHITECTURE.md)
- [Course Management System](../README.md#course-management)

