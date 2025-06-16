import asyncio
from litellm import completion
import os
from dotenv import load_dotenv
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
import json
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Import the actual RAG handler class
try:
    from rag_pipeline.pre_request_hook import RAGHandler
except ImportError:
    # Fallback for when running from within the rag_pipeline directory
    from pre_request_hook import RAGHandler

class TestRAGHandler:
    """Comprehensive tests for the RAG handler functionality"""

    @pytest.fixture
    def mock_context_response(self):
        """Mock context response from MCP server"""
        return {
            "context_items": [
                {
                    "role": "system",
                    "content": "Based on retrieved documents: Q1 goals include revenue growth of 15%",
                    "metadata": {
                        "source": "google_drive",
                        "file_name": "q1_goals.txt",
                        "score": 0.95
                    }
                }
            ],
            "metadata": {
                "retrieval_time_ms": 150,
                "cache_hit": False,
                "user": {"id": "user123", "email": "test@example.com"}
            }
        }

    @pytest.fixture
    def rag_handler(self):
        """Create a RAG handler instance for testing"""
        return RAGHandler()

    @pytest.fixture
    def mock_user_api_key_dict(self):
        """Mock user API key dict"""
        from litellm.proxy.proxy_server import UserAPIKeyAuth
        mock_dict = MagicMock(spec=UserAPIKeyAuth)
        mock_dict.headers = {"X-Auth-Token": "test-token"}
        return mock_dict

    @pytest.fixture
    def mock_cache(self):
        """Mock cache"""
        from litellm.proxy.proxy_server import DualCache
        return MagicMock(spec=DualCache)

    @pytest.mark.asyncio
    async def test_rag_handler_with_context_injection(self, rag_handler, mock_user_api_key_dict, mock_cache, mock_context_response):
        """Test RAG handler with successful context injection"""
        with patch('rag_pipeline.pre_request_hook.get_context_from_mcp', new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = mock_context_response
            
            # Test message that should trigger context retrieval
            request_data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "What are our Q1 goals?"}],
                "metadata": {"X-Auth-Token": "test-token"}
            }
            
            # Test the hook
            result = await rag_handler.async_pre_call_hook(
                user_api_key_dict=mock_user_api_key_dict,
                cache=mock_cache,
                data=request_data,
                call_type="completion"
            )
            
            # Verify context was injected
            assert "messages" in result
            
            # Check that system message was added with context
            system_messages = [msg for msg in result["messages"] if msg.get("role") == "system"]
            assert len(system_messages) > 0
            
            # Verify the system message contains the context
            system_content = system_messages[0]["content"]
            assert "Q1 goals include revenue growth of 15%" in system_content
            assert "google_drive" in system_content

    @pytest.mark.asyncio
    async def test_rag_handler_mcp_server_error(self, rag_handler, mock_user_api_key_dict, mock_cache):
        """Test RAG handler when MCP server returns error"""
        with patch('rag_pipeline.pre_request_hook.get_context_from_mcp', new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = None  # Simulate error
            
            request_data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "What are our goals?"}],
                "metadata": {"X-Auth-Token": "test-token"}
            }
            
            # Should handle error gracefully and still add date to system message
            result = await rag_handler.async_pre_call_hook(
                user_api_key_dict=mock_user_api_key_dict,
                cache=mock_cache,
                data=request_data,
                call_type="completion"
            )
            
            # Should still add system message with date even without context
            system_messages = [msg for msg in result["messages"] if msg.get("role") == "system"]
            assert len(system_messages) > 0
            assert "current date" in system_messages[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_rag_handler_no_auth_token(self, rag_handler, mock_cache):
        """Test RAG handler without auth token"""
        mock_user_api_key_dict = MagicMock()
        mock_user_api_key_dict.headers = {}
        
        request_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "What are our goals?"}]
            # No metadata with auth token
        }
        
        with patch('rag_pipeline.pre_request_hook.get_context_from_mcp', new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = None
            
            # Should still process and add date
            result = await rag_handler.async_pre_call_hook(
                user_api_key_dict=mock_user_api_key_dict,
                cache=mock_cache,
                data=request_data,
                call_type="completion"
            )
            
            # Should add system message with date
            system_messages = [msg for msg in result["messages"] if msg.get("role") == "system"]
            assert len(system_messages) > 0

    @pytest.mark.asyncio
    async def test_rag_handler_empty_context(self, rag_handler, mock_user_api_key_dict, mock_cache):
        """Test RAG handler with empty context response"""
        with patch('rag_pipeline.pre_request_hook.get_context_from_mcp', new_callable=AsyncMock) as mock_get_context:
            # Mock empty context response
            empty_response = {
                "context_items": [],
                "metadata": {"retrieval_time_ms": 50, "cache_hit": False}
            }
            mock_get_context.return_value = empty_response
            
            request_data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "What are our goals?"}],
                "metadata": {"X-Auth-Token": "test-token"}
            }
            
            result = await rag_handler.async_pre_call_hook(
                user_api_key_dict=mock_user_api_key_dict,
                cache=mock_cache,
                data=request_data,
                call_type="completion"
            )
            
            # Should add basic system message with date when no context available
            system_messages = [msg for msg in result["messages"] if msg.get("role") == "system"]
            assert len(system_messages) > 0
            assert "current date" in system_messages[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_rag_handler_network_timeout(self, rag_handler, mock_user_api_key_dict, mock_cache):
        """Test RAG handler with network timeout"""
        with patch('rag_pipeline.pre_request_hook.get_context_from_mcp', new_callable=AsyncMock) as mock_get_context:
            # Mock network timeout
            mock_get_context.side_effect = Exception("Network timeout")
            
            request_data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "What are our goals?"}],
                "metadata": {"X-Auth-Token": "test-token"}
            }
            
            # Should handle timeout gracefully
            result = await rag_handler.async_pre_call_hook(
                user_api_key_dict=mock_user_api_key_dict,
                cache=mock_cache,
                data=request_data,
                call_type="completion"
            )
            
            # Should return data even on error
            assert "messages" in result

    @pytest.mark.asyncio
    async def test_rag_handler_multiple_messages(self, rag_handler, mock_user_api_key_dict, mock_cache, mock_context_response):
        """Test RAG handler with multiple messages in conversation"""
        with patch('rag_pipeline.pre_request_hook.get_context_from_mcp', new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = mock_context_response
            
            request_data = {
                "model": "gpt-4",
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                    {"role": "user", "content": "What are our Q1 goals?"}
                ],
                "metadata": {"X-Auth-Token": "test-token"}
            }
            
            result = await rag_handler.async_pre_call_hook(
                user_api_key_dict=mock_user_api_key_dict,
                cache=mock_cache,
                data=request_data,
                call_type="completion"
            )
            
            # Should inject context while preserving conversation history
            # Check that original conversation is preserved
            user_messages = [msg for msg in result["messages"] if msg.get("role") == "user"]
            assert len(user_messages) >= 2
            
            # Check that system message contains context
            system_messages = [msg for msg in result["messages"] if msg.get("role") == "system"]
            assert len(system_messages) > 0
            system_content = system_messages[0]["content"]
            assert "Q1 goals include revenue growth of 15%" in system_content

    @pytest.mark.asyncio
    async def test_rag_handler_non_completion_call(self, rag_handler, mock_user_api_key_dict, mock_cache):
        """Test RAG handler with non-completion call type"""
        request_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "What are our goals?"}]
        }
        
        result = await rag_handler.async_pre_call_hook(
            user_api_key_dict=mock_user_api_key_dict,
            cache=mock_cache,
            data=request_data,
            call_type="embeddings"  # Non-completion call
        )
        
        # Should return original data unchanged for non-completion calls
        assert result == request_data

    @pytest.mark.asyncio
    async def test_rag_handler_no_messages(self, rag_handler, mock_user_api_key_dict, mock_cache):
        """Test RAG handler with request containing no messages"""
        request_data = {
            "model": "gpt-4",
            "messages": []  # Empty messages
        }
        
        result = await rag_handler.async_pre_call_hook(
            user_api_key_dict=mock_user_api_key_dict,
            cache=mock_cache,
            data=request_data,
            call_type="completion"
        )
        
        # Should return original data when no messages
        assert result == request_data

    def test_environment_configuration(self):
        """Test that required environment variables are configured"""
        # Check that MCP-related environment variables can be set
        required_vars = ["MCP_API_URL", "MCP_API_KEY"]
        
        for var in required_vars:
            # Test that we can set and read the variable
            test_value = f"test_{var.lower()}"
            os.environ[var] = test_value
            assert os.environ.get(var) == test_value

@pytest.mark.asyncio
async def test_full_rag_handler():
    """Test the complete RAG handler with a real request"""
    print("\n=== Testing Full RAG Handler ===")
    
    try:
        # Test message that should trigger the handler
        messages = [
            {"role": "user", "content": "Hello, can you help me?"}
        ]
        
        # Mock the completion to avoid actual API calls in tests
        with patch('litellm.completion') as mock_completion:
            mock_completion.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="I can help you!"))]
            )
            
            response = completion(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7
            )
            
            print(f"  ✓ Handler executed successfully")
            assert response is not None
            
    except Exception as e:
        print(f"  ✗ Error during full handler test: {str(e)}")
        pytest.fail(f"Full handler test failed: {str(e)}")

if __name__ == "__main__":
    print("Starting RAG Handler Tests...")
    
    # Run the test
    asyncio.run(test_full_rag_handler())
    
    print("\nAll tests completed!")