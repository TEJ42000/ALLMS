"""
AI-based syllabus data extraction service.

Uses Claude to extract structured course data from syllabus PDF text.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from app.services.gcp_service import get_anthropic_api_key

logger = logging.getLogger(__name__)

# Initialize Anthropic client
client = AsyncAnthropic(api_key=get_anthropic_api_key())

EXTRACTION_SYSTEM_PROMPT = """You are an expert at extracting structured course data from academic syllabi.

Extract the following information from the syllabus text and return it as valid JSON:

{
  "courseName": "Full course name",
  "courseCode": "Subject code (e.g., RGPAR510AD)",
  "academicYear": "Academic year (e.g., 2025-2026)",
  "program": "Program name (e.g., International and European Law)",
  "institution": "University/Faculty name",
  "totalPoints": 200,
  "passingThreshold": 110,
  "components": [
    {"id": "A", "name": "Law", "maxPoints": 100, "description": "..."},
    {"id": "B", "name": "Legal Skills", "maxPoints": 100, "description": "..."}
  ],
  "coordinators": [
    {"name": "Full Name", "title": "Dr./Prof./LLM", "email": null}
  ],
  "lecturers": [
    {"name": "Full Name", "title": "Dr./Prof./LLM"}
  ],
  "weeks": [
    {
      "weekNumber": 1,
      "title": "Week title/topic",
      "topics": ["Topic 1", "Topic 2"],
      "readings": [
        {"author": "Author", "title": "Book/Article Title", "chapters": "Chapter X, par. Y-Z"}
      ]
    }
  ],
  "examInfo": {
    "type": "digital/written",
    "format": "closed book/open book",
    "description": "Exam details"
  },
  "participationRequirements": "Attendance and participation requirements"
}

Rules:
1. Extract ALL weeks mentioned in the syllabus
2. For each week, extract the topic and all required readings
3. Include lecturer names for each week if mentioned
4. Extract course components (parts) with their point values
5. Return ONLY valid JSON, no markdown or explanations
6. Use null for missing values, not empty strings
7. Preserve exact names and titles as written"""


async def extract_course_data(syllabus_text: str) -> Dict[str, Any]:
    """
    Extract structured course data from syllabus text using AI.
    
    Args:
        syllabus_text: Raw text extracted from syllabus PDF
        
    Returns:
        Dictionary with extracted course data
    """
    try:
        # Truncate if too long (Claude has context limits)
        max_chars = 100000
        if len(syllabus_text) > max_chars:
            syllabus_text = syllabus_text[:max_chars] + "\n\n[Text truncated...]"
        
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Extract course data from this syllabus:\n\n{syllabus_text}"
            }]
        )
        
        response_text = response.content[0].text
        
        # Parse JSON from response
        extracted_data = _parse_json_response(response_text)
        
        logger.info("Successfully extracted course data: %s", extracted_data.get("courseName", "Unknown"))
        
        return extracted_data
        
    except Exception as e:
        logger.error("Error extracting course data: %s", str(e))
        raise


def _parse_json_response(text: str) -> Dict[str, Any]:
    """Parse JSON from AI response, handling markdown code blocks."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try extracting from markdown code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try finding JSON object in text
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"Could not parse JSON from response: {text[:500]}...")

