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

# MCP Server configuration
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://mcp:8000")
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
MCP_TIMEOUT = int(os.environ.get("MCP_TIMEOUT", "30"))  # Timeout in seconds
MCP_MAX_RETRIES = int(os.environ.get("MCP_MAX_RETRIES", "3"))
TOKEN_TYPE = os.environ.get("TOKEN_TYPE", "OpenWebUI")  # Type of JWT token being used

async def get_context_from_mcp(
    api_key: str,
    auth_token: str,
    token_type: str,
    prompt: str,
    history_summary: str,
    session: Optional[aiohttp.ClientSession] = None
) -> Optional[Dict[str, Any]]:
    """Get context from MCP server"""
    if not api_key or not auth_token or not prompt:
        return None
        
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True
    
    try:
        # Use the legacy REST API endpoint directly
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "auth_token": auth_token,
            "token_type": token_type,
            "prompt": prompt,
            "history_summary": history_summary
        }
        
        logger.info(f"Calling MCP context endpoint: {MCP_SERVER_URL}/context")
        async with session.post(
            f"{MCP_SERVER_URL}/context",
            headers=headers,
            json=payload,
            timeout=MCP_TIMEOUT
        ) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"Successfully retrieved context from MCP server")
                return result
            else:
                error_text = await response.text()
                logger.error(f"MCP server error: {response.status} - {error_text}")
                return None
    except Exception as e:
        logger.error(f"Error calling MCP server: {e}")
        return None
    finally:
        if close_session:
            await session.close()

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
        call_type: Literal["completion", "text_completion", "embeddings", "image_generation", "moderation", "audio_transcription"]
    ):
        logger.info("=== RAG HANDLER ENTRY POINT ===")
        logger.info(f"Call type: {call_type}")
        logger.info(f"Data keys: {list(data.keys())}")
        
        try:
            # Only process completion requests
            if call_type != "completion":
                logger.info("Skipping non-completion request")
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
            
            # Get context from MCP server
            session = await self._ensure_session()
            context = await get_context_from_mcp(
                api_key=MCP_API_KEY,
                auth_token=auth_token,
                token_type=token_type,
                prompt=latest_user_message,
                history_summary=history_summary,
                session=session
            )
            
            # Only modify the request if we got valid context
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
                
                # Create a system message that instructs the model to cite sources with URLs
                system_message = (
                    "You are a helpful assistant that MUST cite sources in EVERY response. "
                    "IMPORTANT: You MUST explicitly mention which documents you used in your answer. "
                    "Format your response like this:\n\n"
                    "1. First, provide your answer\n"
                    "2. Then, on a new line, write 'Sources used:' followed by a list of the document sources you referenced\n"
                    "3. If the source has a URL, include it after the source name using the format: [Source Name](URL)\n\n"
                    "Here are the relevant documents to help answer the user's question:\n\n"
                    f"{context_str}\n\n"
                    "REMEMBER: You MUST cite your sources in EVERY response. If you don't cite sources, your response is incomplete."
                )
                
                # Find or create system message
                system_messages = [msg for msg in messages if msg.get("role") == "system"]
                if system_messages:
                    # Update the system message with context
                    system_messages[0]["content"] = system_message
                    logger.info("Updated existing system message with context")
                else:
                    # Create new system message with context
                    messages.insert(0, {
                        "role": "system",
                        "content": system_message
                    })
                    logger.info("Created new system message with context")
                
                # Update the request data
                data["messages"] = messages
                logger.info("Successfully injected context into request")
            else:
                logger.info("No context items received from MCP")
            
        except Exception as e:
            logger.error(f"Error in pre_request_hook: {str(e)}", exc_info=True)
            # On error, return the original data unchanged
            return data
        
        return data

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