import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, "/app")

import logging

# Create logger
logger = logging.getLogger("mcp_tool_handler_simple")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

logger.info("!!! SIMPLE MCP TOOL HANDLER MODULE LOADED !!!")

# Import LiteLLM dependencies only when needed
def get_custom_logger():
    from litellm.integrations.custom_logger import CustomLogger
    return CustomLogger

class SimpleMCPToolHandler:
    def __init__(self):
        logger.info("SimpleMCPToolHandler initialized")
    
    async def async_post_call_success_hook(
        self,
        user_api_key_dict,
        response_obj,
        start_time: float,
        end_time: float
    ):
        """Simple post-response hook that just logs"""
        logger.info("=== SIMPLE MCP TOOL HANDLER POST-RESPONSE ===")
        logger.info(f"Response received in {end_time - start_time:.2f}s")
        
        # Check if response has tool calls
        if hasattr(response_obj, 'choices') and response_obj.choices:
            message = response_obj.choices[0].message
            
            if hasattr(message, 'tool_calls') and message.tool_calls:
                logger.info(f"Found {len(message.tool_calls)} tool calls (not executing in simple mode)")
        
        return response_obj

# Create the handler class that inherits from CustomLogger
try:
    CustomLogger = get_custom_logger()
    
    class MCPToolHandlerSimple(CustomLogger, SimpleMCPToolHandler):
        pass
    
    # Create an instance of the handler
    mcp_tool_handler_instance = MCPToolHandlerSimple()
    logger.info("Created simple mcp_tool_handler_instance")
    
except Exception as e:
    logger.error(f"Failed to create CustomLogger-based handler: {e}")
    # Fallback to simple handler
    mcp_tool_handler_instance = SimpleMCPToolHandler()
    logger.info("Created fallback mcp_tool_handler_instance") 