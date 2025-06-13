import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, "/app")

import logging
from typing import Optional, Literal, Dict, Any, List
import json
import asyncio

# Lazy imports to avoid startup issues
def get_litellm_imports():
    from litellm.integrations.custom_logger import CustomLogger
    from litellm.proxy.proxy_server import UserAPIKeyAuth, DualCache
    return CustomLogger, UserAPIKeyAuth, DualCache

def get_fastmcp_client():
    from fastmcp import Client
    return Client

# Create logger
logger = logging.getLogger("mcp_tool_handler")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

logger.info("!!! MCP TOOL HANDLER MODULE LOADED !!!")

# MCP Server configuration
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://mcp:9091/sse")
ENABLE_MCP_TOOL_EXECUTION = os.environ.get("ENABLE_MCP_TOOL_EXECUTION", "true").lower() == "true"

# Get the CustomLogger class
CustomLogger, UserAPIKeyAuth, DualCache = get_litellm_imports()

class MCPToolHandler(CustomLogger):
    def __init__(self):
        self.mcp_client = None
        logger.info("MCPToolHandler initialized")
    
    async def _get_mcp_client(self):
        """Get or create MCP client connection"""
        if self.mcp_client is None:
            Client = get_fastmcp_client()
            self.mcp_client = Client(MCP_SERVER_URL)
            await self.mcp_client.__aenter__()
            logger.info(f"Created MCP client connection to {MCP_SERVER_URL}")
        return self.mcp_client
    
    async def async_post_call_success_hook(
        self,
        user_api_key_dict,  # Remove type hint to avoid import issues
        response_obj: Any,
        start_time: float,
        end_time: float
    ):
        """Handle tool calls in LLM responses"""
        if not ENABLE_MCP_TOOL_EXECUTION:
            return response_obj
            
        logger.info("=== MCP TOOL HANDLER POST-RESPONSE ===")
        
        try:
            # Check if response has tool calls
            if hasattr(response_obj, 'choices') and response_obj.choices:
                message = response_obj.choices[0].message
                
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    logger.info(f"Found {len(message.tool_calls)} tool calls to execute")
                    
                    # Execute each tool call
                    tool_results = []
                    for tool_call in message.tool_calls:
                        try:
                            result = await self._execute_tool_call(tool_call)
                            tool_results.append({
                                "tool_call_id": tool_call.id,
                                "result": result
                            })
                        except Exception as e:
                            logger.error(f"Failed to execute tool call {tool_call.id}: {e}")
                            tool_results.append({
                                "tool_call_id": tool_call.id,
                                "error": str(e)
                            })
                    
                    # Add tool results to response metadata
                    if not hasattr(response_obj, 'metadata'):
                        response_obj.metadata = {}
                    response_obj.metadata['tool_results'] = tool_results
                    
                    logger.info(f"Executed {len(tool_results)} tool calls")
            
        except Exception as e:
            logger.error(f"Error in post-response hook: {str(e)}", exc_info=True)
        
        return response_obj
    
    async def _execute_tool_call(self, tool_call):
        """Execute a single tool call on MCP server"""
        try:
            # Import the transformation function
            from litellm.experimental_mcp_client.tools import transform_openai_tool_call_request_to_mcp_tool_call_request
            
            # Convert OpenAI tool call to MCP format
            mcp_call = transform_openai_tool_call_request_to_mcp_tool_call_request(
                openai_tool=tool_call.model_dump()
            )
            
            logger.info(f"Executing MCP tool: {mcp_call.name} with args: {mcp_call.arguments}")
            
            # Get MCP client and execute tool
            client = await self._get_mcp_client()
            result = await client.call_tool(
                name=mcp_call.name, 
                arguments=mcp_call.arguments
            )
            
            logger.info(f"Tool execution result: {result}")
            return result
            
        except ImportError as e:
            logger.error(f"Failed to import MCP tool utilities: {e}")
            raise Exception("MCP tool execution requires litellm.experimental_mcp_client.tools")
        except Exception as e:
            logger.error(f"Error executing tool call: {e}")
            raise
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.mcp_client:
            await self.mcp_client.__aexit__(exc_type, exc_val, exc_tb)
            self.mcp_client = None
            logger.info("Closed MCP client connection")

# Create an instance of the handler
mcp_tool_handler_instance = MCPToolHandler()
logger.info("Created mcp_tool_handler_instance") 