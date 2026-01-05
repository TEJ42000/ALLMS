"""Tests for Files API Content endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.files_api_service import FilesAPIService


class TestFilesContentQuizEndpoint:
    """Tests for the /api/files-content/quiz endpoint."""

    def test_quiz_generation_success(self, client):
        """Test successful quiz generation."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_private_law"]
        mock_service.generate_quiz_from_files = AsyncMock(return_value=[
            {
                "question": "What is Art. 6:74?",
                "options": ["A", "B", "C", "D"],
                "correct": 0
            }
        ])

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/quiz", json={
                "topic": "Private Law",
                "num_questions": 5,
                "difficulty": "medium"
            })

            assert response.status_code == 200
            data = response.json()
            assert "quiz" in data
            assert "files_used" in data

    def test_quiz_with_week_parameter(self, client):
        """Test quiz generation with week parameter."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_admin_law"]
        mock_service.generate_quiz_from_files = AsyncMock(return_value=[])

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/quiz", json={
                "topic": "Administrative Law",
                "week": 3,
                "num_questions": 10,
                "difficulty": "hard"
            })

            assert response.status_code == 200


class TestFilesContentStudyGuideEndpoint:
    """Tests for the /api/files-content/study-guide endpoint."""

    def test_study_guide_generation_success(self, client):
        """Test successful study guide generation."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_criminal_law"]
        mock_service.generate_study_guide = AsyncMock(
            return_value="# Study Guide\n\nContent..."
        )

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/study-guide", json={
                "topic": "Criminal Law"
            })

            assert response.status_code == 200
            data = response.json()
            assert "guide" in data
            assert "topic" in data


class TestFilesContentArticleExplainEndpoint:
    """Tests for the /api/files-content/explain-article endpoint."""

    def test_article_explanation_success(self, client):
        """Test successful article explanation."""
        mock_service = MagicMock()
        mock_service.explain_article = AsyncMock(
            return_value="Art. 6:74 DCC establishes..."
        )

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/explain-article", json={
                "article": "6:74",
                "code": "DCC"
            })

            assert response.status_code == 200
            data = response.json()
            assert "article" in data
            assert "explanation" in data
            assert "Art. 6:74 DCC" in data["article"]


class TestFilesContentCaseAnalysisEndpoint:
    """Tests for the /api/files-content/case-analysis endpoint."""

    def test_case_analysis_success(self, client):
        """Test successful case analysis."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_admin_law"]
        mock_service.generate_case_analysis = AsyncMock(
            return_value="## Legal Analysis\n\n..."
        )

        case_facts = (
            "A municipality denied a permit without giving proper notice to "
            "the applicant. The applicant was not given an opportunity to be "
            "heard before the decision."
        )

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/case-analysis", json={
                "case_facts": case_facts,
                "topic": "Administrative Law"
            })

            assert response.status_code == 200
            data = response.json()
            assert "analysis" in data
            assert "topic" in data

    def test_case_analysis_short_facts_fails(self, client):
        """Test that too short case facts returns validation error."""
        response = client.post("/api/files-content/case-analysis", json={
            "case_facts": "Short facts",  # Less than 50 chars
            "topic": "Administrative Law"
        })

        assert response.status_code == 422


class TestFilesContentFlashcardsEndpoint:
    """Tests for the /api/files-content/flashcards endpoint."""

    def test_flashcards_generation_success(self, client):
        """Test successful flashcards generation."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_constitutional_law"]
        mock_service.generate_flashcards = AsyncMock(return_value=[
            {"front": "Art. 120", "back": "Prohibition of constitutional review"}
        ])

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/flashcards", json={
                "topic": "Constitutional Law",
                "num_cards": 10
            })

            assert response.status_code == 200
            data = response.json()
            assert "flashcards" in data
            assert "count" in data
            assert "topic" in data


class TestFilesContentInfoEndpoints:
    """Tests for information endpoints."""

    def test_available_files_endpoint(self, client):
        """Test listing available files."""
        mock_service = MagicMock()
        mock_service.list_available_files = AsyncMock(return_value=[
            {"id": "file1", "name": "reader.pdf", "size_mb": 1.5}
        ])

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.get("/api/files-content/available-files")

            assert response.status_code == 200
            data = response.json()
            assert "files" in data
            assert "count" in data

    def test_status_endpoint(self, client):
        """Test Files API status check."""
        mock_service = MagicMock()
        mock_service.file_ids = {"reader": {"id": "123"}}
        mock_service.list_available_files = AsyncMock(return_value=[])

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.get("/api/files-content/status")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_examples_endpoint(self, client):
        """Test usage examples endpoint."""
        response = client.get("/api/files-content/examples")

        assert response.status_code == 200
        data = response.json()
        assert "quiz" in data
        assert "study_guide" in data
        assert "explain_article" in data


class TestThreeTierMaterialsStructure:
    """Tests for three-tier materials structure functionality."""

    def test_get_files_by_tier(self):
        """Test get_files_by_tier() method."""
        service = FilesAPIService()
        service.file_ids = {
            "syllabus_criminal_law_part_a": {"tier": "Syllabus", "tier_priority": 1},
            "course_materials_criminal_law_lecture": {"tier": "Course_Materials", "tier_priority": 2},
            "supplementary_sources_case_law": {"tier": "Supplementary_Sources", "tier_priority": 3},
            "syllabus_admin_law": {"tier": "Syllabus", "tier_priority": 1}
        }

        # Test Tier 1 (Syllabus)
        result = service.get_files_by_tier("Syllabus")
        assert len(result) == 2
        assert "syllabus_criminal_law_part_a" in result
        assert "syllabus_admin_law" in result

        # Test Tier 2 (Course_Materials)
        result = service.get_files_by_tier("Course_Materials")
        assert len(result) == 1
        assert "course_materials_criminal_law_lecture" in result

        # Test Tier 3 (Supplementary_Sources)
        result = service.get_files_by_tier("Supplementary_Sources")
        assert len(result) == 1
        assert "supplementary_sources_case_law" in result

        # Test non-existent tier
        result = service.get_files_by_tier("NonExistent")
        assert len(result) == 0

    def test_get_files_by_subject(self):
        """Test get_files_by_subject() method."""
        service = FilesAPIService()
        service.file_ids = {
            "syllabus_crim_law": {"subject": "Criminal_Law", "tier": "Syllabus"},
            "course_crim_law_lecture": {"subject": "Criminal_Law", "tier": "Course_Materials"},
            "syllabus_admin_law": {"subject": "Administrative_Law", "tier": "Syllabus"},
            "course_private_law": {"subject": "Private_Law", "tier": "Course_Materials"}
        }

        # Test Criminal Law
        result = service.get_files_by_subject("Criminal_Law")
        assert len(result) == 2
        assert "syllabus_crim_law" in result
        assert "course_crim_law_lecture" in result

        # Test case-insensitive matching
        result = service.get_files_by_subject("criminal_law")
        assert len(result) == 2

        # Test Administrative Law
        result = service.get_files_by_subject("Administrative_Law")
        assert len(result) == 1
        assert "syllabus_admin_law" in result

        # Test non-existent subject
        result = service.get_files_by_subject("NonExistent")
        assert len(result) == 0

    def test_get_prioritized_files(self):
        """Test get_prioritized_files() method."""
        service = FilesAPIService()
        service.file_ids = {
            "tier3_file": {"tier": "Supplementary_Sources", "tier_priority": 3},
            "tier1_file": {"tier": "Syllabus", "tier_priority": 1},
            "tier2_file": {"tier": "Course_Materials", "tier_priority": 2},
            "tier1_file2": {"tier": "Syllabus", "tier_priority": 1}
        }

        # Test prioritization
        result = service.get_prioritized_files(["tier3_file", "tier1_file", "tier2_file", "tier1_file2"])

        # Should be sorted by tier_priority (1, 1, 2, 3)
        assert result[0] in ["tier1_file", "tier1_file2"]  # Both have priority 1
        assert result[1] in ["tier1_file", "tier1_file2"]
        assert result[2] == "tier2_file"
        assert result[3] == "tier3_file"

        # Test with empty list
        result = service.get_prioritized_files([])
        assert result == []

        # Test with files not in file_ids (should go to end with priority 999)
        result = service.get_prioritized_files(["tier1_file", "unknown_file", "tier3_file"])
        assert result[0] == "tier1_file"
        assert result[1] == "tier3_file"
        assert result[2] == "unknown_file"

    def test_get_topic_files_with_three_tier_structure(self):
        """Test get_topic_files() with three-tier structure."""
        service = FilesAPIService()
        service.file_ids = {
            "syllabus_criminal_law_part_a": {
                "tier": "Syllabus",
                "tier_priority": 1,
                "subject": "Criminal_Law"
            },
            "course_materials_criminal_law_lecture": {
                "tier": "Course_Materials",
                "tier_priority": 2,
                "subject": "Criminal_Law"
            },
            "supplementary_sources_case_law_echr": {
                "tier": "Supplementary_Sources",
                "tier_priority": 3,
                "subject": "Criminal_Law"
            },
            "syllabus_admin_law": {
                "tier": "Syllabus",
                "tier_priority": 1,
                "subject": "Administrative_Law"
            }
        }

        # Test Criminal Law - should return files sorted by tier priority
        result = service.get_topic_files("Criminal Law")
        assert len(result) == 3
        # First should be Syllabus (tier 1)
        assert result[0] == "syllabus_criminal_law_part_a"
        # Second should be Course_Materials (tier 2)
        assert result[1] == "course_materials_criminal_law_lecture"
        # Third should be Supplementary_Sources (tier 3)
        assert result[2] == "supplementary_sources_case_law_echr"

        # Test Administrative Law
        result = service.get_topic_files("Administrative Law")
        assert len(result) == 1
        assert result[0] == "syllabus_admin_law"

        # Test unrecognized topic - should return all files sorted by priority
        result = service.get_topic_files("Unknown Topic")
        assert len(result) == 4
        # Should start with Syllabus files (tier 1)
        assert result[0] in ["syllabus_criminal_law_part_a", "syllabus_admin_law"]

        # Test topic with no files - should return empty list
        service.file_ids = {}
        result = service.get_topic_files("Criminal Law")
        assert result == []


class TestInputValidation:
    """Tests for input validation in Files API service."""

    @pytest.mark.asyncio
    async def test_generate_quiz_empty_file_keys(self):
        """Test that generate_quiz_from_files raises ValueError for empty file_keys."""
        service = FilesAPIService()

        with pytest.raises(ValueError, match="file_keys cannot be empty"):
            await service.generate_quiz_from_files(
                file_keys=[],
                topic="Criminal Law",
                num_questions=10
            )

    @pytest.mark.asyncio
    async def test_generate_quiz_invalid_file_keys_type(self):
        """Test that generate_quiz_from_files raises TypeError for non-string file_keys."""
        service = FilesAPIService()

        with pytest.raises(TypeError, match="All file_keys must be strings"):
            await service.generate_quiz_from_files(
                file_keys=["valid_key", 123, "another_key"],
                topic="Criminal Law",
                num_questions=10
            )

    @pytest.mark.asyncio
    async def test_generate_study_guide_empty_file_keys(self):
        """Test that generate_study_guide raises ValueError for empty file_keys."""
        service = FilesAPIService()

        with pytest.raises(ValueError, match="file_keys cannot be empty"):
            await service.generate_study_guide(
                topic="Criminal Law",
                file_keys=[]
            )

    @pytest.mark.asyncio
    async def test_generate_study_guide_invalid_file_keys_type(self):
        """Test that generate_study_guide raises TypeError for non-string file_keys."""
        service = FilesAPIService()

        with pytest.raises(TypeError, match="All file_keys must be strings"):
            await service.generate_study_guide(
                topic="Criminal Law",
                file_keys=["valid_key", None, "another_key"]
            )

    @pytest.mark.asyncio
    async def test_generate_flashcards_empty_file_keys(self):
        """Test that generate_flashcards raises ValueError for empty file_keys."""
        service = FilesAPIService()

        with pytest.raises(ValueError, match="file_keys cannot be empty"):
            await service.generate_flashcards(
                topic="Criminal Law",
                file_keys=[],
                num_cards=20
            )

    @pytest.mark.asyncio
    async def test_generate_flashcards_invalid_file_keys_type(self):
        """Test that generate_flashcards raises TypeError for non-string file_keys."""
        service = FilesAPIService()

        with pytest.raises(TypeError, match="All file_keys must be strings"):
            await service.generate_flashcards(
                topic="Criminal Law",
                file_keys=[123, 456],
                num_cards=20
            )


class TestCourseAwareQuizEndpoint:
    """Tests for course-aware quiz generation."""

    def test_quiz_with_course_id(self, client):
        """Test quiz generation with course_id parameter."""
        mock_service = MagicMock()
        mock_service.get_files_for_course.return_value = ["reader_private_law"]
        mock_service.generate_quiz_from_files = AsyncMock(return_value=[
            {"question": "Test question", "options": ["A", "B"], "correct": 0}
        ])

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "num_questions": 5,
                "difficulty": "medium"
            })

            assert response.status_code == 200
            data = response.json()
            assert "quiz" in data
            assert data.get("course_id") == "LLS-2025-2026"
            mock_service.get_files_for_course.assert_called_once()

    def test_quiz_with_course_id_and_week(self, client):
        """Test quiz generation with course_id and week parameters."""
        mock_service = MagicMock()
        mock_service.get_files_for_course.return_value = ["lecture_week_3"]
        mock_service.generate_quiz_from_files = AsyncMock(return_value=[])

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "week": 3,
                "num_questions": 10,
                "difficulty": "hard"
            })

            assert response.status_code == 200
            data = response.json()
            assert data.get("course_id") == "LLS-2025-2026"
            assert data.get("week") == 3
            mock_service.get_files_for_course.assert_called_with(
                "LLS-2025-2026", week_number=3
            )

    def test_quiz_course_not_found(self, client):
        """Test quiz returns 404 when course not found."""
        mock_service = MagicMock()
        mock_service.get_files_for_course.side_effect = ValueError(
            "Course not found: INVALID"
        )

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "INVALID",
                "num_questions": 5,
                "difficulty": "medium"
            })

            assert response.status_code == 404
            assert "Course not found" in response.json()["detail"]

    def test_quiz_requires_topic_or_course_id(self, client):
        """Test quiz returns 400 when neither topic nor course_id provided."""
        mock_service = MagicMock()

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/quiz", json={
                "num_questions": 5,
                "difficulty": "medium"
            })

            assert response.status_code == 400
            assert "Either 'topic' or 'course_id'" in response.json()["detail"]


class TestCourseAwareStudyGuideEndpoint:
    """Tests for course-aware study guide generation."""

    def test_study_guide_with_course_id(self, client):
        """Test study guide generation with course_id parameter."""
        mock_service = MagicMock()
        mock_service.get_files_for_course.return_value = ["reader_criminal_law"]
        mock_service.generate_study_guide = AsyncMock(return_value={
            "sections": []
        })

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/study-guide", json={
                "course_id": "LLS-2025-2026"
            })

            assert response.status_code == 200
            data = response.json()
            assert "guide" in data
            assert data.get("course_id") == "LLS-2025-2026"

    def test_study_guide_with_course_id_and_weeks(self, client):
        """Test study guide with course_id and multiple weeks uses batch method."""
        mock_service = MagicMock()
        # Should use get_files_for_course_weeks for multiple weeks (N+1 fix)
        mock_service.get_files_for_course_weeks.return_value = [
            "lecture_week_2", "lecture_week_3"
        ]
        mock_service.generate_study_guide = AsyncMock(return_value={})

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/study-guide", json={
                "course_id": "LLS-2025-2026",
                "weeks": [2, 3]
            })

            assert response.status_code == 200
            data = response.json()
            assert data.get("weeks") == [2, 3]
            # Verify batch method was called instead of individual calls
            mock_service.get_files_for_course_weeks.assert_called_once_with(
                "LLS-2025-2026",
                week_numbers=[2, 3]
            )

    def test_study_guide_weeks_validation(self, client):
        """Test study guide rejects invalid week numbers via Pydantic."""
        response = client.post("/api/files-content/study-guide", json={
            "course_id": "LLS-2025-2026",
            "weeks": [0, 53]  # Invalid weeks
        })

        # Should return 422 Unprocessable Entity for validation error
        assert response.status_code == 422


class TestStudyGuideErrorHandling:
    """Tests for study guide error handling improvements (PR #65)."""

    def test_study_guide_no_materials_with_course_id(self, client):
        """Test study guide returns 400 when course has no materials."""
        mock_service = MagicMock()
        mock_service.get_files_for_course.return_value = []  # Empty file list

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/study-guide", json={
                "course_id": "Legal-History-2025-2026"
            })

            assert response.status_code == 400
            detail = response.json()["detail"]
            assert "No course materials available" in detail
            assert "Legal-History-2025-2026" in detail
            assert "contact your instructor" in detail

    def test_study_guide_no_materials_with_weeks(self, client):
        """Test study guide returns 400 when specific weeks have no materials."""
        mock_service = MagicMock()
        mock_service.get_files_for_course_weeks.return_value = []

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/study-guide", json={
                "course_id": "LLS-2025-2026",
                "weeks": [1, 2]
            })

            assert response.status_code == 400
            detail = response.json()["detail"]
            assert "No course materials available" in detail
            assert "weeks [1, 2]" in detail

    def test_study_guide_no_materials_legacy_mode(self, client):
        """Test study guide returns 400 in legacy mode with no materials."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = []

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/study-guide", json={
                "topic": "Nonexistent Topic"
            })

            assert response.status_code == 400
            detail = response.json()["detail"]
            assert "No course materials available" in detail
            assert "select a topic" in detail


class TestCourseAwareFlashcardsEndpoint:
    """Tests for course-aware flashcards generation."""

    def test_flashcards_with_course_id(self, client):
        """Test flashcards generation with course_id parameter."""
        mock_service = MagicMock()
        mock_service.get_files_for_course.return_value = ["reader_admin_law"]
        mock_service.generate_flashcards = AsyncMock(return_value=[
            {"front": "Q1", "back": "A1"},
            {"front": "Q2", "back": "A2"}
        ])

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/flashcards", json={
                "course_id": "LLS-2025-2026",
                "num_cards": 10
            })

            assert response.status_code == 200
            data = response.json()
            assert "flashcards" in data
            assert data.get("course_id") == "LLS-2025-2026"
            assert data["count"] == 2


class TestCourseFilesEndpoint:
    """Tests for /api/files-content/course-files/{course_id} endpoint."""

    def test_get_course_files(self, client):
        """Test getting files for a course."""
        mock_service = MagicMock()
        mock_service.get_files_for_course.return_value = ["file1", "file2"]
        mock_service.get_file_id.return_value = "file-id-123"
        mock_service.file_ids = {
            "file1": {"filename": "test.pdf", "tier": "Syllabus"},
            "file2": {"filename": "test2.pdf", "tier": "Course_Materials"}
        }

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.get("/api/files-content/course-files/LLS-2025-2026")

            assert response.status_code == 200
            data = response.json()
            assert data["course_id"] == "LLS-2025-2026"
            assert "files" in data
            assert data["count"] == 2

    def test_get_course_files_with_week(self, client):
        """Test getting files for a course filtered by week."""
        mock_service = MagicMock()
        mock_service.get_files_for_course.return_value = ["lecture_week_3"]
        mock_service.get_file_id.return_value = "file-id-456"
        mock_service.file_ids = {
            "lecture_week_3": {"filename": "week3.pdf", "tier": "Course_Materials"}
        }

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.get(
                "/api/files-content/course-files/LLS-2025-2026?week=3"
            )

            assert response.status_code == 200
            data = response.json()
            assert data.get("week") == 3
            mock_service.get_files_for_course.assert_called_with(
                "LLS-2025-2026", week_number=3
            )

    def test_get_course_files_not_found(self, client):
        """Test 404 when course not found."""
        mock_service = MagicMock()
        mock_service.get_files_for_course.side_effect = ValueError(
            "Course not found: INVALID"
        )

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.get("/api/files-content/course-files/INVALID")

            assert response.status_code == 404


class TestTopicsEndpointCourseAware:
    """Tests for course-aware /api/tutor/topics endpoint."""

    def test_topics_default(self, client):
        """Test topics endpoint returns default topics."""
        response = client.get("/api/tutor/topics")

        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        assert len(data["topics"]) == 5  # Default topics
        assert data["status"] == "success"

    def test_topics_with_course_id(self, client):
        """Test topics endpoint with course_id parameter."""
        mock_service = MagicMock()
        mock_service.get_course_topics.return_value = [
            {"id": "week1_intro", "name": "Introduction", "week": 1}
        ]

        # Patch the import inside the function
        with patch(
            'app.services.files_api_service.get_files_api_service',
            return_value=mock_service
        ):
            response = client.get("/api/tutor/topics?course_id=LLS-2025-2026")

            assert response.status_code == 200
            data = response.json()
            assert data.get("course_id") == "LLS-2025-2026"
            assert "topics" in data

    def test_topics_course_not_found(self, client):
        """Test topics returns 404 when course not found."""
        mock_service = MagicMock()
        mock_service.get_course_topics.side_effect = ValueError(
            "Course not found: INVALID"
        )

        # Patch the import inside the function
        with patch(
            'app.services.files_api_service.get_files_api_service',
            return_value=mock_service
        ):
            response = client.get("/api/tutor/topics?course_id=INVALID")

            assert response.status_code == 404


class TestWeekValidation:
    """Tests for week parameter validation."""

    def test_quiz_week_too_high(self, client):
        """Test quiz returns 400 for week > 52."""
        mock_service = MagicMock()

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "week": 100,
                "num_questions": 5,
                "difficulty": "medium"
            })

            # FastAPI validates Field(ge=1, le=52) at the Pydantic level
            assert response.status_code == 422

    def test_quiz_week_zero(self, client):
        """Test quiz returns 422 for week = 0."""
        mock_service = MagicMock()

        with patch(
            'app.routes.files_content.get_files_api_service',
            return_value=mock_service
        ):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "week": 0,
                "num_questions": 5,
                "difficulty": "medium"
            })

            assert response.status_code == 422
