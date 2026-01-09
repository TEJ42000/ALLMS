"""Content Generation Service for the LLS Study Portal.

This service provides AI-powered content generation (quizzes, study guides, flashcards)
using course materials. It integrates with CourseService to get course-specific
materials from Firestore and uses text extraction to get content from files.

Content is extracted locally using the text_extractor service, which handles:
- Real PDFs (using PyMuPDF)
- Slide archives (ZIP files with JPEG slides + text, disguised as PDFs)
- Images (OCR)
- DOCX, Markdown, HTML, etc.

This approach is more robust than the Files API because it:
1. Works with all file types including slide archives
2. Doesn't require managing file IDs and expiry
3. Simpler architecture with no external file state
"""

import asyncio
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from anthropic import AsyncAnthropic, RateLimitError

from app.models.course_models import CourseMaterial
from app.models.usage_models import UserContext
from app.services.gcp_service import get_anthropic_api_key, get_firestore_client
from app.services.text_extractor import extract_text, detect_file_type, ExtractionResult
from app.services.usage_tracking_service import track_llm_usage_from_response

logger = logging.getLogger(__name__)

# Constants
DEFAULT_FALLBACK_COUNT = 5  # Number of files to return when no specific files found
MATERIALS_ROOT = Path("Materials")
MAX_TEXT_LENGTH = 100000  # Maximum characters per document to avoid context overflow
MAX_MATERIALS_PER_GENERATION = 10  # Limit materials to avoid context overflow in AI generation

# Validation constants
MIN_FLASHCARDS = 5  # Minimum number of flashcards to generate
MAX_FLASHCARDS = 50  # Maximum number of flashcards to generate
MAX_TOPIC_LENGTH = 200  # Maximum length for topic parameter (prevent prompt injection)
MAX_WEEK_NUMBER = 52  # Maximum week number in academic year
DEFAULT_TOPIC = "Course Materials"  # Default topic when none is provided

# Text truncation constants
SENTENCE_BOUNDARY_THRESHOLD = 0.9  # Prefer sentence boundaries in last 10% of text

# Compiled regex patterns for prompt injection detection (compiled once for performance)
# These patterns detect common prompt injection attempts while avoiding false positives
# for legitimate legal education content (e.g., "act as a judge" is valid legal topic)
# Patterns are tightened to require AI-specific context words to avoid blocking legal topics
PROMPT_INJECTION_PATTERNS = [
    # Instruction override attempts - target AI/system instructions specifically
    # Requires context words like "instructions", "prompts", "rules", "commands"
    re.compile(r'ignore\s+(previous|all|above|prior|earlier)\s+(instructions?|prompts?|rules?|commands?)', re.IGNORECASE),
    re.compile(r'disregard\s+(previous|all|above|prior|earlier)\s+(instructions?|prompts?|rules?|commands?)', re.IGNORECASE),
    re.compile(r'forget\s+(previous|all|above|prior|earlier)\s+(instructions?|prompts?|rules?|commands?)', re.IGNORECASE),
    re.compile(r'override\s+(previous|all|above|prior)\s+(instructions?|prompts?|rules?|commands?)', re.IGNORECASE),

    # System manipulation attempts - specific to AI system
    # Tightened: requires "AI", "assistant", or "model" before "system" to avoid legal topics
    # Allows: "legal system instruction", "justice system message"
    # Blocks: "AI system prompt", "ignore system instruction"
    re.compile(r'(ai|assistant|model|chatbot)\s+system\s+(prompt|message|instruction)', re.IGNORECASE),
    re.compile(r'(ignore|bypass|override)\s+(the\s+)?system\s+(prompt|instruction|rules?)', re.IGNORECASE),
    re.compile(r'new\s+(instructions?|prompt)\s+(for\s+)?(you|the\s+system|the\s+ai)', re.IGNORECASE),

    # Role manipulation attempts - target AI role changes, not legal roles
    # Requires AI-specific roles: unrestricted, jailbroken, developer, admin, root, DAN
    re.compile(r'you\s+are\s+now\s+(an?\s+)?(unrestricted|jailbroken|developer|admin|root)', re.IGNORECASE),
    re.compile(r'act\s+as\s+(an?\s+)?(unrestricted|jailbroken|developer|admin|root|dan)', re.IGNORECASE),
    re.compile(r'pretend\s+(to\s+be|you\s+are)\s+(an?\s+)?(unrestricted|jailbroken|developer|admin)', re.IGNORECASE),

    # Direct command attempts targeting AI behavior
    # Requires "code", "command", or "script" to avoid blocking legal topics
    re.compile(r'(^|\s)(execute|run|perform)\s+(this|the|following)\s+(code|command|script)', re.IGNORECASE),

    # Explicit jailbreak attempts
    re.compile(r'(jailbreak|dan\s+mode|developer\s+mode|god\s+mode)', re.IGNORECASE),
]


class FilesAPIService:
    """Service for generating content using course materials with text extraction.

    This service uses text extraction to get content from local files,
    supporting all file types including slide archives.

    Key methods:
    - get_course_materials(): Fetch materials from Firestore
    - get_course_materials_with_text(): Get materials with extracted text content
    - generate_quiz_from_course(): Generate quizzes using course materials
    """

    def __init__(self):
        """Initialize the content generation service."""
        self.client = AsyncAnthropic(api_key=get_anthropic_api_key())

        # Lazy-loaded service references
        self._course_service = None
        self._firestore = None

        # Legacy file_ids dict - kept for backwards compatibility with methods
        # that haven't been migrated to text extraction yet (explain_article,
        # analyze_case, get_topic_files, etc). These methods will return empty
        # results until they are refactored.
        # TODO: Remove once all methods are migrated to text extraction
        self.file_ids: Dict[str, Dict[str, Any]] = {}

        # Beta header for Files API (used by legacy methods)
        self.beta_header = "pdfs-2024-09-25"

    def get_file_id(self, key: str) -> str:
        """Get file_id for a course material (legacy method).

        Note: This is kept for backwards compatibility with legacy methods
        that haven't been migrated to text extraction yet. Returns empty
        results since file_ids is no longer loaded from file_ids.json.

        Args:
            key: File key from file_ids.json

        Returns:
            File ID string

        Raises:
            ValueError: If file key not found
        """
        file_info = self.file_ids.get(key)
        if not file_info:
            raise ValueError(f"File {key} not found in file_ids.json")
        return file_info["file_id"]

    def _get_course_service(self):
        """Get CourseService instance (lazy loading to avoid circular imports)."""
        if self._course_service is None:
            from app.services.course_service import get_course_service
            self._course_service = get_course_service()
        return self._course_service

    def _get_anthropic_client(self):
        """Get Anthropic client instance.

        This method exists for test mocking purposes. Tests can patch this method
        to inject mock clients without affecting the actual client initialization.

        Returns:
            AsyncAnthropic: The Anthropic client instance
        """
        return self.client

    @property
    def firestore(self):
        """Lazy-load Firestore client."""
        if self._firestore is None:
            self._firestore = get_firestore_client()
        return self._firestore

    # ========== Firestore-Based Methods ==========

    def get_course_materials(
        self,
        course_id: str,
        week_number: Optional[int] = None,
        tier: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[CourseMaterial]:
        """Get course materials from Firestore.

        Args:
            course_id: Course ID
            week_number: Optional week filter
            tier: Optional tier filter ('syllabus', 'course_materials', 'supplementary')
            category: Optional category filter
            limit: Maximum materials to return

        Returns:
            List of CourseMaterial objects

        Raises:
            TypeError: If week_number is not an integer
            ValueError: If week_number is out of valid range
        """
        if not self.firestore:
            logger.warning("Firestore not available")
            return []

        # Validate week_number type and range
        if week_number is not None:
            if not isinstance(week_number, int):
                raise TypeError(f"week_number must be an integer, got {type(week_number).__name__}")
            if week_number < 1 or week_number > MAX_WEEK_NUMBER:
                raise ValueError(f"week_number must be between 1 and {MAX_WEEK_NUMBER}, got {week_number}")

        query = (
            self.firestore
            .collection("courses")
            .document(course_id)
            .collection("materials")
        )

        # Apply filters
        if week_number is not None:
            query = query.where("weekNumber", "==", week_number)
        if tier:
            query = query.where("tier", "==", tier)
        if category:
            query = query.where("category", "==", category)

        # Execute query
        docs = query.limit(limit).stream()

        materials = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            try:
                materials.append(CourseMaterial(**data))
            except Exception as e:
                logger.warning("Failed to parse material %s: %s", doc.id, str(e))

        return materials

    def _get_local_file_path(self, material: CourseMaterial) -> Path:
        """Get the local file path for a material.

        Args:
            material: The course material

        Returns:
            Path to the local file
        """
        return MATERIALS_ROOT / material.storagePath

    def _extract_text_from_material(self, material: CourseMaterial) -> Optional[str]:
        """Extract text content from a material file.

        Handles all file types including slide archives (ZIP files disguised as PDFs).

        Args:
            material: The course material

        Returns:
            Extracted text content, or None if extraction failed
        """
        file_path = self._get_local_file_path(material)

        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            return None

        # Detect file type and extract text
        file_type = detect_file_type(file_path)
        logger.info("Extracting text from %s (type: %s)", material.filename, file_type)

        result = extract_text(file_path)

        if not result.success:
            logger.warning(
                "Failed to extract text from %s: %s",
                material.filename,
                result.error
            )
            return None

        # Truncate if too long to avoid context overflow
        text = result.text
        if len(text) > MAX_TEXT_LENGTH:
            logger.info(
                "Truncating text from %s: %d -> %d chars",
                material.filename,
                len(text),
                MAX_TEXT_LENGTH
            )
            # Try to truncate at last period within limit to avoid breaking mid-sentence
            # rfind searches up to MAX_TEXT_LENGTH, returns -1 if no period found
            truncate_at = text.rfind('.', 0, MAX_TEXT_LENGTH)
            # Only use sentence boundary if found AND within threshold (last 10% of limit)
            if truncate_at != -1 and truncate_at > MAX_TEXT_LENGTH * SENTENCE_BOUNDARY_THRESHOLD:
                text = text[:truncate_at + 1] + "\n\n[... content truncated ...]"
            else:
                # Fall back to hard truncation if no good sentence boundary found (or truncate_at == -1)
                text = text[:MAX_TEXT_LENGTH] + "\n\n[... content truncated ...]"

        logger.info(
            "Extracted %d chars from %s (type: %s)",
            len(text),
            material.filename,
            file_type
        )
        return text

    async def get_course_materials_with_text(
        self,
        course_id: str,
        week_number: Optional[int] = None,
        tier: Optional[str] = None,
        limit: int = 10
    ) -> List[Tuple[CourseMaterial, str]]:
        """Get course materials with their extracted text content.

        This method extracts text from local files, supporting all file types
        including slide archives (ZIP files with JPEG slides + text).

        Args:
            course_id: Course ID
            week_number: Optional week filter
            tier: Optional tier filter
            limit: Maximum materials to return

        Returns:
            List of (CourseMaterial, extracted_text) tuples
        """
        materials = self.get_course_materials(
            course_id=course_id,
            week_number=week_number,
            tier=tier,
            limit=limit
        )

        if not materials:
            logger.warning("No materials found for course %s", course_id)
            return []

        results = []

        for material in materials:
            try:
                text = self._extract_text_from_material(material)
                if text:
                    results.append((material, text))
                else:
                    logger.warning("No text extracted from %s", material.filename)
            except Exception as e:
                logger.error(
                    "Failed to extract text from %s: %s",
                    material.filename,
                    str(e)
                )
                # Continue with other materials

        logger.info(
            "Got %d materials with text for course %s",
            len(results),
            course_id
        )
        return results

    async def generate_quiz_from_files(
        self,
        file_keys: List[str],
        topic: str,
        num_questions: int = 10,
        difficulty: str = "medium"
    ) -> Dict:
        """
        Generate quiz questions from uploaded files.

        Args:
            file_keys: List of file keys to use (e.g., ["lecture_week_3", "lls_reader"])
            topic: Topic name
            num_questions: Number of questions
            difficulty: easy, medium, or hard

        Returns:
            Dictionary with quiz questions

        Raises:
            ValueError: If file_keys is empty
            TypeError: If file_keys contains non-string values
        """
        # Input validation
        if not file_keys:
            raise ValueError("file_keys cannot be empty")
        if not all(isinstance(k, str) for k in file_keys):
            raise TypeError("All file_keys must be strings")

        logger.info("Generating quiz: %d questions, files: %s", num_questions, file_keys)

        # Build content blocks
        content_blocks = []

        # Add all requested files
        for key in file_keys:
            try:
                file_id = self.get_file_id(key)
                content_blocks.append({
                    "type": "document",
                    "source": {
                        "type": "file",
                        "file_id": file_id
                    },
                    "title": key.replace("_", " ").title(),
                    "citations": {"enabled": True}
                })
            except ValueError as e:
                logger.warning("Skipping file '%s': %s", key, e)
                continue

        # Add text prompt
        prompt_text = """Generate %d multiple choice quiz questions about %s from these documents.

Difficulty: %s
Requirements:
- Use only information from the provided documents
- Using information from provided documents, create further questions that are related to course content (Minimum of 20 Questions per Week)
- Each question tests understanding of legal concepts
- Include article citations (e.g., Art. 6:74 DCC)
- Provide 4 multiple choice answer options
- Mark correct answer
- Include detailed explanation

Return ONLY valid JSON:
{
  "questions": [
    {
      "question": "What are the 4 requirements for a valid contract?",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "explanation": "Under Dutch law...",
      "difficulty": "%s",
      "articles": ["Art. 3:32 DCC", "Art. 3:33 DCC"],
      "topic": "%s"
    }
  ]
}""" % (num_questions, topic, difficulty, difficulty, topic)

        content_blocks.append({
            "type": "text",
            "text": prompt_text
        })

        # Call API with Files API beta
        client = self._get_anthropic_client()
        response = await client.beta.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            betas=[self.beta_header],
            messages=[{
                "role": "user",
                "content": content_blocks
            }]
        )

        # Parse response
        text = response.content[0].text
        quiz_data = self._parse_json(text)

        logger.info("Generated %d questions", len(quiz_data.get('questions', [])))
        return quiz_data

    async def generate_quiz_from_course(
        self,
        course_id: str,
        topic: str,
        num_questions: int = 10,
        difficulty: str = "medium",
        week_number: Optional[int] = None,
        user_context: Optional[UserContext] = None,
    ) -> Dict:
        """Generate quiz using Firestore materials with text extraction.

        This method uses the materials subcollection in Firestore and
        extracts text from local files to send as content blocks.

        Args:
            course_id: Course ID
            topic: Topic name for the quiz
            num_questions: Number of questions to generate
            difficulty: 'easy', 'medium', or 'hard'
            week_number: Optional week filter
            user_context: User context for usage tracking

        Returns:
            Dictionary with quiz questions

        Raises:
            ValueError: If no materials found
        """
        logger.info(
            "Generating quiz from course %s: %d questions, week=%s",
            course_id, num_questions, week_number
        )

        # Get materials with their extracted text content
        materials_with_text = await self.get_course_materials_with_text(
            course_id=course_id,
            week_number=week_number,
            limit=MAX_MATERIALS_PER_GENERATION
        )

        if not materials_with_text:
            raise ValueError(f"No materials found for course {course_id}")

        # Build content blocks using extracted text
        content_blocks = []

        # Add each document's content as a text block with clear labeling
        for material, text in materials_with_text:
            title = material.title or material.filename
            document_block = f"""
=== DOCUMENT: {title} ===
{text}
=== END OF {title} ===
"""
            content_blocks.append({
                "type": "text",
                "text": document_block
            })

        # Add the quiz generation prompt
        prompt_text = """Based on the documents provided above, generate %d multiple choice quiz questions about %s.

Difficulty: %s
Requirements:
- Use only information from the provided documents
- Each question tests understanding of legal concepts
- Include article citations where applicable
- Provide 4 multiple choice answer options
- Mark correct answer
- Include detailed explanation

Return ONLY valid JSON:
{
  "questions": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "explanation": "...",
      "difficulty": "%s",
      "articles": [],
      "topic": "%s"
    }
  ]
}""" % (num_questions, topic, difficulty, difficulty, topic)

        content_blocks.append({
            "type": "text",
            "text": prompt_text
        })

        logger.info(
            "Sending %d content blocks to Anthropic (from %d materials)",
            len(content_blocks),
            len(materials_with_text)
        )

        # Call API (no Files API beta header needed)
        client = self._get_anthropic_client()
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": content_blocks
            }]
        )

        # Track usage if user context provided
        await track_llm_usage_from_response(
            response=response,
            user_context=user_context,
            operation_type="quiz",
            model="claude-sonnet-4-20250514",
            request_metadata={
                "topic": topic,
                "num_questions": num_questions,
                "difficulty": difficulty,
                "week_number": week_number,
            },
        )

        # Parse response
        text = response.content[0].text
        quiz_data = self._parse_json(text)

        logger.info(
            "Generated %d questions from %d materials",
            len(quiz_data.get('questions', [])),
            len(materials_with_text)
        )
        return quiz_data

    async def generate_study_guide_from_course(
        self,
        course_id: str,
        topic: str,
        week_numbers: Optional[List[int]] = None,
        user_context: Optional[UserContext] = None,
    ) -> str:
        """Generate comprehensive study guide using Firestore materials with text extraction.

        This method uses the materials subcollection in Firestore and
        extracts text from local files to send as content blocks.

        Args:
            course_id: Course ID
            topic: Topic description for the study guide
            week_numbers: Optional list of week numbers to filter by (e.g., [1, 2, 3])
            user_context: User context for usage tracking

        Returns:
            Formatted study guide in Markdown

        Raises:
            ValueError: If no materials found
        """
        logger.info(
            "Generating study guide from course %s, weeks=%s",
            course_id, week_numbers
        )

        # Get materials with their extracted text content
        # For multiple weeks, fetch each week separately and combine
        materials_with_text = []

        if week_numbers and len(week_numbers) > 0:
            # Fetch materials for each specified week
            # Limit to 3 materials per week to stay under rate limits (10k tokens/min)
            for week_num in week_numbers:
                week_materials = await self.get_course_materials_with_text(
                    course_id=course_id,
                    week_number=week_num,
                    limit=3  # Reduced from 10 to manage rate limits
                )
                materials_with_text.extend(week_materials)
        else:
            # No week filter - get all materials
            # Limit to 5 materials total for general study guides
            materials_with_text = await self.get_course_materials_with_text(
                course_id=course_id,
                week_number=None,
                limit=5  # Reduced from 15 to manage rate limits
            )

        if not materials_with_text:
            raise ValueError(f"No materials found for course {course_id}")

        # Build content blocks using extracted text
        content_blocks = []

        # Add each document's content as a text block with clear labeling
        # We'll mark the last document block for caching since cache applies
        # to all content up to and including the marked block
        for i, (material, text) in enumerate(materials_with_text):
            title = material.title or material.filename
            document_block = f"""
=== DOCUMENT: {title} ===
{text}
=== END OF {title} ===
"""
            block = {
                "type": "text",
                "text": document_block
            }

            # Add cache_control to the LAST document block
            # This caches all documents as a unit (cache breakpoint)
            # Cache TTL is 5 minutes by default, refreshed on each use
            if i == len(materials_with_text) - 1:
                block["cache_control"] = {"type": "ephemeral"}
                logger.info("Prompt caching enabled for %d documents", len(materials_with_text))

            content_blocks.append(block)

        prompt_text = f"""Based on the documents provided above, create a comprehensive study guide for {topic}.
        Wherever possible include links to the source material to all of easy cross referencing. When echr cases
        are mentioned try to include a link to the case in the HUDOC database. When Dutch law is mentioned include a link to the article on the wetten.nl website.

REQUIRED SECTIONS:

## 📚 Key Concepts
- All core concepts mentioned in the materials with clear definitions
- Use **bold** for key terms being defined
- Group related concepts together under ### subheadings

## 🔄 Decision Models & Frameworks
- Create visual decision trees using Mermaid flowchart syntax
- Use this format for flowcharts:
```mermaid
graph TD
    A[Start] --> B{{Decision?}}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
```
- Include step-by-step analysis frameworks
- Show how concepts connect to each other

## 📖 Important Articles
Present articles in a Markdown table:
| Article | Name | Purpose | Key Elements |
|---------|------|---------|--------------|
| Art. X:XX | ... | ... | ... |

- Explain each article's purpose and when it applies
- Group by topic or code section

## ⚠️ Common Mistakes
| ❌ Mistake | ✅ Correct Approach |
|-----------|---------------------|
| What students do wrong | What they should do instead |

## 🎯 Exam Tips
- Numbered list of practical tips
- How to structure answers
- Time management advice
- Key phrases to use

## 📝 Practice Scenarios
Provide 2-3 example scenarios with:
1. **Facts**: Brief situation
2. **Issue**: What legal question arises
3. **Analysis**: How to approach it
4. **Conclusion**: Expected outcome

FORMATTING REQUIREMENTS:
- Use valid Markdown (headers, bold, tables, lists)
- Use Mermaid syntax for ALL flowcharts and diagrams (not ASCII art)
- Use Markdown tables (not ASCII tables)
- Use emojis for visual appeal: ✅ ❌ ⚠️ 💡 📌
- Cite articles properly: **Art. 6:74 DCC**
- Keep content detailed but well-organized"""

        content_blocks.append({
            "type": "text",
            "text": prompt_text
        })

        # System prompt emphasizing accuracy and grounding in provided materials
        # Use list format with cache_control to cache the system prompt
        system_blocks = [{
            "type": "text",
            "text": """You are an expert legal education content creator for University of Groningen law students.

CRITICAL REQUIREMENTS:
- ONLY use information explicitly stated in the provided documents
- DO NOT invent, assume, or hallucinate any legal rules, articles, or case law
- If information is not in the documents, do not include it
- Cite specific documents when referencing information
- Use proper Dutch legal terminology and article citations (e.g., Art. 6:74 DCC)

OUTPUT QUALITY:
- Create clear, well-organized study materials
- Use Mermaid diagrams for flowcharts and decision trees
- Use Markdown tables for structured information
- Make content visually appealing and easy to scan
- Focus on exam-relevant material""",
            "cache_control": {"type": "ephemeral"}  # Cache the system prompt
        }]

        # Use extended thinking for better reasoning and accuracy
        # Note: temperature must be 1 when using extended thinking (API requirement)
        # Extended thinking helps reduce hallucinations through careful reasoning
        #
        # Prompt Caching Benefits:
        # - System prompt: cached (static, never changes)
        # - Document content: cached (same documents reused across requests)
        # - Cache TTL: 5 minutes, refreshed on each use
        # - Cost reduction: ~90% cheaper for cached tokens on cache hits
        #
        # Retry logic for rate limits with exponential backoff
        max_retries = 5
        base_delay = 60  # Start with 60 seconds (rate limit is per minute)

        for attempt in range(max_retries):
            try:
                client = self._get_anthropic_client()
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=16000,  # Increased to accommodate thinking + output
                    thinking={
                        "type": "enabled",
                        "budget_tokens": 5000  # Allow up to 5000 tokens for reasoning
                    },
                    system=system_blocks,
                    messages=[{"role": "user", "content": content_blocks}]
                )
                break  # Success, exit retry loop
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 60s, 120s, 240s, 480s
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "⏳ Rate limit hit (attempt %d/%d). Waiting %d seconds before retry...",
                        attempt + 1, max_retries, delay
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("❌ Rate limit exceeded after %d attempts", max_retries)
                    raise

        # Log cache statistics from the response
        usage = response.usage
        cache_created = getattr(usage, 'cache_creation_input_tokens', 0) or 0
        cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
        input_tokens = getattr(usage, 'input_tokens', 0) or 0
        output_tokens = getattr(usage, 'output_tokens', 0) or 0

        if cache_read > 0:
            cache_hit_pct = (cache_read / (input_tokens + cache_read)) * 100 if input_tokens else 0
            logger.info(
                "📦 CACHE HIT: %d tokens read from cache (%.1f%% cached), %d new input tokens",
                cache_read, cache_hit_pct, input_tokens
            )
        elif cache_created > 0:
            logger.info(
                "📝 CACHE MISS: %d tokens written to cache for future requests",
                cache_created
            )
        else:
            logger.info("⚠️ No cache activity detected")

        logger.info(
            "💰 Token usage - Input: %d, Output: %d, Cache read: %d, Cache created: %d",
            input_tokens, output_tokens, cache_read, cache_created
        )

        # Track usage if user context provided
        await track_llm_usage_from_response(
            response=response,
            user_context=user_context,
            operation_type="study_guide",
            model="claude-sonnet-4-20250514",
            request_metadata={
                "topic": topic,
                "week_numbers": week_numbers,
                "materials_count": len(materials_with_text),
            },
        )

        # With extended thinking, response has thinking blocks and text blocks
        # Extract just the text content (not the thinking)
        guide = ""
        for block in response.content:
            if block.type == "text":
                guide += block.text

        logger.info(
            "Generated study guide: %d characters from %d materials",
            len(guide), len(materials_with_text)
        )
        return guide

    async def explain_article(
        self,
        article: str,
        code: str = "DCC",
        use_reader: bool = True
    ) -> str:
        """
        Explain a legal article using course materials.

        Args:
            article: Article number (e.g., "6:74")
            code: Legal code
            use_reader: Whether to include LLS Reader

        Returns:
            Detailed explanation
        """
        logger.info("Explaining Art. %s %s", article, code)

        content_blocks = []

        # Add LLS Reader if requested
        if use_reader and "lls_reader" in self.file_ids:
            reader_id = self.get_file_id("lls_reader")
            content_blocks.append({
                "type": "document",
                "source": {"type": "file", "file_id": reader_id},
                "title": "LLS Course Reader",
                "citations": {"enabled": True}
            })

        # Add prompt
        prompt_text = """Explain Art. %s %s in detail.

Provide:
1. **Full Article Text** (if available in documents)
2. **Purpose** - What this article is for
3. **Key Elements** - Requirements/components
4. **Common Applications** - When it's used
5. **Related Articles** - Connected provisions
6. **Exam Tips** - How to apply in exam
7. **Example Scenario** - Practical example

Use visual formatting with headers, ✅, ❌, ⚠️, etc.
Cite page numbers if available.""" % (article, code)

        content_blocks.append({
            "type": "text",
            "text": prompt_text
        })

        client = self._get_anthropic_client()
        response = await client.beta.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            betas=[self.beta_header],
            messages=[{"role": "user", "content": content_blocks}]
        )

        return response.content[0].text

    async def generate_case_analysis(
        self,
        case_facts: str,
        topic: str,
        relevant_files: Optional[List[str]] = None
    ) -> str:
        """
        Analyze a case using course materials.

        Args:
            case_facts: Description of case
            topic: Legal topic
            relevant_files: Optional specific files to use

        Returns:
            Case analysis
        """
        logger.info("Generating case analysis for %s", topic)

        content_blocks = []

        # Use relevant files or default to reader
        if relevant_files:
            for key in relevant_files:
                try:
                    file_id = self.get_file_id(key)
                    content_blocks.append({
                        "type": "document",
                        "source": {"type": "file", "file_id": file_id}
                    })
                except ValueError as e:
                    logger.warning("Skipping file '%s': %s", key, e)
                    continue
        elif "lls_reader" in self.file_ids:
            try:
                reader_id = self.get_file_id("lls_reader")
            except ValueError as e:
                logger.error("Failed to get lls_reader: %s", e)
                raise
            content_blocks.append({
                "type": "document",
                "source": {"type": "file", "file_id": reader_id}
            })

        prompt_text = """Analyze this %s case:

%s

Provide structured analysis:

## STEP 1: Identify Legal Questions
[What needs to be determined?]

## STEP 2: Applicable Law
[Relevant articles with citations]

## STEP 3: Analysis
[Apply law to facts systematically]

## STEP 4: Conclusion
[Clear answer with reasoning]

Use proper legal analysis method and cite articles.""" % (topic, case_facts)

        content_blocks.append({
            "type": "text",
            "text": prompt_text
        })

        client = self._get_anthropic_client()
        response = await client.beta.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            betas=[self.beta_header],
            messages=[{"role": "user", "content": content_blocks}]
        )

        return response.content[0].text

    def _sanitize_topic(self, topic: str | None, default: str = DEFAULT_TOPIC) -> str:
        """Sanitize and validate topic parameter to prevent prompt injection.

        Args:
            topic: The topic string to sanitize (can be None)
            default: Default value if topic is None or empty (defaults to DEFAULT_TOPIC constant)

        Returns:
            Sanitized topic string

        Raises:
            ValueError: If topic is too long, only whitespace, or contains suspicious patterns
        """
        # Handle None or empty string consistently - return default
        if topic is None or topic == '':
            return default

        # Strip whitespace and validate non-empty
        # If topic becomes empty after stripping, return default (consistent behavior)
        topic = topic.strip()
        if not topic:
            return default

        # Validate length BEFORE normalization
        if len(topic) > MAX_TOPIC_LENGTH:
            raise ValueError(f"topic must not exceed {MAX_TOPIC_LENGTH} characters")

        # Unicode normalization to prevent homoglyph and zero-width character attacks
        # NFKC normalization converts visually similar characters to canonical form
        # Examples: ℀ -> a/c, ﬁ -> fi, zero-width spaces removed
        # WARNING: NFKC can EXPAND character count (e.g., ℀ becomes 3 chars: a/c)
        topic = unicodedata.normalize('NFKC', topic)

        # Remove zero-width characters that could be used for obfuscation
        # Zero-width space (U+200B), zero-width joiner (U+200D), etc.
        zero_width_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\ufeff',  # Zero-width no-break space (BOM)
        ]
        for char in zero_width_chars:
            topic = topic.replace(char, '')

        # Re-validate length AFTER normalization (CRITICAL: NFKC can expand character count)
        # Example: A topic with 200 compatibility chars could expand beyond limit
        if len(topic) > MAX_TOPIC_LENGTH:
            raise ValueError(f"topic must not exceed {MAX_TOPIC_LENGTH} characters after normalization")

        # Normalize topic for pattern matching to catch obfuscation attempts
        # Remove excessive whitespace and normalize to single spaces
        normalized_topic = re.sub(r'\s+', ' ', topic)

        # Check for suspicious prompt injection patterns using compiled regex (faster)
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(normalized_topic):
                raise ValueError("topic contains suspicious content that may be a prompt injection attempt")

        # Sanitize topic by escaping special characters that could manipulate AI behavior
        # IMPORTANT: Escape backslashes FIRST to prevent bypass attacks (e.g., \")
        topic = topic.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')

        # Also escape other Unicode whitespace characters
        topic = topic.replace('\t', ' ').replace('\u2028', ' ').replace('\u2029', ' ')

        # Final check: After all normalization and sanitization, ensure topic is not empty
        # This catches edge cases where topic becomes empty after processing
        # (e.g., topic was only zero-width chars, or only special chars that got replaced)
        topic = topic.strip()
        if not topic:
            return default

        return topic

    async def generate_flashcards(
        self,
        topic: str,
        file_keys: List[str],
        num_cards: int = 20
    ) -> List[Dict]:
        """
        Generate flashcards from files (legacy method).

        Args:
            topic: Topic name
            file_keys: Files to use
            num_cards: Number of flashcards to generate (5-50)

        Returns:
            List of flashcard dictionaries

        Raises:
            ValueError: If file_keys is empty, topic is invalid, or num_cards out of range
            TypeError: If file_keys contains non-string values
        """
        # Input validation
        if not file_keys:
            raise ValueError("file_keys cannot be empty")
        if not all(isinstance(k, str) for k in file_keys):
            raise TypeError("All file_keys must be strings")

        # Validate num_cards range (consistent with course-aware method)
        if not MIN_FLASHCARDS <= num_cards <= MAX_FLASHCARDS:
            raise ValueError(f"num_cards must be between {MIN_FLASHCARDS} and {MAX_FLASHCARDS}")

        # Sanitize topic using shared method
        topic = self._sanitize_topic(topic)

        content_blocks = []

        for key in file_keys:
            try:
                file_id = self.get_file_id(key)
                content_blocks.append({
                    "type": "document",
                    "source": {"type": "file", "file_id": file_id}
                })
            except ValueError as e:
                logger.warning("Skipping file '%s': %s", key, e)
                continue

        prompt_text = """Generate %d flashcards for %s.

Return ONLY valid JSON:
{
  "flashcards": [
    {
      "front": "What is consensus?",
      "back": "Meeting of the minds between parties (Art. 3:33 DCC)..."
    }
  ]
}

Include:
- Article definitions
- Key concepts
- Legal principles
- Procedural rules""" % (num_cards, topic)

        content_blocks.append({
            "type": "text",
            "text": prompt_text
        })

        client = self._get_anthropic_client()
        response = await client.beta.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            betas=[self.beta_header],
            messages=[{"role": "user", "content": content_blocks}]
        )

        data = self._parse_json(response.content[0].text)
        return data.get("flashcards", [])

    async def generate_flashcards_from_course(
        self,
        course_id: str,
        topic: str,
        num_cards: int = 20,
        week_number: Optional[int] = None
    ) -> List[Dict]:
        """Generate flashcards using Firestore materials with text extraction.

        This method uses the materials subcollection in Firestore and
        extracts text from local files to send as content blocks.

        Args:
            course_id: Course ID
            topic: Topic name for the flashcards
            num_cards: Number of flashcards to generate (5-50)
            week_number: Optional week filter

        Returns:
            List of flashcard dictionaries with 'front' and 'back' keys

        Raises:
            ValueError: If no materials found or invalid parameters
        """
        # Input validation
        if not course_id or not course_id.strip():
            raise ValueError("course_id is required and cannot be empty")
        if not MIN_FLASHCARDS <= num_cards <= MAX_FLASHCARDS:
            raise ValueError(f"num_cards must be between {MIN_FLASHCARDS} and {MAX_FLASHCARDS}")
        if week_number is not None and not 1 <= week_number <= MAX_WEEK_NUMBER:
            raise ValueError(f"week_number must be between 1 and {MAX_WEEK_NUMBER}")

        # Sanitize topic using shared method
        topic = self._sanitize_topic(topic)

        logger.info(
            "Generating flashcards from course %s: %d cards, week=%s, topic=%s",
            course_id, num_cards, week_number, topic
        )

        # Get materials with their extracted text content
        materials_with_text = await self.get_course_materials_with_text(
            course_id=course_id,
            week_number=week_number,
            limit=MAX_MATERIALS_PER_GENERATION
        )

        if not materials_with_text:
            # Include week context in error message for better debugging
            week_msg = f" for week {week_number}" if week_number else ""
            raise ValueError(f"No materials found for course {course_id}{week_msg}")

        # Build content blocks using extracted text
        content_blocks = []

        # Add each document's content as a text block with clear labeling
        for material, text in materials_with_text:
            title = material.title or material.filename
            document_block = f"""
=== DOCUMENT: {title} ===
{text}
=== END OF {title} ===
"""
            content_blocks.append({
                "type": "text",
                "text": document_block
            })

        # Add the flashcard generation prompt
        prompt_text = """Based on the documents provided above, generate %d flashcards for %s.

Return ONLY valid JSON:
{
  "flashcards": [
    {
      "front": "What is consensus?",
      "back": "Meeting of the minds between parties (Art. 3:33 DCC). Both parties must intend to be legally bound and agree on essential terms."
    }
  ]
}

Include:
- Article definitions with citations
- Key legal concepts and principles
- Important procedural rules
- Common legal terms
- Case law principles

Make flashcards clear, concise, and exam-focused.""" % (num_cards, topic)

        content_blocks.append({
            "type": "text",
            "text": prompt_text
        })

        logger.info(
            "Sending %d content blocks to Anthropic (from %d materials)",
            len(content_blocks),
            len(materials_with_text)
        )

        # Call API (no Files API beta header needed)
        client = self._get_anthropic_client()
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": content_blocks
            }]
        )

        # Parse response
        text = response.content[0].text
        data = self._parse_json(text)
        flashcards = data.get("flashcards", [])

        logger.info(
            "Generated %d flashcards from %d materials",
            len(flashcards),
            len(materials_with_text)
        )
        return flashcards

    async def list_available_files(self) -> List[Dict]:
        """List all uploaded files from Anthropic API."""
        try:
            client = self._get_anthropic_client()
            response = await client.beta.files.list()

            files = []
            for file_item in response.data:
                files.append({
                    "id": file_item.id,
                    "filename": file_item.filename,
                    "size_bytes": file_item.size_bytes,
                    "size_mb": round(file_item.size_bytes / (1024 * 1024), 2),
                    "created_at": file_item.created_at
                })

            return files
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error listing files: %s", e)
            return []

    # ========== Helper Methods ==========

    def _parse_json(self, text: str) -> Dict:
        """Parse JSON from AI response, handling markdown code blocks."""
        # Remove markdown code blocks
        if "```json" in text:
            match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
            if match:
                text = match.group(1)
        elif "```" in text:
            match = re.search(r'```\n(.*?)\n```', text, re.DOTALL)
            if match:
                text = match.group(1)

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON: %s", e)
            logger.error("Text was: %s", text[:500])
            raise ValueError("Invalid JSON response: %s" % e) from e

    def get_files_by_tier(self, tier: str) -> List[str]:
        """Get all file keys for a specific tier."""
        return [key for key, info in self.file_ids.items()
                if info.get("tier") == tier]

    def get_files_by_subject(self, subject: str) -> List[str]:
        """Get all file keys for a specific subject."""
        return [key for key, info in self.file_ids.items()
                if info.get("subject", "").lower() == subject.lower()]

    def get_prioritized_files(self, file_keys: List[str]) -> List[str]:
        """
        Sort file keys by tier priority (Syllabus first, then Course_Materials, then Supplementary_Sources).

        Args:
            file_keys: List of file keys to sort

        Returns:
            Sorted list with highest priority (lowest tier_priority number) first
        """
        def get_priority(key: str) -> int:
            file_info = self.file_ids.get(key, {})
            return file_info.get("tier_priority", 999)  # Default to low priority if not found

        return sorted(file_keys, key=get_priority)

    def get_topic_files(self, topic: str) -> List[str]:
        """
        Get recommended file keys for a topic, prioritized by tier.

        Now uses the three-tier structure:
        - Tier 1 (Syllabus): Highest priority
        - Tier 2 (Course_Materials): Medium priority
        - Tier 3 (Supplementary_Sources): Lowest priority

        Args:
            topic: Topic name (e.g., "Criminal Law", "Administrative Law")

        Returns:
            List of file keys sorted by tier priority
        """

        # Map topics to subjects in the new structure
        topic_to_subject = {
            "Criminal Law": "Criminal_Law",
            "Administrative Law": "Administrative_Law",
            "Private Law": "Private_Law",
            "Constitutional Law": "Constitutional_Law",
            "International Law": "International_Law"
        }

        subject = topic_to_subject.get(topic)

        if not subject:
            # If topic not recognized, return all files sorted by priority
            logger.warning("Topic '%s' not recognized, returning all files", topic)
            all_keys = list(self.file_ids.keys())
            return self.get_prioritized_files(all_keys)

        # Get files for this subject
        subject_files = self.get_files_by_subject(subject)

        if not subject_files:
            # Fallback: try to find files with topic name in key
            logger.warning("No files found for subject '%s', searching by keyword", subject)
            subject_files = [key for key in self.file_ids.keys()
                           if topic.lower().replace(" ", "_") in key.lower()]

        # Sort by tier priority (Syllabus first, then Course_Materials, then Supplementary_Sources)
        prioritized_files = self.get_prioritized_files(subject_files)

        if not prioritized_files:
            # No files found for this topic - return empty list with clear logging
            logger.warning("No files found for topic '%s', returning empty list", topic)
            return []

        logger.info("Found %d files for topic '%s'", len(prioritized_files), topic)
        return prioritized_files

    # ========== Course-Aware Methods (Phase 3) ==========

    def get_files_for_course(
        self,
        course_id: str,
        week_number: Optional[int] = None
    ) -> List[str]:
        """
        Get file keys for a course from Firestore, optionally filtered by week.

        This method looks up the course in Firestore and returns files based on
        the course's materialSubjects configuration.

        Args:
            course_id: Course ID (e.g., "LLS-2025-2026")
            week_number: Optional week number to filter materials (1-52)

        Returns:
            List of file keys sorted by tier priority

        Raises:
            ValueError: If course not found
        """
        course_service = self._get_course_service()

        # Get course from Firestore
        course = course_service.get_course(course_id, include_weeks=week_number is not None)
        if course is None:
            raise ValueError(f"Course not found: {course_id}")

        # Get material subjects from course
        material_subjects = course.materialSubjects or []

        if not material_subjects:
            logger.warning("Course %s has no materialSubjects configured", course_id)
            return []

        # Collect all files for the course's material subjects
        all_files = []
        for subject in material_subjects:
            subject_files = self.get_files_by_subject(subject)
            all_files.extend(subject_files)

        # If week-specific filtering requested
        if week_number is not None and course.weeks:
            # Find the week
            week = next(
                (w for w in course.weeks if w.weekNumber == week_number),
                None
            )
            if week and week.materials:
                # Filter to materials listed in the week
                week_material_files = []
                for material in week.materials:
                    if hasattr(material, 'file') and material.file:
                        # Try to find matching file key
                        matching_keys = [
                            key for key in all_files
                            if material.file in self.file_ids.get(key, {}).get("filename", "")
                        ]
                        week_material_files.extend(matching_keys)

                if week_material_files:
                    all_files = week_material_files
                    logger.info(
                        "Filtered to %d week %d materials for course %s",
                        len(all_files), week_number, course_id
                    )

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in all_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        # Sort by tier priority
        prioritized = self.get_prioritized_files(unique_files)

        logger.info(
            "Found %d files for course %s (subjects: %s)",
            len(prioritized), course_id, material_subjects
        )
        return prioritized

    def get_files_for_course_weeks(
        self,
        course_id: str,
        week_numbers: List[int]
    ) -> List[str]:
        """
        Get file keys for multiple weeks in a course with a single Firestore read.

        This method avoids the N+1 query problem by fetching the course once
        and filtering by multiple weeks locally.

        Args:
            course_id: Course ID (e.g., "LLS-2025-2026")
            week_numbers: List of week numbers to get materials for

        Returns:
            List of unique file keys sorted by tier priority

        Raises:
            ValueError: If course not found
        """
        course_service = self._get_course_service()

        # Single Firestore read - include_weeks=True to get all weeks
        course = course_service.get_course(course_id, include_weeks=True)
        if course is None:
            raise ValueError(f"Course not found: {course_id}")

        # Get material subjects from course
        material_subjects = course.materialSubjects or []

        if not material_subjects:
            logger.warning("Course %s has no materialSubjects configured", course_id)
            return []

        # Collect all files for the course's material subjects
        all_files = []
        for subject in material_subjects:
            subject_files = self.get_files_by_subject(subject)
            all_files.extend(subject_files)

        # Filter by requested weeks
        if course.weeks and week_numbers:
            week_material_files = []
            for week_num in week_numbers:
                week = next(
                    (w for w in course.weeks if w.weekNumber == week_num),
                    None
                )
                if week and week.materials:
                    for material in week.materials:
                        if hasattr(material, 'file') and material.file:
                            matching_keys = [
                                key for key in all_files
                                if material.file in self.file_ids.get(key, {}).get("filename", "")
                            ]
                            week_material_files.extend(matching_keys)

            if week_material_files:
                all_files = week_material_files
                logger.info(
                    "Filtered to %d materials for weeks %s in course %s",
                    len(all_files), week_numbers, course_id
                )

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in all_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        # Sort by tier priority
        prioritized = self.get_prioritized_files(unique_files)

        logger.info(
            "Found %d files for course %s weeks %s",
            len(prioritized), course_id, week_numbers
        )
        return prioritized

    def get_course_topics(self, course_id: str) -> List[Dict]:
        """
        Get topics covered in a course from Firestore.

        Returns topics from all weeks in the course.

        Args:
            course_id: Course ID

        Returns:
            List of topic dictionaries with id, name, and description

        Raises:
            ValueError: If course not found
        """
        course_service = self._get_course_service()

        course = course_service.get_course(course_id, include_weeks=True)
        if course is None:
            raise ValueError(f"Course not found: {course_id}")

        topics = []
        seen_topics = set()

        # Extract topics from each week
        for week in course.weeks or []:
            for topic in week.topics or []:
                # Create normalized topic id
                topic_id = topic.lower().replace(" ", "_").replace("-", "_")
                if topic_id not in seen_topics:
                    seen_topics.add(topic_id)
                    topics.append({
                        "id": topic_id,
                        "name": topic,
                        "description": f"Week {week.weekNumber}: {week.title or 'No title'}",
                        "week": week.weekNumber
                    })

        logger.info("Found %d topics for course %s", len(topics), course_id)
        return topics

    def get_week_key_concepts(
        self,
        course_id: str,
        week_number: int
    ) -> List[Dict]:
        """
        Get key concepts for a specific week in a course.

        Args:
            course_id: Course ID
            week_number: Week number (1-52)

        Returns:
            List of key concept dictionaries

        Raises:
            ValueError: If course or week not found
        """
        course_service = self._get_course_service()

        week = course_service.get_week(course_id, week_number)
        if week is None:
            raise ValueError(f"Week {week_number} not found in course {course_id}")

        concepts = []
        for concept in week.keyConcepts or []:
            concepts.append({
                "term": concept.term,
                "definition": concept.definition,
                "source": concept.source,
                "citation": getattr(concept, 'citation', None)
            })

        logger.info(
            "Found %d key concepts for week %d of course %s",
            len(concepts), week_number, course_id
        )
        return concepts

    def get_legal_skill_framework(
        self,
        course_id: str,
        skill_id: str
    ) -> Optional[Dict]:
        """
        Get a legal skill framework from a course.

        Args:
            course_id: Course ID
            skill_id: Skill ID (e.g., "ecthr_case_analysis")

        Returns:
            Legal skill dictionary or None if not found
        """
        course_service = self._get_course_service()

        skills = course_service.get_legal_skills(course_id)
        skill = skills.get(skill_id)

        if skill:
            return {
                "id": skill_id,
                "name": skill.name,
                "description": skill.description,
                "steps": [
                    {"step": s.step, "description": s.description}
                    for s in (skill.decisionModel.steps if skill.decisionModel else [])
                ]
            }

        return None


# Singleton
_files_api_service = None  # pylint: disable=invalid-name


def get_files_api_service() -> FilesAPIService:
    """Get or create Files API service singleton."""
    global _files_api_service  # pylint: disable=global-statement
    if _files_api_service is None:
        _files_api_service = FilesAPIService()
    return _files_api_service
