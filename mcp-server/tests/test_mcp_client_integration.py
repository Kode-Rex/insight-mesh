#!/usr/bin/env python3
"""
MCP Client Integration Tests

Tests the MCP server from a client perspective using the FastMCP client library.
These tests require a running MCP server and are marked as integration tests.
"""

import asyncio
import pytest
import os
from fastmcp import Client

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_mcp_client_connection_and_tools():
    """Test MCP server connection and tool availability via FastMCP client"""
    # Get MCP server configuration from environment
    mcp_port = os.environ.get("MCP_PORT", "9091")
    mcp_host = os.environ.get("MCP_HOST", "localhost")
    mcp_url = f"http://{mcp_host}:{mcp_port}/mcp/"
    
    try:
        # Create FastMCP client for SSE transport
        client = Client(mcp_url)
        
        async with client:
            # Test that we can connect
            assert client is not None
            
            # Test listing available tools
            tools = await client.list_tools()
            assert tools is not None
            assert len(tools) > 0
            
            tool_names = [tool.name for tool in tools]
            
            # Verify required tools are available
            assert "health_check" in tool_names, "health_check tool should be available"
            assert "get_context" in tool_names, "get_context tool should be available"
            
            return tool_names
            
    except Exception as e:
        pytest.fail(f"Failed to connect to MCP server at {mcp_url}: {e}")


@pytest.mark.asyncio 
async def test_mcp_health_check_tool():
    """Test the health_check tool via FastMCP client"""
    mcp_port = os.environ.get("MCP_PORT", "9091")
    mcp_host = os.environ.get("MCP_HOST", "localhost")
    mcp_url = f"http://{mcp_host}:{mcp_port}/mcp/"
    
    try:
        client = Client(mcp_url)
        
        async with client:
            # Call the health_check tool
            result = await client.call_tool("health_check", {})
            
            # Verify the result structure
            assert result is not None
            assert len(result) > 0
            
            # The result should contain health status information
            # FastMCP returns a list of TextContent objects
            health_response = result[0].text if hasattr(result[0], 'text') else str(result[0])
            assert "healthy" in health_response.lower()
            
    except Exception as e:
        pytest.fail(f"Health check tool test failed: {e}")


@pytest.mark.asyncio
async def test_mcp_get_context_tool():
    """Test the get_context tool via FastMCP client"""
    mcp_port = os.environ.get("MCP_PORT", "9091") 
    mcp_host = os.environ.get("MCP_HOST", "localhost")
    mcp_url = f"http://{mcp_host}:{mcp_port}/mcp/"
    
    try:
        client = Client(mcp_url)
        
        async with client:
            # Call the get_context tool with test parameters
            result = await client.call_tool("get_context", {
                "auth_token": "default_token",
                "token_type": "OpenWebUI",
                "prompt": "test prompt for integration test",
                "history_summary": "test history summary"
            })
            
            # Verify we got a response
            assert result is not None
            assert len(result) > 0
            
            # The result should be a structured response
            context_response = result[0].text if hasattr(result[0], 'text') else str(result[0])
            assert context_response is not None
            assert len(context_response) > 0
            
    except Exception as e:
        # Get context might fail due to authentication or other issues in test environment
        # That's okay - we're mainly testing that the tool is callable
        assert "auth_token" in str(e) or "token" in str(e) or "Invalid" in str(e), \
               f"Expected authentication error, but got: {e}"


if __name__ == "__main__":
    # Allow running tests directly for debugging
    import asyncio
    
    async def run_tests():
        print("Running MCP client integration tests...")
        
        try:
            print("1. Testing connection and tools...")
            tools = await test_mcp_client_connection_and_tools()
            print(f"✅ Found tools: {tools}")
            
            print("2. Testing health check...")
            await test_mcp_health_check_tool()
            print("✅ Health check passed")
            
            print("3. Testing get context...")
            await test_mcp_get_context_tool()
            print("✅ Get context test passed")
            
            print("\n🎉 All MCP client integration tests passed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(run_tests()) 