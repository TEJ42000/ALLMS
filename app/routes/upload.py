"""
Upload and Analysis Routes for Course Materials

This module provides endpoints for:
1. Uploading course materials (PDF, DOCX, PPTX, etc.)
2. Analyzing uploaded content with Claude AI
3. Extracting text and generating structured analysis

MVP Implementation - Issue #200
"""

from fastapi import APIRouter, UploadFile, Form, HTTPException
from pathlib import Path
import uuid
import shutil
import logging
from typing import Optional
import json
import re

from app.services.text_extractor import extract_text
from app.services.files_api_service import get_files_api_service

# Configure logging
logger = logging.getLogger(__name__)

# Router configuration
router = APIRouter(prefix="/api/upload", tags=["Upload"])

# Upload configuration
UPLOAD_DIR = Path("Materials/uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "txt", "md", "html"}
MAX_SIZE_MB = 25
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024


@router.post("")
async def upload_file(
    file: UploadFile,
    course_id: str = Form(...),
    week_number: Optional[int] = Form(None)
):
    """
    Upload a course material file.
    
    Args:
        file: The uploaded file
        course_id: Course identifier
        week_number: Optional week number for organization
        
    Returns:
        JSON with material_id, filename, and storage path
        
    Raises:
        HTTPException: If file type not allowed or upload fails
    """
    logger.info(f"Upload request: {file.filename} for course {course_id}")
    
    # Validate file extension
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Invalid file type: .{ext}")
        raise HTTPException(
            400, 
            f"File type .{ext} not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if size > MAX_SIZE_BYTES:
        logger.warning(f"File too large: {size} bytes")
        raise HTTPException(
            400,
            f"File too large ({size / 1024 / 1024:.1f}MB). Maximum size: {MAX_SIZE_MB}MB"
        )
    
    # Generate unique material ID
    material_id = str(uuid.uuid4())[:8]
    
    # Sanitize filename (remove path traversal attempts)
    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    safe_filename = f"{material_id}_{safe_filename}"
    
    # Ensure upload directory exists
    course_dir = UPLOAD_DIR / course_id
    course_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = course_dir / safe_filename
    
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        logger.info(f"File saved: {file_path}")
        
        return {
            "status": "success",
            "material_id": material_id,
            "filename": file.filename,
            "storage_path": str(file_path.relative_to("Materials")),
            "size_bytes": size,
            "message": f"File uploaded successfully. Use /api/upload/{material_id}/analyze to process."
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        # Clean up partial file if it exists
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.post("/{material_id}/analyze")
async def analyze_uploaded_file(
    material_id: str,
    course_id: str
):
    """
    Extract text and analyze uploaded file with Claude AI.
    
    Args:
        material_id: Unique identifier from upload
        course_id: Course identifier
        
    Returns:
        JSON with extraction results and AI analysis
        
    Raises:
        HTTPException: If file not found or analysis fails
    """
    logger.info(f"Analysis request: {material_id} for course {course_id}")
    
    # Find the file
    course_dir = UPLOAD_DIR / course_id
    if not course_dir.exists():
        raise HTTPException(404, f"Course directory not found: {course_id}")
    
    matching_files = list(course_dir.glob(f"{material_id}_*"))
    
    if not matching_files:
        raise HTTPException(404, f"File not found: {material_id}")
    
    file_path = matching_files[0]
    logger.info(f"Analyzing file: {file_path}")
    
    # Extract text using existing service
    try:
        result = extract_text(file_path)
        
        if not result.success:
            logger.error(f"Extraction failed: {result.error}")
            raise HTTPException(500, f"Text extraction failed: {result.error}")
        
        logger.info(f"Extracted {len(result.text)} characters")
        
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        raise HTTPException(500, f"Extraction error: {str(e)}")
    
    # Truncate for analysis (Claude has token limits)
    text_preview = result.text[:50000] if len(result.text) > 50000 else result.text
    
    # Analyze with Claude
    try:
        service = get_files_api_service()
        
        analysis_prompt = f"""Analyze this course material and return ONLY valid JSON.

CONTENT:
{text_preview[:30000]}

Return JSON with this exact structure:
{{
    "content_type": "lecture_notes|case_law|textbook|syllabus|practice_problems|other",
    "main_topics": ["topic1", "topic2", "topic3"],
    "key_concepts": [
        {{"term": "concept name", "definition": "brief definition"}}
    ],
    "difficulty": "easy|medium|hard",
    "recommended_study_methods": ["flashcards", "quiz", "summary", "spaced_repetition"],
    "summary": "2-3 sentence summary of the content"
}}"""

        response = await service.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        
        # Parse JSON response
        text = response.content[0].text
        
        # Handle markdown code blocks
        if "```json" in text:
            match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
            if match:
                text = match.group(1)
        
        try:
            analysis = json.loads(text)
            logger.info(f"Analysis successful: {analysis.get('content_type', 'unknown')}")
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}, using raw response")
            analysis = {
                "raw_response": text,
                "parse_error": True,
                "error_message": str(e)
            }
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(500, f"AI analysis failed: {str(e)}")
    
    # Return comprehensive response
    return {
        "status": "success",
        "material_id": material_id,
        "filename": file_path.name,
        "extraction": {
            "success": True,
            "char_count": len(result.text),
            "preview": result.text[:500] + "..." if len(result.text) > 500 else result.text,
            "method": result.method if hasattr(result, 'method') else "unknown"
        },
        "analysis": analysis
    }

