import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, "/app")

import logging

# Create a custom logger (named "rag_handler") and set its level to INFO.
logger = logging.getLogger("rag_handler")
logger.setLevel(logging.INFO)

# Determine log file path based on environment
LOG_DIR = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "rag_handler.log")

# Create a console handler to output logs to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

try:
    # Try to create a file handler, but don't fail if it's not possible
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s – %(name)s – %(levelname)s – %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    logger.info(f"File logging enabled: {LOG_FILE}")
except Exception as e:
    logger.warning(f"Could not set up file logging to {LOG_FILE}: {e}")

# Log a message that the module has been loaded
logger.info("!!! RAG HANDLER MODULE LOADED !!!")

from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy.proxy_server import UserAPIKeyAuth, DualCache
from typing import Optional, Literal, Dict, Any, List
import json
import aiohttp
import asyncio
from datetime import datetime

# MCP Server configuration
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://mcp:9091/sse")
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
MCP_TIMEOUT = int(os.environ.get("MCP_TIMEOUT", "30"))  # Timeout in seconds
MCP_MAX_RETRIES = int(os.environ.get("MCP_MAX_RETRIES", "3"))
TOKEN_TYPE = os.environ.get("TOKEN_TYPE", "OpenWebUI")  # Type of JWT token being used

# MCP Registry configuration (for reading config)
MCP_REGISTRY_URL = os.environ.get("MCP_REGISTRY_URL", "http://mcp-registry:8080")

async def get_context_from_mcp(
    api_key: str,
    auth_token: str,
    token_type: str,
    prompt: str,
    history_summary: str,
    session: Optional[aiohttp.ClientSession] = None
) -> Optional[Dict[str, Any]]:
    """Get context from MCP server using FastMCP client"""
    if not auth_token or not prompt:
        return None
    
    try:
        from fastmcp import Client
        
        # Use the MCP server URL directly for SSE transport
        mcp_url = MCP_SERVER_URL
        
        # Use the FastMCP client which handles all the protocol details
        logger.info(f"Calling MCP server with FastMCP client at: {mcp_url}")
        
        # Create the MCP client - exactly like the working test
        client = Client(mcp_url)
        
        # Call the get_context tool - exactly like the working test
        async with client:
            result = await client.call_tool("get_context", {
                "auth_token": auth_token,
                "token_type": token_type,
                "prompt": prompt,
                "history_summary": history_summary or ""
            })
            
            logger.info(f"MCP response received: {len(str(result))} chars")
            
            # The result from call_tool is already parsed - it's a list of TextContent objects
            if result and len(result) > 0:
                # Extract the text content from the first result
                text_content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                try:
                    # Parse the JSON response
                    import json
                    parsed_result = json.loads(text_content)
                    return parsed_result
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse MCP response as JSON: {text_content[:200]}...")
                    return None
            else:
                logger.warning("Empty result from MCP server")
                return None
        
    except Exception as e:
        logger.error(f"Error calling MCP server: {str(e)}")
        return None

async def get_mcp_servers_from_registry(
    session: Optional[aiohttp.ClientSession] = None
) -> Optional[Dict[str, Any]]:
    """Get MCP server configurations from the registry"""
    try:
        if not session:
            session = aiohttp.ClientSession()
            should_close = True
        else:
            should_close = False
            
        # Get RAG-scoped MCP servers from registry
        async with session.get(
            f"{MCP_REGISTRY_URL}/servers/rag",
            timeout=aiohttp.ClientTimeout(total=MCP_TIMEOUT)
        ) as response:
            if response.status == 200:
                servers_data = await response.json()
                logger.info(f"Retrieved {len(servers_data)} MCP servers from registry")
                return servers_data
            else:
                logger.warning(f"Failed to get MCP servers from registry: {response.status}")
                return None
                
    except Exception as e:
        logger.error(f"Error getting MCP servers from registry: {str(e)}")
        return None
    finally:
        if should_close and session:
            await session.close()

# Removed get_mcp_tools_from_litellm - LiteLLM doesn't have MCP server management APIs
# The correct approach is to read MCP servers directly from the registry and call them directly

def summarize_conversation_history(messages: List[Dict[str, str]]) -> str:
    """Create a summary of the conversation history"""
    if not messages:
        return ""
        
    # Only include the last few messages to keep the summary concise
    recent_messages = messages[-5:] if len(messages) > 5 else messages
    
    summary = []
    for msg in recent_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "").strip()
        if content:
            summary.append(f"{role}: {content[:100]}...")
            
    return "\n".join(summary)

class RAGHandler(CustomLogger):
    def __init__(self):
        self.session = None
        logger.info("RAGHandler initialized")
        
    async def _ensure_session(self):
        """Ensure we have an active aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            logger.info("Created new aiohttp session")
        return self.session

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: Literal["completion", "acompletion", "text_completion", "embeddings", "image_generation", "moderation", "audio_transcription"]
    ):
        logger.info("=== RAG HANDLER ENTRY POINT ===")
        logger.info(f"Call type: {call_type}")
        logger.info(f"Data keys: {list(data.keys())}")
        
        try:
            # Only process completion requests (both sync and async)
            if call_type not in ["completion", "acompletion"]:
                logger.info(f"Skipping non-completion request: {call_type}")
                return data

            # Get the messages from the request
            messages = data.get("messages", [])
            if not messages:
                logger.warning("No messages in request")
                return data

            # Log full metadata contents
            metadata = data.get("metadata", {})
            logger.info(f"Full metadata: {metadata.keys()}")
            
            # Log full headers if available
            if "headers" in metadata:
                logger.info(f"Headers in metadata: {metadata['headers']}")
            
            # Log proxy_server_request
            proxy_request = data.get("proxy_server_request", {})
            if proxy_request:
                logger.info(f"Proxy request headers: {proxy_request.get('headers', {})}")
            
            # Log user_api_key_dict details
            if hasattr(user_api_key_dict, "headers"):
                logger.info(f"user_api_key_dict headers: {user_api_key_dict.headers}")
            
            if hasattr(user_api_key_dict, "metadata"):
                logger.info(f"user_api_key_dict metadata: {user_api_key_dict.metadata}")

            # Extract auth token from metadata if available
            auth_token = "default_token"
            token_type = TOKEN_TYPE
            
            # Check if we have metadata with user information
            metadata = data.get("metadata", {})
            
            # Try to extract headers from the original request
            if "X-Auth-Token" in metadata:
                auth_token = metadata["X-Auth-Token"]
                # If token is in format slack:USER_ID, extract the user ID
                if auth_token.startswith("slack:"):
                    token_type = "Slack"
                logger.info(f"Using auth token from X-Auth-Token header: {auth_token[:10]}... (Type: {token_type})")
            # Check the headers passed via user_api_key_dict
            elif hasattr(user_api_key_dict, "headers") and user_api_key_dict.headers:
                auth_header = user_api_key_dict.headers.get("x-auth-token") or user_api_key_dict.headers.get("X-Auth-Token")
                if auth_header:
                    auth_token = auth_header
                    # If token is in format slack:USER_ID, extract the user ID
                    if auth_token.startswith("slack:"):
                        token_type = "Slack"
                    logger.info(f"Using auth token from user_api_key_dict headers: {auth_token[:10]}... (Type: {token_type})")
            # Check metadata headers
            elif "headers" in metadata and metadata["headers"]:
                headers = metadata["headers"]
                auth_header = headers.get("x-auth-token") or headers.get("X-Auth-Token")
                if auth_header:
                    auth_token = auth_header
                    if auth_token.startswith("slack:"):
                        token_type = "Slack"
                    logger.info(f"Using auth token from metadata headers: {auth_token[:10]}... (Type: {token_type})")
            # Check proxy_server_request headers
            elif proxy_request and "headers" in proxy_request:
                headers = proxy_request.get("headers", {})
                auth_header = headers.get("x-auth-token") or headers.get("X-Auth-Token")
                if auth_header:
                    auth_token = auth_header
                    if auth_token.startswith("slack:"):
                        token_type = "Slack"
                    logger.info(f"Using auth token from proxy_server_request headers: {auth_token[:10]}... (Type: {token_type})")
            else:
                logger.info(f"No auth token found in request, using default: {auth_token}")
            
            # Get the latest user message
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            if not user_messages:
                logger.warning("No user messages found")
                return data
                
            latest_user_message = user_messages[-1]["content"]
            logger.info(f"Latest user message: {latest_user_message[:100]}...")
            
            history_summary = summarize_conversation_history(messages[:-1])  # Exclude latest message
            logger.info(f"History summary: {history_summary[:100]}...")
            
            # Get context from MCP server and available tools
            session = await self._ensure_session()
            
            # Fetch context from MCP
            context = await get_context_from_mcp(
                api_key=MCP_API_KEY,
                auth_token=auth_token,
                token_type=token_type,
                prompt=latest_user_message,
                history_summary=history_summary,
                session=session
            )
            
            # Get current date and time for all requests
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            
            # Check if we got valid context from MCP
            if context and context.get("context_items"):
                logger.info(f"Got {len(context['context_items'])} context items from MCP")
                # Build the context string from context items
                context_parts = []
                document_sources = []  # Track document sources with metadata
                for item in context["context_items"]:
                    item_metadata = item.get("metadata", {})
                    source = item_metadata.get("source", "unknown")
                    content = item.get("content", "")
                    url = item_metadata.get("url")
                    file_name = item_metadata.get("file_name")
                    
                    if content:
                        # Clean up the content by removing BOM and extra whitespace
                        content = content.replace("\ufeff", "").strip()
                        
                        # Add source information with metadata
                        source_info = f"[{source}]"
                        if file_name:
                            source_info += f" {file_name}"
                        
                        context_parts.append(f"{source_info}\n{content}\n")
                        
                        # Only add non-system context to document sources
                        if source != "system_context":
                            doc_meta = {
                                "source": source,
                                "url": url,
                                "file_name": file_name
                            }
                            document_sources.append(doc_meta)
                
                context_str = "\n\n".join(context_parts)
                logger.info(f"Context string length: {len(context_str)}")
                
                # Build a list of valid sources with proper formatting for citation examples
                citation_examples = []
                valid_sources = []
                
                for item in context["context_items"]:
                    item_metadata = item.get("metadata", {})
                    source = item_metadata.get("source", "unknown")
                    url = item_metadata.get("url")
                    file_name = item_metadata.get("file_name")
                    
                    # Skip system context for citation examples
                    if source == "system_context":
                        continue
                    
                    # Create a proper source name
                    if file_name:
                        source_name = file_name
                    elif source and source != "unknown":
                        source_name = source.replace("_", " ").title()
                    else:
                        source_name = "Document"
                    
                    # Include all sources, with URL if available
                    if url:
                        citation_examples.append(f"- [{source_name}]({url})")
                        valid_sources.append({"name": source_name, "url": url})
                    else:
                        citation_examples.append(f"- {source_name}")
                        valid_sources.append({"name": source_name, "url": None})
                
                # Create citation examples text
                if citation_examples:
                    examples_text = "Available sources for citation:\n" + "\n".join(citation_examples[:5])  # Limit to 5 examples
                else:
                    examples_text = "No specific sources available for citation."
                
                # Create a system message that instructs the model to cite sources with URLs
                system_message = (
                    f"The current date is {current_date}.\n\n"
                    "You are a helpful assistant that MUST cite sources in EVERY response when using provided context.\n\n"
                    "## SOURCE CITATION REQUIREMENTS:\n"
                    "1. You MUST cite sources for any information you use from the provided documents\n"
                    "2. Use ONLY the exact source names and URLs provided below\n"
                    "3. Do NOT make up or modify URLs - only use valid URLs that are provided\n\n"
                    "## CITATION FORMAT:\n"
                    "End your response with a 'Sources:' section using this exact format:\n\n"
                    "**Sources:**\n"
                    "- [Document Name](URL) - if URL is available\n"
                    "- Document Name - if no URL is available\n\n"
                    "## CITATION EXAMPLES:\n"
                    "**Sources:**\n"
                    "- [Company Policy Manual](https://docs.company.com/policies)\n"
                    "- Meeting Notes - March 2024\n"
                    "- [Technical Documentation](https://wiki.company.com/tech-docs)\n\n"
                    f"## {examples_text}\n\n"
                    "## CONTEXT DOCUMENTS:\n"
                    "Here are the relevant documents to help answer the user's question:\n\n"
                    f"{context_str}\n\n"
                    "## IMPORTANT REMINDERS:\n"
                    "- ALWAYS include a 'Sources:' section when using information from the provided documents\n"
                    "- Use the EXACT source names and URLs provided above\n"
                    "- Do NOT create or modify URLs\n"
                    "- If you cannot find relevant information in the provided sources, say so clearly"
                )
                
                logger.info("Created system message with MCP context and current date")
            else:
                logger.info("No context items received from MCP, creating basic system message with date")
                # Create a basic system message with just the current date
                system_message = f"The current date is {current_date}."
            
            # Find or create system message
            system_messages = [msg for msg in messages if msg.get("role") == "system"]
            if system_messages:
                # Check if existing system message already has date info
                existing_content = system_messages[0]["content"]
                if "The current date is" not in existing_content:
                    # Prepend date to existing system message
                    system_messages[0]["content"] = f"The current date is {current_date}.\n\n{existing_content}"
                    logger.info("Added current date to existing system message")
                elif context and context.get("context_items"):
                    # Update the system message with context (already includes date)
                    system_messages[0]["content"] = system_message
                    logger.info("Updated existing system message with context and date")
            else:
                # Create new system message
                messages.insert(0, {
                    "role": "system",
                    "content": system_message
                })
                logger.info("Created new system message with current date")
            
            # Note: MCP tools integration removed - LiteLLM doesn't provide MCP server management APIs
            # Tools would need to be implemented via direct MCP server communication if needed
            
            # Update the request data
            data["messages"] = messages
            logger.info("Successfully injected current date and tools into request")
            
        except Exception as e:
            logger.error(f"Error in pre_request_hook: {str(e)}", exc_info=True)
            # On error, return the original data unchanged
            return data
        
        return data

    async def async_post_call_success_hook(
        self,
        user_api_key_dict,
        response_obj,
        start_time: float,
        end_time: float
    ):
        """Handle tool calls in LLM responses - DISABLED since not using LiteLLM proxy for MCP tools"""
        # MCP tool execution disabled - just return the response as-is
        logger.debug(f"Post-call hook completed in {end_time - start_time:.2f}s (MCP tool execution disabled)")
        return response_obj
    
# _execute_mcp_tool_call method removed - not using LiteLLM proxy for MCP tool execution

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            logger.info("Closed aiohttp session")

# Create an instance of the handler
rag_handler_instance = RAGHandler()
logger.info("Created rag_handler_instance")