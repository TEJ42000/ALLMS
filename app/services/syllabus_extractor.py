"""
AI-based syllabus data extraction service.

Uses Claude to extract structured course data from syllabus PDF text.
"""

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from app.services.gcp_service import get_anthropic_api_key

logger = logging.getLogger(__name__)

# Initialize Anthropic client
client = AsyncAnthropic(api_key=get_anthropic_api_key())

# Maximum syllabus text length for AI processing (Claude context limits)
MAX_SYLLABUS_TEXT_LENGTH = 100000

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
      "title": "Short topic title (3-10 words)",
      "topicDescription": "3-5 sentence description of what this week's topic covers, including key concepts, legal principles, and learning objectives.",
      "topics": ["Sub-topic 1", "Sub-topic 2"],
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
1. Extract ALL weeks mentioned in the syllabus (typically 6 weeks per course)
2. For each week, extract:
   - title: A short, descriptive topic title (3-10 words)
   - topicDescription: A detailed 3-5 sentence description explaining what the topic covers
   - topics: List of sub-topics or key points (optional, for backward compatibility)
   - readings: All required readings with author, title, and chapters
3. If topics are not explicitly listed, INFER them from readings, lecture content, and learning objectives
4. Include lecturer names for each week if mentioned
5. Extract course components (parts) with their point values
6. Return ONLY valid JSON, no markdown or explanations
7. Use null for missing values, not empty strings
8. Preserve exact names and titles as written"""


TOPIC_EXTRACTION_SYSTEM_PROMPT = """You are an expert at extracting course topics from academic syllabi.

Your task is to identify ALL topics covered in this course. Topics may be:
1. EXPLICIT: Listed directly in weekly schedules, lecture titles, or topic lists
2. INFERRED: Mentioned in readings, case discussions, or learning objectives

For each topic, provide:
- A clear, concise name (3-10 words)
- A 2-3 sentence description explaining what the topic covers
- The week number(s) where this topic is covered (can be empty if course-wide)
- Confidence level: "high" (explicitly listed), "medium" (clearly implied), "low" (inferred)

Return valid JSON in this format:
{
  "topics": [
    {
      "name": "Topic Name",
      "description": "2-3 sentence description of what this topic covers...",
      "weekNumbers": [1, 2],
      "confidence": "high"
    }
  ],
  "extractionNotes": "Any notes about ambiguities or topics that may need review"
}

Rules:
1. Extract ALL distinct topics, even if only mentioned briefly
2. For topics spanning multiple weeks, include all relevant week numbers
3. Course-wide topics (e.g., "Legal Research Skills") may have empty weekNumbers
4. Be thorough - topics are used for study guides, quizzes, and flashcards
5. Return ONLY valid JSON, no markdown or explanations
6. Descriptions should be educational and help students understand the topic's scope"""


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
        if len(syllabus_text) > MAX_SYLLABUS_TEXT_LENGTH:
            syllabus_text = syllabus_text[:MAX_SYLLABUS_TEXT_LENGTH] + "\n\n[Text truncated...]"

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


def _generate_topic_id(name: str) -> str:
    """Generate a URL-safe topic ID from the topic name."""
    # Convert to lowercase, replace spaces and special chars
    topic_id = re.sub(r'[^a-z0-9]+', '-', name.lower())
    # Remove leading/trailing hyphens
    topic_id = topic_id.strip('-')
    # Fallback for names with only special characters
    if not topic_id:
        topic_id = "topic"
    # Add short UUID suffix for uniqueness
    short_uuid = str(uuid.uuid4())[:8]
    return f"{topic_id[:50]}-{short_uuid}"


async def extract_topics_from_syllabus(
    syllabus_text: str,
    course_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract detailed topics from syllabus text using AI.

    This function focuses specifically on topic extraction with descriptions,
    handling both explicitly listed topics and inferred topics.

    Args:
        syllabus_text: Raw text extracted from syllabus PDF
        course_name: Optional course name for context

    Returns:
        Dictionary with:
        - topics: List of topic dicts with id, name, description, weekNumbers, confidence
        - extractionNotes: Any notes about the extraction process
    """
    try:
        # Truncate if too long
        if len(syllabus_text) > MAX_SYLLABUS_TEXT_LENGTH:
            syllabus_text = syllabus_text[:MAX_SYLLABUS_TEXT_LENGTH] + "\n\n[Text truncated...]"

        context = f" for {course_name}" if course_name else ""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=TOPIC_EXTRACTION_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Extract all topics{context} from this syllabus:\n\n{syllabus_text}"
            }]
        )

        response_text = response.content[0].text

        # Parse JSON from response
        result = _parse_json_response(response_text)

        # Process topics to add IDs and normalize
        processed_topics = []
        for topic in result.get("topics", []):
            processed_topic = {
                "id": _generate_topic_id(topic.get("name", "unknown")),
                "name": topic.get("name", "").strip(),
                "description": topic.get("description", "").strip(),
                "weekNumbers": topic.get("weekNumbers", []),
                "extractionConfidence": topic.get("confidence", "medium"),
                "extractedFromSyllabus": True
            }
            processed_topics.append(processed_topic)

        logger.info(
            "Successfully extracted %d topics%s",
            len(processed_topics),
            context
        )

        return {
            "topics": processed_topics,
            "extractionNotes": result.get("extractionNotes", "")
        }

    except Exception as e:
        logger.error("Error extracting topics: %s", str(e))
        raise


async def extract_course_data_with_topics(
    syllabus_text: str,
    expected_weeks: int = 6
) -> Dict[str, Any]:
    """
    Extract course data with week-based topics from syllabus.

    Topics are now extracted as part of each week's data, not as a separate collection.
    Each week has:
    - title: Short topic title (3-10 words)
    - topicDescription: 3-5 sentence description of the topic

    Args:
        syllabus_text: Raw text extracted from syllabus PDF
        expected_weeks: Expected number of weeks in the course (default: 6)

    Returns:
        Dictionary with course data including weeks with topic descriptions
    """
    # Extract course data - the prompt now extracts topicDescription for each week
    course_data = await extract_course_data(syllabus_text)

    # Validate and ensure we have the expected number of weeks with topics
    weeks = course_data.get("weeks", [])

    # Log extraction summary
    weeks_with_topics = sum(1 for w in weeks if w.get("topicDescription"))
    logger.info(
        "Extracted %d weeks (%d with topic descriptions) for course: %s",
        len(weeks),
        weeks_with_topics,
        course_data.get("courseName", "Unknown")
    )

    # If we have fewer weeks than expected, note it but don't fail
    if len(weeks) < expected_weeks:
        logger.warning(
            "Extracted %d weeks but expected %d for course: %s",
            len(weeks),
            expected_weeks,
            course_data.get("courseName", "Unknown")
        )

    # Add metadata about extraction
    course_data["expectedWeeks"] = expected_weeks
    course_data["extractedWeekCount"] = len(weeks)
    course_data["weeksWithTopicDescriptions"] = weeks_with_topics

    return course_data


# Deprecated: Keep for backward compatibility but log deprecation warning
async def extract_topics_from_syllabus_deprecated(
    syllabus_text: str,
    course_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    DEPRECATED: Use extract_course_data_with_topics() instead.

    Topics are now extracted as part of week data, not as a separate collection.
    This function is kept for backward compatibility only.
    """
    import warnings
    warnings.warn(
        "extract_topics_from_syllabus is deprecated. "
        "Topics are now part of week data. Use extract_course_data_with_topics() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return await extract_topics_from_syllabus(syllabus_text, course_name)
