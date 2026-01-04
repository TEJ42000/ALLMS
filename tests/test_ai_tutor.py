"""Tests for AI Tutor endpoints."""

from unittest.mock import AsyncMock, patch


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
