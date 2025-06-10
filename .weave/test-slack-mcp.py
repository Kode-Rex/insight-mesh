#!/usr/bin/env python3
"""
Test script for MCP server Slack integration

This script demonstrates how to call the MCP server with Slack authentication
using the sample user data for tmfrisinger@gmail.com.
"""

import asyncio
import aiohttp
import json
import os

# MCP server configuration
MCP_SERVER_URL = "http://localhost:9090"
SLACK_USER_ID = "U12345TRAVIS"  # Sample Slack user ID from our test data
SLACK_TOKEN = f"slack:{SLACK_USER_ID}"

async def test_mcp_call():
    """Test calling the MCP server with Slack authentication"""
    
    # Prepare the request payload
    payload = {
        "auth_token": SLACK_TOKEN,
        "token_type": "Slack",
        "prompt": "What are our Q1 goals and objectives?",
        "history_summary": "User is asking about quarterly planning and business objectives."
    }
    
    print("🚀 Testing MCP Server Slack Integration")
    print(f"📡 MCP Server URL: {MCP_SERVER_URL}")
    print(f"👤 Slack User ID: {SLACK_USER_ID}")
    print(f"🔑 Auth Token: {SLACK_TOKEN}")
    print(f"💬 Prompt: {payload['prompt']}")
    print("\n" + "="*60)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test the get_context tool
            print("📞 Calling MCP server get_context tool...")
            
            # MCP tool call format
            mcp_payload = {
                "method": "tools/call",
                "params": {
                    "name": "get_context",
                    "arguments": payload
                }
            }
            
            async with session.post(
                f"{MCP_SERVER_URL}/mcp",
                json=mcp_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"📊 Response Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ Success! MCP server response:")
                    print(json.dumps(result, indent=2))
                    
                    # Extract and display key information
                    if "result" in result:
                        context_items = result["result"].get("context_items", [])
                        metadata = result["result"].get("metadata", {})
                        
                        print(f"\n📋 Context Items Found: {len(context_items)}")
                        print(f"👤 User Info: {metadata.get('user', {})}")
                        print(f"🔐 Token Type: {metadata.get('token_type')}")
                        
                        if context_items:
                            print("\n📄 Context Items:")
                            for i, item in enumerate(context_items[:3], 1):  # Show first 3
                                print(f"  {i}. Source: {item.get('metadata', {}).get('source', 'Unknown')}")
                                print(f"     Content: {item.get('content', '')[:100]}...")
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Error: {response.status}")
                    print(f"📝 Error Details: {error_text}")
                    
    except aiohttp.ClientConnectorError:
        print("❌ Connection Error: Could not connect to MCP server")
        print("💡 Make sure the MCP server is running on localhost:9090")
        print("🐳 Try: docker-compose up mcp")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

async def test_health_check():
    """Test the MCP server health check"""
    print("\n🏥 Testing MCP server health check...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MCP_SERVER_URL}/mcp",
                json={
                    "method": "tools/call",
                    "params": {
                        "name": "health_check",
                        "arguments": {}
                    }
                },
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print("✅ Health check passed!")
                    print(f"📊 Result: {result}")
                else:
                    print(f"❌ Health check failed: {response.status}")
                    
    except Exception as e:
        print(f"❌ Health check error: {e}")

def print_setup_instructions():
    """Print setup instructions for running the test"""
    print("\n" + "="*60)
    print("🛠️  SETUP INSTRUCTIONS")
    print("="*60)
    print("1. Start the consolidated PostgreSQL and MCP services:")
    print("   docker-compose up postgres mcp")
    print()
    print("2. Run database migrations:")
    print("   weave migrate up")
    print()
    print("3. Insert sample Slack user data:")
    print("   docker-compose exec postgres psql -U postgres -d insight_mesh -f /tmp/sample-slack-data.sql")
    print("   (You may need to copy the SQL file into the container first)")
    print()
    print("4. Run this test script:")
    print("   python .weave/test-slack-mcp.py")
    print()
    print("📝 Sample Slack User Data:")
    print(f"   User ID: {SLACK_USER_ID}")
    print("   Email: tmfrisinger@gmail.com")
    print("   Name: Travis Frisinger")
    print()
    print("💡 Additional Weave migrate commands:")
    print("   weave migrate status          # Check migration status")
    print("   weave migrate history mcp     # View MCP migration history")
    print("   weave migrate create mcp 'message'  # Create new migration")

async def main():
    """Main test function"""
    print_setup_instructions()
    
    print("\n" + "="*60)
    print("🧪 RUNNING TESTS")
    print("="*60)
    
    # Test health check first
    await test_health_check()
    
    # Test Slack integration
    await test_mcp_call()
    
    print("\n" + "="*60)
    print("✨ Test completed!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main()) 