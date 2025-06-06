#!/usr/bin/env python3

import os
import sys
import asyncio
from fastmcp import Client

async def main():
    print("Connecting to FastMCP server...")
    
    server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/sse")
    print(f"Using server URL: {server_url}")
    
    try:
        async with Client(server_url) as client:
            print("\n✅ Successfully connected to FastMCP server!")
            
            # Get server info
            info = await client.get_server_info()
            print(f"\nServer Name: {info.name}")
            print(f"Server Version: {info.version}")
            
            # List available tools
            tools = await client.list_tools()
            print(f"\nAvailable Tools ({len(tools)}):")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # List available resources
            resources = await client.list_resources()
            print(f"\nAvailable Resources ({len(resources)}):")
            for resource in resources:
                print(f"  - {resource.uri}: {resource.description}")
            
            # Try to call the health check tool
            print("\nTesting health check...")
            result = await client.call_tool("health_check", {})
            print(f"Health check result: {result.text}")
            
            print("\nFastMCP server is configured and running correctly! 🚀")
    
    except Exception as e:
        print(f"\n❌ Error connecting to FastMCP server: {e}")
        print("\nPlease make sure the server is running and the URL is correct.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 