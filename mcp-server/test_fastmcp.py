#!/usr/bin/env python3

import json
import aiohttp
import asyncio
import os

async def test_fastmcp_endpoints():
    """Test the FastMCP HTTP endpoints directly"""
    # Get MCP server port from environment, default to 9091
    mcp_port = os.environ.get("MCP_PORT", "9091")
    mcp_host = os.environ.get("MCP_HOST", "localhost")
    
    base_url = f"http://{mcp_host}:{mcp_port}/mcp"
    
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

if __name__ == "__main__":
    asyncio.run(test_fastmcp_endpoints()) 