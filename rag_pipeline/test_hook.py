#!/usr/bin/env python3

import asyncio
import os
import pytest
from rag_pipeline.pre_request_hook import rag_handler_instance, get_context_from_mcp

# Get MCP server port from environment, default to 9091
mcp_port = os.environ.get("MCP_PORT", "9091")
mcp_host = os.environ.get("MCP_HOST", "localhost")

# Force override the MCP_SERVER_URL in the pre_request_hook module
import rag_pipeline.pre_request_hook as pre_request_hook
pre_request_hook.MCP_SERVER_URL = f"http://{mcp_host}:{mcp_port}"
print(f"Using MCP server URL: {pre_request_hook.MCP_SERVER_URL}")

@pytest.mark.asyncio
async def test():
    print("Testing RAG hook with MCP server...")
    
    try:
        result = await get_context_from_mcp(
            api_key='insight-mesh-mcp-abc-123',
            auth_token='default_token',
            token_type='OpenWebUI',
            prompt='Test prompt',
            history_summary='Test history'
        )
        
        if result:
            print(f"Success! Retrieved {len(result.get('context_items', []))} context items")
            print(f"Metadata: {result.get('metadata', {})}")
        else:
            print("Failed to retrieve context from MCP server")
    
    except Exception as e:
        print(f"Error testing RAG hook: {e}")

if __name__ == "__main__":
    asyncio.run(test()) 