from fastmcp import FastMCP, Context
import jwt
import os
from loguru import logger
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
from context_service import context_service
from models import (
    ContextRequest,
    ContextResponse,
    ContextItem,
    ContextSource,
    RetrievalMetadata,
    ResponseMetadata,
    UserInfo
)
from datetime import datetime, UTC
import time
from fastapi import FastAPI, Depends, Header, HTTPException

# Load environment variables
load_dotenv()

# Configuration
class Settings:
    MCP_API_KEY: str = os.getenv("MCP_API_KEY", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    OPENWEBUI_DB_URL: str = os.getenv("OPENWEBUI_DB_URL", "postgresql://postgres:postgres@postgres:5432/openwebui")
    MCP_PORT: int = int(os.getenv("MCP_PORT", "9091"))  # Default port 9091
    MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0")  # Default host 0.0.0.0

settings = Settings()

# Configure logger
logger.remove()  # Remove default handler
logger.add(
    "logs/mcp_server.log",
    rotation="100 MB",
    retention="1 week",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}"
)
logger.add(
    lambda msg: print(msg, end=""),  # Console handler
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}"
)

# Create the FastMCP app
mcp = FastMCP("InsightMesh MCP Server")

# Create a FastAPI app for backward compatibility
app = FastAPI()

# Helper function to validate token
async def validate_token(token: str, token_type: str) -> UserInfo:
    """Validate and decode the JWT token"""
    try:
        logger.info(f"Validating token of type {token_type}")
        
        # Handle default token
        if token == "default_token":
            logger.info("Using default token with default email for permission filtering")
            return UserInfo(
                id="default_user",
                email="tmfrisinger@gmail.com",  # Default email for permission filtering
                name="Default User",
                is_active=True,
                token_type=token_type
            )
        
        # For OpenWebUI tokens, we don't verify the signature
        if token_type == "OpenWebUI":
            logger.debug("Decoding OpenWebUI token without signature verification")
            decoded = jwt.decode(token, options={"verify_signature": False})
            logger.debug(f"Decoded token payload: {decoded}")
            user_id = decoded.get("sub")
            logger.info("Extracted user_id from token")
            if not user_id:
                logger.error("OpenWebUI token missing user_id (sub claim)")
                raise ValueError("Invalid OpenWebUI token: missing user ID")
            # Use default email for permission filtering
            logger.info(f"Using default email for permission filtering")
            return UserInfo(
                id=user_id,
                email="tmfrisinger@gmail.com",  # Default email for permission filtering
                name="Default User",
                is_active=True,
                token_type=token_type
            )
        elif token_type == "Slack":
            if not token.startswith("slack:"):
                logger.error("Invalid Slack token format")
                raise ValueError("Invalid Slack token format. Expected 'slack:{user_id}'")
            user_id = token.split(":", 1)[1]
            logger.info("Extracted Slack user_id from token")
            # Use default email for permission filtering
            logger.info(f"Using default email for permission filtering")
            return UserInfo(
                id=user_id,
                email="tmfrisinger@gmail.com",  # Default email for permission filtering
                name="Default User",
                is_active=True,
                token_type=token_type
            )
        else:
            logger.info("Validating token with signature verification")
            decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
            logger.debug(f"Decoded token payload: {decoded}")
            user_id = decoded.get("sub") or decoded.get("id")
            logger.info("Extracted user_id from token")
            if not user_id:
                logger.error("Token missing user ID")
                raise ValueError("Invalid token: missing user ID")
            return UserInfo(
                id=user_id,
                email=decoded.get("email"),
                name=decoded.get("name"),
                is_active=decoded.get("is_active", True),
                token_type=token_type
            )
        logger.info("Token validation successful")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token error: {str(e)}")
        raise ValueError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}", exc_info=True)
        raise ValueError("Error processing token")

# FastAPI API key verification
async def verify_api_key(x_api_key: str = Header(...)) -> None:
    """Verify the API key from the request header"""
    if x_api_key != settings.MCP_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

@mcp.tool
async def get_context(
    auth_token: str,
    token_type: str,
    prompt: str,
    history_summary: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Retrieve context based on the user's token, prompt, and conversation history.
    The context is personalized based on the user's identity and the current conversation.
    
    Args:
        auth_token: JWT token for user authentication
        token_type: Type of JWT token (e.g., OpenWebUI)
        prompt: User's current prompt
        history_summary: Summary of conversation history (optional)
        
    Returns:
        A dictionary containing context items and metadata
    """
    try:
        if ctx:
            await ctx.info(f"Processing context request for prompt: {prompt[:100]}...")  # Log first 100 chars of prompt
        else:
            logger.info(f"Processing context request for prompt: {prompt[:100]}...")
        
        # Validate the token and get user info
        user_info = await validate_token(auth_token, token_type)
        user_id = user_info.id
        
        if ctx:
            await ctx.info(f"User authenticated: {user_id}")
        else:
            logger.info(f"User authenticated: {user_id}")
        
        # Get context for the prompt using ContextService (this will search Elasticsearch)
        context_result = await context_service.get_context_for_prompt(
            user_id=user_id,
            prompt=prompt,
            history_summary=history_summary,
            user_info=user_info
        )
        
        if ctx:
            await ctx.info(f"Context retrieved - Cache hit: {context_result.cache_hit}, "
                    f"Retrieval time: {context_result.retrieval_time_ms}ms, "
                    f"Documents: {len(context_result.documents)}")
        else:
            logger.info(f"Context retrieved - Cache hit: {context_result.cache_hit}, "
                    f"Retrieval time: {context_result.retrieval_time_ms}ms, "
                    f"Documents: {len(context_result.documents)}")
        
        # Convert document results to context items
        context_items = [
            ContextItem(
                content=doc.content,
                role="system",
                metadata={
                    "source": doc.source,
                    "document_id": doc.metadata.get("id"),
                    "url": doc.metadata.get("url"),
                    "file_name": doc.metadata.get("file_name"),
                    "created_time": doc.metadata.get("created_time"),
                    "modified_time": doc.metadata.get("modified_time"),
                    "relevance_score": doc.metadata.get("score"),
                    "source_type": doc.metadata.get("source_type")
                }
            )
            for doc in context_result.documents
        ]
        
        # Create response metadata
        response_metadata = ResponseMetadata(
            user=user_info,
            token_type=token_type,
            timestamp=datetime.now(UTC).isoformat(),
            context_sources=[
                ContextSource(type="documents", count=len(context_result.documents))
            ],
            retrieval_metadata=RetrievalMetadata(
                cache_hit=context_result.cache_hit,
                retrieval_time_ms=context_result.retrieval_time_ms
            )
        )
        
        # Create and return the response
        response = {
            "context_items": [item.dict() for item in context_items],
            "metadata": response_metadata.dict()
        }
        
        if ctx:
            await ctx.info(f"Returning response with {len(context_items)} context items")
        else:
            logger.info(f"Returning response with {len(context_items)} context items")
            
        return response
        
    except Exception as e:
        logger.error(f"Error processing context request: {str(e)}", exc_info=True)
        if ctx:
            await ctx.error(f"Error processing context request: {str(e)}")
        raise

@mcp.tool
def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}

@mcp.resource("system://about")
def system_info() -> str:
    """Get information about the MCP server"""
    return """
    InsightMesh MCP Server
    
    This server implements the Model Context Protocol (MCP) for providing context-aware
    responses to LLM conversations. It retrieves context from various sources based on
    user queries and conversation history.
    
    Available tools:
    - get_context: Retrieve personalized context for a user's prompt
    - health_check: Check if the server is healthy
    """

# FastAPI endpoint for backward compatibility with the RAG hook
@app.post("/context", response_model=ContextResponse)
async def legacy_context_endpoint(
    request: ContextRequest,
    _: None = Depends(verify_api_key)
) -> ContextResponse:
    """Legacy REST API endpoint for backward compatibility with the RAG hook"""
    try:
        logger.info(f"Legacy REST endpoint called for prompt: {request.prompt[:100]}...")
        
        # Implement the context logic directly here instead of trying to call the FastMCP tool
        try:
            # Validate the token and get user info
            user_info = await validate_token(request.auth_token, request.token_type)
            user_id = user_info.id
            logger.info(f"User authenticated: {user_id}")
            
            # Get context for the prompt using ContextService
            context_result = await context_service.get_context_for_prompt(
                user_id=user_id,
                prompt=request.prompt,
                history_summary=request.history_summary,
                user_info=user_info
            )
            
            logger.info(f"Context retrieved - Cache hit: {context_result.cache_hit}, "
                    f"Retrieval time: {context_result.retrieval_time_ms}ms, "
                    f"Documents: {len(context_result.documents)}")
            
            # Convert document results to context items
            context_items = [
                ContextItem(
                    content=doc.content,
                    role="system",
                    metadata={
                        "source": doc.source,
                        "document_id": doc.metadata.get("id"),
                        "url": doc.metadata.get("url"),
                        "file_name": doc.metadata.get("file_name"),
                        "created_time": doc.metadata.get("created_time"),
                        "modified_time": doc.metadata.get("modified_time"),
                        "relevance_score": doc.metadata.get("score"),
                        "source_type": doc.metadata.get("source_type")
                    }
                )
                for doc in context_result.documents
            ]
            
            # Create response metadata
            response_metadata = ResponseMetadata(
                user=user_info,
                token_type=request.token_type,
                timestamp=datetime.now(UTC).isoformat(),
                context_sources=[
                    ContextSource(type="documents", count=len(context_result.documents))
                ],
                retrieval_metadata=RetrievalMetadata(
                    cache_hit=context_result.cache_hit,
                    retrieval_time_ms=context_result.retrieval_time_ms
                )
            )
            
            # Create and return the response
            response = ContextResponse(
                context_items=context_items,
                metadata=response_metadata
            )
            
            logger.info(f"Legacy REST endpoint returning {len(context_items)} context items")
            return response
                
        except Exception as e:
            logger.error(f"Error processing context request: {str(e)}", exc_info=True)
            raise
        
    except ValueError as e:
        logger.error(f"Validation error in legacy endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in legacy endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check_endpoint() -> Dict[str, str]:
    """Health check endpoint for FastAPI"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    import contextlib
    
    # Create a FastAPI app that mounts both the FastMCP app and the legacy REST API
    from fastapi import FastAPI
    
    # Create a combined app
    combined_app = FastAPI()
    
    # Mount the FastMCP http app at /mcp
    combined_app.mount("/mcp", mcp.http_app())
    
    # Include the legacy API routes
    for route in app.routes:
        combined_app.routes.append(route)
    
    # Run the combined app
    logger.info(f"Starting combined FastMCP + REST API server on {settings.MCP_HOST}:{settings.MCP_PORT}...")
    uvicorn.run(combined_app, host=settings.MCP_HOST, port=settings.MCP_PORT) 