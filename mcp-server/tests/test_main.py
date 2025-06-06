import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, UTC
import jwt
import os
import asyncio

# Patch environment variables for testing
os.environ["MCP_API_KEY"] = "test_api_key"
os.environ["JWT_SECRET_KEY"] = "test_secret_key"

# Import after environment variables are set
from main import mcp, _process_context_request, health_check_direct
from models import (
    ContextItem, 
    ContextSource, 
    ResponseMetadata, 
    RetrievalMetadata,
    UserInfo,
)
from context_service import ContextResult, DocumentResult

@pytest.fixture
def test_context_result():
    """Create a sample context result for testing."""
    return ContextResult(
        documents=[
            DocumentResult(
                content="Q1 goals include increasing revenue by 15%",
                source="google_drive",
                metadata={
                    "id": "doc123",
                    "url": "https://example.com/doc1",
                    "file_name": "q1_goals.txt",
                    "created_time": "2025-01-01T00:00:00Z",
                    "modified_time": "2025-01-02T00:00:00Z",
                    "score": 0.95,
                    "source_type": "document"
                }
            ),
            DocumentResult(
                content="Team objectives for the quarter",
                source="slack",
                metadata={
                    "id": "doc456",
                    "url": "https://example.com/doc2",
                    "file_name": "team_objectives.txt",
                    "created_time": "2025-01-03T00:00:00Z",
                    "modified_time": "2025-01-04T00:00:00Z", 
                    "score": 0.85,
                    "source_type": "document"
                }
            )
        ],
        retrieval_time_ms=150,
        cache_hit=False
    )

class TestMCP:
    """Tests for the FastMCP implementation."""
    
    def test_health_check(self):
        """Test the health check tool."""
        # Call the actual function (not the FastMCP tool wrapper)
        response = health_check_direct()
        
        # Verify the response
        assert response == {"status": "healthy"}
    
    @pytest.mark.asyncio
    async def test_process_context_with_openwebui_token(self, test_context_result):
        """Test processing context with an OpenWebUI token."""
        # Create a mock context service that returns our test result
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context:
            # Set up the get_context_for_prompt method
            mock_get_context.return_value = test_context_result
            
            # Create a sample OpenWebUI token
            token_payload = {
                "sub": "user123",
                "email": "tmfrisinger@gmail.com",
                "name": "Test User",
                "exp": datetime.now(UTC).timestamp() + 3600  # 1 hour expiration
            }
            token = jwt.encode(token_payload, "not_verified", algorithm="HS256")
            
            # Call the process context function directly
            result = await _process_context_request(
                auth_token=token,
                token_type="OpenWebUI",
                prompt="What are our Q1 goals?",
                history_summary="Previous conversation about company plans."
            )
            
            # Validate result structure
            assert "context_items" in result
            assert len(result["context_items"]) == 2
            
            # Check the first context item
            context_item = result["context_items"][0]
            assert context_item["role"] == "system"
            assert "Q1 goals include increasing revenue by 15%" in context_item["content"]
            assert context_item["metadata"]["source"] == "google_drive"
            
            # Check metadata
            assert "metadata" in result
            metadata = result["metadata"]
            assert metadata["token_type"] == "OpenWebUI"
            assert "user" in metadata
            assert metadata["user"]["id"] == "user123"
            assert metadata["user"]["email"] == "tmfrisinger@gmail.com"
    
    @pytest.mark.asyncio
    async def test_process_context_with_slack_token(self, test_context_result):
        """Test processing context with a Slack token."""
        # Create a mock context service that returns our test result
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context:
            # Set up the get_context_for_prompt method
            mock_get_context.return_value = test_context_result
            
            # Create a sample Slack token
            token = "slack:U123456"
            
            # Call the process context function directly
            result = await _process_context_request(
                auth_token=token,
                token_type="Slack",
                prompt="What are our Q1 goals?",
                history_summary="Previous conversation about company plans."
            )
            
            # Validate result structure
            assert "context_items" in result
            assert len(result["context_items"]) == 2
            
            # Check metadata
            assert "metadata" in result
            metadata = result["metadata"]
            assert metadata["token_type"] == "Slack"
            assert "user" in metadata
            assert metadata["user"]["id"] == "U123456"
    
    @pytest.mark.asyncio
    async def test_process_context_invalid_token(self):
        """Test processing context with an invalid auth token."""
        # Test with an invalid token
        with pytest.raises(ValueError, match="Invalid token:"):
            await _process_context_request(
                auth_token="invalid_token",
                token_type="OpenWebUI",
                prompt="What are our Q1 goals?",
                history_summary="Previous conversation about company plans."
            )

if __name__ == "__main__":
    pytest.main(["-v"])
