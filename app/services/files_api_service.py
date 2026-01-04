"""Content Generation using Anthropic Files API for the LLS Study Portal."""

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
    """Service for generating content using uploaded files via Anthropic Files API."""

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
- Each question tests understanding of legal concepts
- Include article citations (e.g., Art. 6:74 DCC)
- Provide 4 answer options
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
- Main legal principles
- Important definitions

## Important Articles
- List with brief explanations
- Include article numbers

## Common Mistakes
- What students often get wrong (use ❌)
- Correct approaches (use ✅)

## Exam Tips
- How to approach questions
- What to remember

## Practice Scenarios
- Example situations to analyze

Use visual formatting:
- ## for sections
- ### for subsections with 💡
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


# Singleton
_files_api_service = None  # pylint: disable=invalid-name


def get_files_api_service() -> FilesAPIService:
    """Get or create Files API service singleton."""
    global _files_api_service  # pylint: disable=global-statement
    if _files_api_service is None:
        _files_api_service = FilesAPIService()
    return _files_api_service
