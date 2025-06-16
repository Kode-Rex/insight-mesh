import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, UTC
import jwt
import os
import asyncio
from fastapi import HTTPException

# Patch environment variables for testing
os.environ["MCP_API_KEY"] = "test_api_key"
os.environ["JWT_SECRET_KEY"] = "test_secret_key"
os.environ["DB_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
os.environ["SLACK_DB_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_slack_db"

# Import after environment variables are set
from main import (
    mcp, _process_context_request, health_check_direct,
    verify_api_key, parse_auth_token, extract_user_info_from_token
)
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
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context, \
             patch("main.get_slack_user_by_id", new_callable=AsyncMock) as mock_get_slack_user:
            # Set up the get_context_for_prompt method
            mock_get_context.return_value = test_context_result
            
            # Mock the Slack user lookup to return None (user not found)
            mock_get_slack_user.return_value = None
            
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
    
    @pytest.mark.asyncio
    async def test_process_context_empty_prompt(self, test_context_result):
        """Test processing context with empty prompt."""
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = test_context_result
            
            token_payload = {
                "sub": "user123",
                "email": "test@example.com",
                "name": "Test User",
                "exp": datetime.now(UTC).timestamp() + 3600
            }
            token = jwt.encode(token_payload, "not_verified", algorithm="HS256")
            
            result = await _process_context_request(
                auth_token=token,
                token_type="OpenWebUI",
                prompt="",
                history_summary="Previous conversation."
            )
            
            assert "context_items" in result
            assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_process_context_no_history(self, test_context_result):
        """Test processing context without history summary."""
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = test_context_result
            
            token_payload = {
                "sub": "user123",
                "email": "test@example.com",
                "name": "Test User",
                "exp": datetime.now(UTC).timestamp() + 3600
            }
            token = jwt.encode(token_payload, "not_verified", algorithm="HS256")
            
            result = await _process_context_request(
                auth_token=token,
                token_type="OpenWebUI",
                prompt="What are our goals?",
                history_summary=""
            )
            
            assert "context_items" in result
            assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_process_context_service_error(self):
        """Test processing context when context service raises error."""
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context:
            mock_get_context.side_effect = Exception("Context service error")
            
            token_payload = {
                "sub": "user123",
                "email": "test@example.com",
                "name": "Test User",
                "exp": datetime.now(UTC).timestamp() + 3600
            }
            token = jwt.encode(token_payload, "not_verified", algorithm="HS256")
            
            with pytest.raises(Exception, match="Context service error"):
                await _process_context_request(
                    auth_token=token,
                    token_type="OpenWebUI",
                    prompt="What are our goals?",
                    history_summary="Previous conversation."
                )


class TestAuthentication:
    """Tests for authentication functions."""
    
    def test_verify_api_key_valid(self):
        """Test API key verification with valid key."""
        result = verify_api_key("test_api_key")
        assert result is True
    
    def test_verify_api_key_invalid(self):
        """Test API key verification with invalid key."""
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key("invalid_key")
        assert exc_info.value.status_code == 401
    
    def test_verify_api_key_none(self):
        """Test API key verification with None."""
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(None)
        assert exc_info.value.status_code == 401
    
    def test_parse_auth_token_openwebui(self):
        """Test parsing OpenWebUI auth token."""
        token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        result = parse_auth_token(token)
        assert result == ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test", "OpenWebUI")
    
    def test_parse_auth_token_slack(self):
        """Test parsing Slack auth token."""
        token = "slack:U123456"
        result = parse_auth_token(token)
        assert result == ("slack:U123456", "Slack")
    
    def test_parse_auth_token_invalid(self):
        """Test parsing invalid auth token."""
        with pytest.raises(ValueError, match="Invalid token format"):
            parse_auth_token("invalid_token")
    
    def test_parse_auth_token_none(self):
        """Test parsing None auth token."""
        with pytest.raises(ValueError, match="Token is required"):
            parse_auth_token(None)
    
    def test_parse_auth_token_empty(self):
        """Test parsing empty auth token."""
        with pytest.raises(ValueError, match="Token is required"):
            parse_auth_token("")
    
    def test_extract_user_info_openwebui_valid(self):
        """Test extracting user info from valid OpenWebUI token."""
        token_payload = {
            "sub": "user123",
            "email": "test@example.com",
            "name": "Test User",
            "exp": datetime.now(UTC).timestamp() + 3600
        }
        token = jwt.encode(token_payload, "not_verified", algorithm="HS256")
        
        result = extract_user_info_from_token(token, "OpenWebUI")
        
        assert result.id == "user123"
        assert result.email == "test@example.com"
        assert result.name == "Test User"
    
    def test_extract_user_info_openwebui_expired(self):
        """Test extracting user info from expired OpenWebUI token."""
        token_payload = {
            "sub": "user123",
            "email": "test@example.com",
            "name": "Test User",
            "exp": datetime.now(UTC).timestamp() - 3600  # Expired 1 hour ago
        }
        token = jwt.encode(token_payload, "not_verified", algorithm="HS256")
        
        with pytest.raises(ValueError, match="Token expired"):
            extract_user_info_from_token(token, "OpenWebUI")
    
    def test_extract_user_info_openwebui_invalid(self):
        """Test extracting user info from invalid OpenWebUI token."""
        with pytest.raises(ValueError, match="Invalid token"):
            extract_user_info_from_token("invalid.jwt.token", "OpenWebUI")
    
    def test_extract_user_info_slack_valid(self):
        """Test extracting user info from valid Slack token."""
        result = extract_user_info_from_token("slack:U123456", "Slack")
        
        assert result.id == "U123456"
        assert result.email is None
        assert result.name is None
    
    def test_extract_user_info_slack_invalid(self):
        """Test extracting user info from invalid Slack token."""
        with pytest.raises(ValueError, match="Invalid Slack token format"):
            extract_user_info_from_token("slack:invalid", "Slack")
    
    def test_extract_user_info_slack_missing_prefix(self):
        """Test extracting user info from Slack token without prefix."""
        with pytest.raises(ValueError, match="Invalid Slack token format"):
            extract_user_info_from_token("U123456", "Slack")
    
    def test_extract_user_info_unknown_type(self):
        """Test extracting user info from unknown token type."""
        with pytest.raises(ValueError, match="Unsupported token type"):
            extract_user_info_from_token("some_token", "Unknown")


class TestMCPTools:
    """Tests for MCP tool functionality."""
    
    @pytest.mark.asyncio
    async def test_mcp_tool_registration(self):
        """Test that MCP tools are properly registered."""
        # Get the tools from the MCP server
        tools = mcp.list_tools()
        
        # Check that required tools are registered
        tool_names = [tool.name for tool in tools]
        assert "health_check" in tool_names
        assert "get_context" in tool_names
    
    def test_health_check_tool_metadata(self):
        """Test health check tool metadata."""
        tools = mcp.list_tools()
        health_tool = next((tool for tool in tools if tool.name == "health_check"), None)
        
        assert health_tool is not None
        assert health_tool.description == "Check if the MCP server is running"
    
    def test_get_context_tool_metadata(self):
        """Test get context tool metadata."""
        tools = mcp.list_tools()
        context_tool = next((tool for tool in tools if tool.name == "get_context"), None)
        
        assert context_tool is not None
        assert "retrieve relevant context" in context_tool.description.lower()


class TestErrorHandling:
    """Tests for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_process_context_with_slack_user_lookup_error(self, test_context_result):
        """Test context processing when Slack user lookup fails."""
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context, \
             patch("main.get_slack_user_by_id", new_callable=AsyncMock) as mock_get_slack_user:
            
            mock_get_context.return_value = test_context_result
            mock_get_slack_user.side_effect = Exception("Database error")
            
            # Should still work despite user lookup error
            result = await _process_context_request(
                auth_token="slack:U123456",
                token_type="Slack",
                prompt="What are our goals?",
                history_summary="Previous conversation."
            )
            
            assert "context_items" in result
            assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_process_context_empty_results(self):
        """Test context processing with empty results."""
        empty_result = ContextResult(
            documents=[],
            retrieval_time_ms=50,
            cache_hit=False
        )
        
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = empty_result
            
            token_payload = {
                "sub": "user123",
                "email": "test@example.com",
                "name": "Test User",
                "exp": datetime.now(UTC).timestamp() + 3600
            }
            token = jwt.encode(token_payload, "not_verified", algorithm="HS256")
            
            result = await _process_context_request(
                auth_token=token,
                token_type="OpenWebUI",
                prompt="What are our goals?",
                history_summary="Previous conversation."
            )
            
            assert "context_items" in result
            assert len(result["context_items"]) == 0
            assert "metadata" in result


class TestDataValidation:
    """Tests for data validation and edge cases."""
    
    @pytest.mark.asyncio
    async def test_process_context_very_long_prompt(self, test_context_result):
        """Test context processing with very long prompt."""
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = test_context_result
            
            token_payload = {
                "sub": "user123",
                "email": "test@example.com",
                "name": "Test User",
                "exp": datetime.now(UTC).timestamp() + 3600
            }
            token = jwt.encode(token_payload, "not_verified", algorithm="HS256")
            
            long_prompt = "What are our goals? " * 1000  # Very long prompt
            
            result = await _process_context_request(
                auth_token=token,
                token_type="OpenWebUI",
                prompt=long_prompt,
                history_summary="Previous conversation."
            )
            
            assert "context_items" in result
            assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_process_context_special_characters(self, test_context_result):
        """Test context processing with special characters in prompt."""
        with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = test_context_result
            
            token_payload = {
                "sub": "user123",
                "email": "test@example.com",
                "name": "Test User",
                "exp": datetime.now(UTC).timestamp() + 3600
            }
            token = jwt.encode(token_payload, "not_verified", algorithm="HS256")
            
            special_prompt = "What are our goals? 🚀 Here's some émojis & spéciål chars: @#$%^&*()"
            
            result = await _process_context_request(
                auth_token=token,
                token_type="OpenWebUI",
                prompt=special_prompt,
                history_summary="Previous conversation."
            )
            
            assert "context_items" in result
            assert "metadata" in result

if __name__ == "__main__":
    pytest.main(["-v"])
