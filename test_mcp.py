import asyncio
import pytest
from fastmcp import Client

@pytest.mark.asyncio
async def test_mcp_client():
    try:
        # Create FastMCP client for SSE transport
        # The MCP server is running on port 9090 (mapped from 9091) with SSE transport
        # For SSE, we need to connect to the /mcp/ endpoint
        client = Client("http://localhost:9090/mcp/")
        
        print("Testing MCP server connection...")
        
        async with client:
            print("Connected to MCP server!")
            
            # Test listing available tools
            print("Listing available tools...")
            tools = await client.list_tools()
            print(f"Available tools: {[tool.name for tool in tools]}")
            
            # Test the health_check tool
            if any(tool.name == "health_check" for tool in tools):
                print("Testing health_check tool...")
                result = await client.call_tool("health_check", {})
                print(f"Health check result: {result}")
            else:
                print("health_check tool not found")
            
            # Test the get_context tool if available
            if any(tool.name == "get_context" for tool in tools):
                print("Testing get_context tool...")
                result = await client.call_tool("get_context", {
                    "auth_token": "default_token",
                    "token_type": "OpenWebUI", 
                    "prompt": "test prompt",
                    "history_summary": "test history"
                })
                print(f"Get context result: {result}")
            else:
                print("get_context tool not found")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_client()) 