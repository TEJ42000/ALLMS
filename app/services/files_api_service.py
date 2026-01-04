"""Content Generation using Anthropic Files API for the LLS Study Portal.

This service provides AI-powered content generation (quizzes, study guides, flashcards)
using uploaded course materials. It can optionally integrate with CourseService to
get course-specific materials from Firestore.
"""

import json
import logging
import re
from typing import Dict, List, Optional

from anthropic import AsyncAnthropic

from app.services.gcp_service import get_anthropic_api_key

logger = logging.getLogger(__name__)

# Constants
DEFAULT_FALLBACK_COUNT = 5  # Number of files to return when no specific files found


class FilesAPIService:
    """Service for generating content using uploaded files via Anthropic Files API.

    This service can operate in two modes:
    1. **Legacy mode**: Uses hardcoded topic mappings (backward compatible)
    2. **Course-aware mode**: Uses CourseService to get course-specific materials

    The course-aware mode is activated by passing a course_id to methods like
    get_topic_files_for_course().
    """

    def __init__(self, file_ids_path: str = "file_ids.json"):
        """
        Initialize the Files API service.

        Args:
            file_ids_path: Path to the JSON file containing uploaded file IDs.
        """
        self.client = AsyncAnthropic(api_key=get_anthropic_api_key())

        # Load uploaded file IDs
        try:
            with open(file_ids_path, "r", encoding="utf-8") as f:
                self.file_ids = json.load(f)
            logger.info("Loaded %d file IDs", len(self.file_ids))
        except FileNotFoundError:
            logger.warning("file_ids.json not found! Run upload_files_script.py first")
            self.file_ids = {}

        # Beta header for Files API
        self.beta_header = "files-api-2025-04-14"

        # Lazy-loaded CourseService reference
        self._course_service = None

    def _get_course_service(self):
        """Get CourseService instance (lazy loading to avoid circular imports)."""
        if self._course_service is None:
            from app.services.course_service import get_course_service
            self._course_service = get_course_service()
        return self._course_service

    def get_file_id(self, key: str) -> str:
        """Get file_id for a course material."""
        file_info = self.file_ids.get(key)
        if not file_info:
            raise ValueError("File '%s' not found in file_ids.json" % key)
        return file_info["file_id"]

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

        # Call API
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
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

    async def generate_study_guide(
        self,
        topic: str,
        file_keys: List[str]
    ) -> str:
        """
        Generate comprehensive study guide from files.

        Args:
            topic: Topic name
            file_keys: Files to use

        Returns:
            Formatted study guide

        Raises:
            ValueError: If file_keys is empty
            TypeError: If file_keys contains non-string values
        """
        # Input validation
        if not file_keys:
            raise ValueError("file_keys cannot be empty")
        if not all(isinstance(k, str) for k in file_keys):
            raise TypeError("All file_keys must be strings")

        logger.info("Generating study guide for %s using %d files", topic, len(file_keys))

        # Build content
        content_blocks = []

        for key in file_keys:
            try:
                file_id = self.get_file_id(key)
                content_blocks.append({
                    "type": "document",
                    "source": {"type": "file", "file_id": file_id},
                    "citations": {"enabled": True}
                })
            except ValueError as e:
                logger.warning("Skipping file '%s': %s", key, e)
                continue

        prompt_text = """Create a comprehensive study guide for %s.

Include:
## Key Concepts
- All core concepts mentioned in Materials
- Important definitions
- Detailed, well illustrated and visualised decision models
- Prioritize making the study guide visual and easy to understand, while presenting all course information in great detail

## Important Articles
- List with brief explanations
- Include article numbers
- Explain the articles purpose and context

## Common Mistakes
- What students often get wrong (use ❌)
- Correct approaches (use ✅)

## Exam Tips
- How to approach questions
- What to remember

## Practice Scenarios
- Example situations to analyze

Use visual formatting:
- Use valid Markdown formatting 
- ✅ for correct info
- ❌ for mistakes
- ⚠️ for warnings
- Bold **key terms**
- Cite articles properly""" % topic

        content_blocks.append({
            "type": "text",
            "text": prompt_text
        })

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": content_blocks}]
        )

        guide = response.content[0].text
        logger.info("Generated study guide: %d characters", len(guide))
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

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
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

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            messages=[{"role": "user", "content": content_blocks}]
        )

        return response.content[0].text

    async def generate_flashcards(
        self,
        topic: str,
        file_keys: List[str],
        num_cards: int = 20
    ) -> List[Dict]:
        """
        Generate flashcards from files.

        Args:
            topic: Topic name
            file_keys: Files to use
            num_cards: Number of flashcards to generate

        Returns:
            List of flashcard dictionaries

        Raises:
            ValueError: If file_keys is empty
            TypeError: If file_keys contains non-string values
        """
        # Input validation
        if not file_keys:
            raise ValueError("file_keys cannot be empty")
        if not all(isinstance(k, str) for k in file_keys):
            raise TypeError("All file_keys must be strings")

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

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": content_blocks}]
        )

        data = self._parse_json(response.content[0].text)
        return data.get("flashcards", [])

    async def list_available_files(self) -> List[Dict]:
        """List all uploaded files from Anthropic API."""
        try:
            response = await self.client.beta.files.list()

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
