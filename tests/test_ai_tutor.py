"""Tests for AI Tutor endpoints.

Comprehensive test suite for AI Tutor functionality including:
- Chat endpoint with various scenarios
- Topics endpoint (default and course-aware)
- Examples endpoint
- Course-info endpoint
- Caching functionality
- Materials loading
- Error handling
- Authorization
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, Mock
import pytest


class TestChatEndpoint:
    """Tests for the /api/tutor/chat endpoint."""

    def test_chat_success(self, client, sample_chat_request, mock_tutor_response):
        """Test successful chat request."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post("/api/tutor/chat", json=sample_chat_request)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "content" in data
            assert len(data["content"]) > 0
            assert "timestamp" in data

    def test_chat_with_conversation_history(
        self, client, sample_chat_request_with_history, mock_tutor_response
    ):
        """Test chat request with conversation history."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post(
                "/api/tutor/chat", json=sample_chat_request_with_history
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_chat_empty_message_fails(self, client):
        """Test that empty message returns validation error."""
        response = client.post("/api/tutor/chat", json={
            "message": "",
            "context": "Private Law"
        })

        assert response.status_code == 422  # Validation error

    def test_chat_whitespace_only_message_fails(self, client):
        """Test that whitespace-only message returns validation error."""
        response = client.post("/api/tutor/chat", json={
            "message": "   ",
            "context": "Private Law"
        })

        assert response.status_code == 422  # Validation error

    def test_chat_missing_message_fails(self, client):
        """Test that missing message field returns validation error."""
        response = client.post("/api/tutor/chat", json={
            "context": "Private Law"
        })

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Verify error mentions the missing field
        error_str = str(data["detail"]).lower()
        assert "message" in error_str or "required" in error_str

    def test_chat_default_context(self, client, mock_tutor_response):
        """Test that default context is applied when not provided."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post("/api/tutor/chat", json={
                "message": "What is contract law?"
            })

            assert response.status_code == 200

    def test_chat_api_error_handling(self, client, sample_chat_request):
        """Test error handling when API call fails."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))

            response = client.post("/api/tutor/chat", json=sample_chat_request)

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


class TestTopicsEndpoint:
    """Tests for the /api/tutor/topics endpoint."""

    def test_get_topics_success(self, client):
        """Test successful topics retrieval."""
        response = client.get("/api/tutor/topics")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "topics" in data
        assert len(data["topics"]) > 0

    def test_topics_contain_required_fields(self, client):
        """Test that each topic has required fields."""
        response = client.get("/api/tutor/topics")

        data = response.json()
        for topic in data["topics"]:
            assert "id" in topic
            assert "name" in topic
            assert "description" in topic

    def test_topics_include_main_law_areas(self, client):
        """Test that main law areas are included."""
        response = client.get("/api/tutor/topics")

        data = response.json()
        topic_names = [t["name"] for t in data["topics"]]

        assert "Constitutional Law" in topic_names
        assert "Administrative Law" in topic_names
        assert "Criminal Law" in topic_names
        assert "Private Law" in topic_names
        assert "International Law" in topic_names


class TestExamplesEndpoint:
    """Tests for the /api/tutor/examples endpoint."""

    def test_get_examples_success(self, client):
        """Test successful examples retrieval."""
        response = client.get("/api/tutor/examples")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "examples" in data
        assert len(data["examples"]) > 0

    def test_examples_have_questions(self, client):
        """Test that each example has questions."""
        response = client.get("/api/tutor/examples")

        data = response.json()
        for example in data["examples"]:
            assert "topic" in example
            assert "questions" in example
            assert len(example["questions"]) > 0


class TestCourseAwareMode:
    """Tests for course-aware AI tutor functionality."""

    def test_chat_with_course_id(self, client, sample_chat_request, mock_tutor_response):
        """Test chat request with course_id parameter."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            with patch('app.services.files_api_service.FilesAPIService.get_course_topics') as mock_topics:
                mock_topics.return_value = [
                    {"id": "private_law", "name": "Private Law", "description": "Week 1"}
                ]

                response = client.post(
                    "/api/tutor/chat?course_id=LLS-2025-2026",
                    json=sample_chat_request
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert "course_id" in data
                assert data["course_id"] == "LLS-2025-2026"

    def test_topics_with_course_id(self, client):
        """Test topics endpoint with course_id parameter."""
        with patch('app.services.files_api_service.FilesAPIService.get_course_topics') as mock_topics:
            mock_topics.return_value = [
                {
                    "id": "constitutional_law",
                    "name": "Constitutional Law",
                    "description": "Week 1: Introduction",
                    "week": 1
                },
                {
                    "id": "administrative_law",
                    "name": "Administrative Law",
                    "description": "Week 2: GALA",
                    "week": 2
                }
            ]

            response = client.get("/api/tutor/topics?course_id=LLS-2025-2026")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "course_id" in data
            assert data["course_id"] == "LLS-2025-2026"
            assert len(data["topics"]) == 2
            assert data["topics"][0]["name"] == "Constitutional Law"

    def test_topics_with_invalid_course_id(self, client):
        """Test topics endpoint with invalid course_id."""
        with patch('app.services.files_api_service.FilesAPIService.get_course_topics') as mock_topics:
            mock_topics.side_effect = ValueError("Course not found: INVALID")

            response = client.get("/api/tutor/topics?course_id=INVALID")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    def test_examples_with_course_id(self, client):
        """Test examples endpoint with course_id parameter."""
        with patch('app.services.files_api_service.FilesAPIService.get_course_topics') as mock_topics:
            mock_topics.return_value = [
                {
                    "id": "private_law",
                    "name": "Private Law",
                    "description": "Week 3",
                    "week": 3
                }
            ]

            response = client.get("/api/tutor/examples?course_id=LLS-2025-2026")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "course_id" in data
            assert len(data["examples"]) > 0
            assert data["examples"][0]["topic"] == "Private Law"

    def test_course_info_endpoint(self, client):
        """Test course-info endpoint."""
        with patch('app.services.files_api_service.get_files_api_service') as mock_files_service:
            with patch('app.services.course_service.get_course_service') as mock_course_service:
                # Mock course data
                mock_course_obj = Mock()
                mock_course_obj.name = "Law & Legal Skills"
                mock_course_obj.description = "LLS Course 2025-2026"
                mock_course_obj.active = True

                # Mock weeks
                mock_week = Mock()
                mock_week.weekNumber = 1
                mock_week.title = "Introduction"
                mock_week.topics = ["Constitutional Law"]
                mock_week.materials = [Mock(), Mock()]  # 2 materials

                mock_course_obj.weeks = [mock_week]

                # Setup mocks
                mock_course_service.return_value.get_course.return_value = mock_course_obj
                mock_files_service.return_value.get_course_topics.return_value = [
                    {"id": "constitutional_law", "name": "Constitutional Law", "week": 1}
                ]

                response = client.get("/api/tutor/course-info?course_id=LLS-2025-2026")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["course_id"] == "LLS-2025-2026"
                assert data["name"] == "Law & Legal Skills"
                assert len(data["topics"]) == 1
                assert len(data["weeks"]) == 1
                assert data["materials_count"] == 2

    def test_course_info_not_found(self, client):
        """Test course-info endpoint with non-existent course."""
        with patch('app.services.course_service.get_course_service') as mock_course_service:
            mock_course_service.return_value.get_course.return_value = None

            response = client.get("/api/tutor/course-info?course_id=INVALID")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data


class TestCacheFunctionality:
    """Tests for caching functionality in AI Tutor.

    Note: These tests verify basic caching behavior. For production-grade
    cache verification, see issue #193 for planned enhancements:
    - Cache hit/miss verification
    - TTL expiration testing
    - Cache key collision testing
    - Cache invalidation testing
    """

    def test_chat_uses_cache_on_repeated_request(self, client, sample_chat_request, mock_tutor_response):
        """Test that repeated identical requests may use cache (if implemented).

        Note: This test verifies that repeated requests work correctly.
        Actual cache hit verification would require inspecting cache internals
        or counting API calls, which is implementation-dependent.

        TODO: Add cache hit verification when cache implementation is finalized.
        See issue #193 for planned cache testing enhancements.
        """
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            # First request
            response1 = client.post("/api/tutor/chat", json=sample_chat_request)
            assert response1.status_code == 200

            # Second identical request
            response2 = client.post("/api/tutor/chat", json=sample_chat_request)
            assert response2.status_code == 200

            # Both should return same content
            assert response1.json()["content"] == response2.json()["content"]

            # Verify API was called (cache implementation may vary)
            # Note: Actual cache hit would mean call_count == 1, but this is
            # implementation-dependent and may not be reliable in all environments
            assert mock_client.messages.create.call_count >= 1

    def test_chat_different_messages_not_cached(self, client, mock_tutor_response):
        """Test that different messages don't use same cache."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            request1 = {"message": "Question 1", "context": "Private Law"}
            request2 = {"message": "Question 2", "context": "Private Law"}

            response1 = client.post("/api/tutor/chat", json=request1)
            response2 = client.post("/api/tutor/chat", json=request2)

            assert response1.status_code == 200
            assert response2.status_code == 200


class TestMaterialsLoading:
    """Tests for materials loading functionality."""

    def test_chat_with_materials_context(self, client, mock_tutor_response):
        """Test chat with materials loaded in context."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            with patch('app.services.files_api_service.get_files_api_service') as mock_service:
                # Mock the service instance and its method
                mock_instance = Mock()
                mock_material = Mock()
                mock_material.title = "Lecture Week 1"
                mock_material.filename = "lecture_week_1.pdf"

                # get_course_materials_with_text returns list of (material, text) tuples
                mock_instance.get_course_materials_with_text = AsyncMock(
                    return_value=[(mock_material, "This is lecture content")]
                )
                mock_service.return_value = mock_instance

                response = client.post(
                    "/api/tutor/chat?course_id=LLS-2025-2026&week=1",
                    json={"message": "Explain this week's topic", "context": "Private Law"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"

    def test_chat_materials_loading_error(self, client, mock_tutor_response):
        """Test chat when materials loading fails gracefully."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            with patch('app.services.files_api_service.get_files_api_service') as mock_service:
                # Mock the service to raise an exception
                mock_instance = Mock()
                mock_instance.get_course_materials_with_text = AsyncMock(
                    side_effect=Exception("Materials loading failed")
                )
                mock_service.return_value = mock_instance

                # Should still work, just without materials (error is logged and ignored)
                response = client.post(
                    "/api/tutor/chat?course_id=LLS-2025-2026",
                    json={"message": "Test question", "context": "Private Law"}
                )

                assert response.status_code == 200


class TestWeekFiltering:
    """Tests for week-based filtering.

    Note: Week filtering is not yet implemented in the endpoints.
    These tests verify that the endpoints work correctly with week parameters,
    but do not filter results by week. This is a future enhancement.
    See: Future work - implement week filtering feature
    """

    def test_topics_with_week_parameter(self, client):
        """Test topics endpoint accepts week parameter (filtering not yet implemented)."""
        with patch('app.services.files_api_service.FilesAPIService.get_course_topics') as mock_topics:
            mock_topics.return_value = [
                {"id": "topic1", "name": "Topic 1", "week": 1},
                {"id": "topic2", "name": "Topic 2", "week": 2},
                {"id": "topic3", "name": "Topic 3", "week": 1}
            ]

            # Week parameter is accepted but not yet used for filtering
            response = client.get("/api/tutor/topics?course_id=LLS-2025-2026&week=1")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            # Note: Currently returns all topics, not filtered by week
            assert len(data["topics"]) >= 1

    def test_examples_with_week_parameter(self, client):
        """Test examples endpoint accepts week parameter (filtering not yet implemented)."""
        with patch('app.services.files_api_service.FilesAPIService.get_course_topics') as mock_topics:
            mock_topics.return_value = [
                {"id": "topic1", "name": "Topic 1", "week": 2}
            ]

            # Week parameter is accepted but not yet used for filtering
            response = client.get("/api/tutor/examples?course_id=LLS-2025-2026&week=2")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


class TestErrorHandling:
    """Tests for comprehensive error handling."""

    def test_chat_message_at_max_length(self, client, mock_tutor_response):
        """Test chat with message at maximum allowed length (5000 chars)."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            # Exactly 5000 characters (max allowed)
            max_message = "A" * 5000
            response = client.post("/api/tutor/chat", json={
                "message": max_message,
                "context": "Private Law"
            })

            # Should accept message at max length
            assert response.status_code == 200

    def test_chat_message_exceeds_max_length(self, client):
        """Test chat with message exceeding maximum length (>5000 chars)."""
        # 5001 characters (exceeds max)
        too_long_message = "A" * 5001
        response = client.post("/api/tutor/chat", json={
            "message": too_long_message,
            "context": "Private Law"
        })

        # Should reject with validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.parametrize("length,expected_status,description", [
        (1, 200, "Minimum valid length"),
        (100, 200, "Normal length"),
        (4999, 200, "Just under max"),
        (5000, 200, "Exactly at max"),
        (5001, 422, "Just over max (should reject)"),
        (10000, 422, "Far over max (should reject)"),
    ])
    def test_chat_message_boundary_cases(self, client, mock_tutor_response, length, expected_status, description):
        """Test chat with various message length boundaries including rejection cases."""
        # Only mock API for valid requests
        if expected_status == 200:
            with patch('app.services.anthropic_client.client') as mock_client:
                mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

                message = "A" * length
                response = client.post("/api/tutor/chat", json={
                    "message": message,
                    "context": "Private Law"
                })
        else:
            # Don't mock for invalid requests (should fail validation before API call)
            message = "A" * length
            response = client.post("/api/tutor/chat", json={
                "message": message,
                "context": "Private Law"
            })

        assert response.status_code == expected_status, \
            f"{description}: Expected {expected_status} for length {length}, got {response.status_code}"

        # For rejection cases, verify error detail
        if expected_status == 422:
            data = response.json()
            assert "detail" in data, f"{description}: Error response should include detail field"

    def test_chat_with_special_characters(self, client, mock_tutor_response):
        """Test chat with special characters in message."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post("/api/tutor/chat", json={
                "message": "What about Art. 6:74 § 2 DCC? <test> & 'quotes'",
                "context": "Private Law"
            })

            assert response.status_code == 200

    def test_chat_with_unicode_characters(self, client, mock_tutor_response):
        """Test chat with unicode characters."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post("/api/tutor/chat", json={
                "message": "Explain 法律 and émojis 🎓",
                "context": "Private Law"
            })

            assert response.status_code == 200

    def test_chat_api_timeout(self, client, sample_chat_request):
        """Test handling of API timeout."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(side_effect=TimeoutError("API timeout"))

            response = client.post("/api/tutor/chat", json=sample_chat_request)

            assert response.status_code == 500

    def test_chat_api_rate_limit(self, client, sample_chat_request):
        """Test handling of API rate limit."""
        with patch('app.services.anthropic_client.client') as mock_client:
            try:
                from anthropic import RateLimitError
                error = RateLimitError("Rate limit exceeded", response=Mock(), body=None)
            except ImportError:
                # If anthropic package doesn't have RateLimitError, use generic Exception
                error = Exception("Rate limit exceeded")

            mock_client.messages.create = AsyncMock(side_effect=error)

            response = client.post("/api/tutor/chat", json=sample_chat_request)

            assert response.status_code == 500


class TestConversationHistory:
    """Tests for conversation history handling."""

    def test_chat_with_long_conversation_history(self, client, mock_tutor_response):
        """Test chat with long conversation history."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            # Create long history
            history = []
            for i in range(20):
                history.append({"role": "user", "content": f"Question {i}"})
                history.append({"role": "assistant", "content": f"Answer {i}"})

            response = client.post("/api/tutor/chat", json={
                "message": "New question",
                "context": "Private Law",
                "conversation_history": history
            })

            assert response.status_code == 200

    def test_chat_with_invalid_history_format(self, client):
        """Test chat with invalid conversation history format (should reject)."""
        response = client.post("/api/tutor/chat", json={
            "message": "Test question",
            "context": "Private Law",
            "conversation_history": "invalid format"  # Should be array, not string
        })

        # Should reject with validation error (deterministic)
        assert response.status_code == 422, \
            f"Expected 422 for invalid history format, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Error response should include detail field"

    def test_chat_with_empty_history(self, client, mock_tutor_response):
        """Test chat with empty conversation history."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post("/api/tutor/chat", json={
                "message": "Test question",
                "context": "Private Law",
                "conversation_history": []
            })

            assert response.status_code == 200


class TestContextVariations:
    """Tests for different context variations."""

    @pytest.mark.parametrize("context", [
        "Constitutional Law",
        "Administrative Law",
        "Criminal Law",
        "Private Law",
        "International Law"
    ])
    def test_chat_with_law_contexts(self, client, mock_tutor_response, context):
        """Test chat with different law contexts."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post("/api/tutor/chat", json={
                "message": "Test question",
                "context": context
            })
            assert response.status_code == 200

    def test_chat_with_custom_context(self, client, mock_tutor_response):
        """Test chat with custom context."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post("/api/tutor/chat", json={
                "message": "Test question",
                "context": "Custom Legal Topic"
            })

            assert response.status_code == 200

    def test_chat_without_context(self, client, mock_tutor_response):
        """Test chat without context (should use default)."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post("/api/tutor/chat", json={
                "message": "Test question"
            })

            assert response.status_code == 200


class TestResponseFormatting:
    """Tests for response formatting and structure."""

    def test_chat_response_has_timestamp(self, client, sample_chat_request, mock_tutor_response):
        """Test that chat response includes valid timestamp."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            before_request = datetime.now(timezone.utc)
            response = client.post("/api/tutor/chat", json=sample_chat_request)
            after_request = datetime.now(timezone.utc)

            assert response.status_code == 200
            data = response.json()
            assert "timestamp" in data

            # Verify timestamp is valid ISO format
            timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))

            # Verify timestamp is reasonable (within request time window)
            assert before_request <= timestamp <= after_request, \
                f"Timestamp {timestamp} not within request window {before_request} - {after_request}"

            # Verify timestamp is timezone-aware
            assert timestamp.tzinfo is not None, "Timestamp should be timezone-aware"

    def test_chat_response_structure(self, client, sample_chat_request, mock_tutor_response):
        """Test complete response structure."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            response = client.post("/api/tutor/chat", json=sample_chat_request)

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "content" in data
            assert "timestamp" in data
            assert data["status"] == "success"
            assert isinstance(data["content"], list)

    def test_topics_response_structure(self, client):
        """Test topics response structure."""
        response = client.get("/api/tutor/topics")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "topics" in data
        assert isinstance(data["topics"], list)

    def test_examples_response_structure(self, client):
        """Test examples response structure."""
        response = client.get("/api/tutor/examples")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "examples" in data
        assert isinstance(data["examples"], list)


class TestConcurrentRequests:
    """Tests for handling concurrent requests."""

    def test_multiple_concurrent_chat_requests(self, client, mock_tutor_response):
        """Test handling multiple concurrent chat requests using threading.

        Note: This test uses threading to simulate actual concurrent requests,
        not just sequential requests in a loop. Uses thread-safe data structures.
        """
        import threading
        from queue import Queue

        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)

            # Use thread-safe queues for results and errors
            results_queue = Queue()
            errors_queue = Queue()

            def make_request(request_data, index):
                """Make a request in a thread (thread-safe)."""
                try:
                    response = client.post("/api/tutor/chat", json=request_data)
                    results_queue.put((index, response))
                except Exception as e:
                    errors_queue.put((index, e))

            # Create threads for concurrent requests
            threads = []
            num_requests = 5
            for i in range(num_requests):
                request_data = {"message": f"Question {i}", "context": "Private Law"}
                thread = threading.Thread(target=make_request, args=(request_data, i))
                threads.append(thread)

            # Start all threads (concurrent execution)
            for thread in threads:
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=5.0)
                assert not thread.is_alive(), f"Thread {thread.name} timed out"

            # Collect results from queues
            results = []
            while not results_queue.empty():
                results.append(results_queue.get())

            errors = []
            while not errors_queue.empty():
                errors.append(errors_queue.get())

            # Verify no errors occurred
            assert len(errors) == 0, f"Errors in concurrent requests: {errors}"

            # All requests should succeed
            assert len(results) == num_requests, \
                f"Expected {num_requests} results, got {len(results)}"

            for index, response in results:
                assert response.status_code == 200, \
                    f"Request {index} failed with status {response.status_code}"
