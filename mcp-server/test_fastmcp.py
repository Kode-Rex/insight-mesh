#!/usr/bin/env python3

import json
import aiohttp
import asyncio
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mark as an asyncio test
pytestmark = pytest.mark.asyncio

# Mock FastMCP function for testing
def mock_health_check():
    return {"status": "healthy"}

@pytest.mark.asyncio
async def test_fastmcp_endpoints():
    """Test the FastMCP HTTP endpoints directly using mocks"""
    # Since we can't easily mock FastMCP's internals, we'll directly test 
    # the functions that FastMCP wraps
    from main import health_check_direct

    # 1. Test health_check
    result = health_check_direct()
    assert result == {"status": "healthy"}

@pytest.mark.asyncio
async def test_get_context():
    """Test the get_context function with mocks"""
    # Import models
    from models import UserInfo, ContextResult, DocumentResult
    from main import _process_context_request
    
    # Mock dependencies instead of calling the actual function
    with patch('main.validate_token', new_callable=AsyncMock) as mock_validate, \
         patch('main.context_service.get_context_for_prompt', new_callable=AsyncMock) as mock_get_context:
            
        # Setup mock returns with proper model instances
        mock_validate.return_value = UserInfo(
            id="default_user",
            email="test@example.com",
            name="Test User",
            is_active=True,
            token_type="OpenWebUI"
        )
        
        mock_get_context.return_value = ContextResult(
            documents=[
                DocumentResult(
                    content="Test document content",
                    source="test_source",
                    metadata={
                        "id": "doc123",
                        "url": "https://example.com/doc1",
                        "file_name": "test1.txt",
                        "created_time": "2025-01-01T00:00:00Z",
                        "modified_time": "2025-01-02T00:00:00Z",
                        "score": 0.95,
                        "source_type": "document"
                    }
                )
            ],
            cache_hit=False,
            retrieval_time_ms=42
        )
        
        # Test parameters
        params = {
            "auth_token": "default_token",
            "token_type": "OpenWebUI",
            "prompt": "Test prompt",
            "history_summary": "Test history"
        }
        
        # Call the function directly
        result = await _process_context_request(**params)
        
        # Verify the function called the mocked dependencies
        mock_validate.assert_called_once_with(params["auth_token"], params["token_type"])
        mock_get_context.assert_called_once()
        
        # Verify basic structure of result
        assert "context_items" in result
        assert "metadata" in result
        assert len(result["context_items"]) == 1

# Function to test actual HTTP endpoints when run directly
# Mark as an integration test so it doesn't run by default
@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_fastmcp_endpoints():
    """Test the FastMCP HTTP endpoints with a live server"""
    # Get MCP server port from environment, default to 9091
    mcp_port = os.environ.get("MCP_PORT", "9091")
    mcp_host = os.environ.get("MCP_HOST", "localhost")
    
    base_url = f"http://{mcp_host}:{mcp_port}/mcp"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test health_check endpoint
            print(f"Testing FastMCP health_check endpoint...")
            payload = {
                "jsonrpc": "2.0",
                "method": "health_check",
                "params": {},
                "id": 1
            }
            
            async with session.post(
                f"{base_url}/v1/json-rpc",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"Health check successful: {result}")
                else:
                    error_text = await response.text()
                    print(f"Health check failed: {response.status} - {error_text}")
                    
            # Test get_context endpoint
            print(f"\nTesting FastMCP get_context endpoint...")
            payload = {
                "jsonrpc": "2.0",
                "method": "get_context",
                "params": {
                    "auth_token": "default_token",
                    "token_type": "OpenWebUI",
                    "prompt": "Test prompt from FastMCP client",
                    "history_summary": "Test history"
                },
                "id": 2
            }
            
            async with session.post(
                f"{base_url}/v1/json-rpc",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"Get context successful:")
                    print(f"Result has {len(result.get('result', {}).get('context_items', []))} context items")
                    print(f"Metadata: {json.dumps(result.get('result', {}).get('metadata', {}), indent=2)}")
                else:
                    error_text = await response.text()
                    print(f"Get context failed: {response.status} - {error_text}")
    except Exception as e:
        print(f"Error connecting to FastMCP server: {str(e)}")
        print("Make sure the server is running with: python main.py")

if __name__ == "__main__":
    asyncio.run(test_live_fastmcp_endpoints()) 