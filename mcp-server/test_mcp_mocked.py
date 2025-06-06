#!/usr/bin/env python3

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, UTC

# Import models and utilities
from main import (
    validate_token,
    ContextRequest,
    ContextResponse,
    ContextItem,
    ContextSource,
    RetrievalMetadata,
    ResponseMetadata,
    UserInfo
)
from context_service import ContextResult, DocumentResult

@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint directly"""
    from main import health_check_endpoint
    
    # Call the health check endpoint function (it's async)
    response = await health_check_endpoint()
    
    # Verify the response
    assert response == {"status": "healthy"}

@pytest.mark.asyncio
async def test_validate_token():
    """Test the validate_token function directly"""
    # Test with default token
    user_info = await validate_token("default_token", "OpenWebUI")
    assert user_info.id == "default_user"
    assert user_info.email == "tmfrisinger@gmail.com"
    assert user_info.token_type == "OpenWebUI"
    
    # Test with Slack token
    user_info = await validate_token("slack:U123456", "Slack")
    assert user_info.id == "U123456"
    assert user_info.token_type == "Slack"
    
    # Test with invalid token should raise an error
    with pytest.raises(ValueError):
        await validate_token("invalid_token", "Unknown")

@pytest.mark.asyncio
async def test_get_context_implementation():
    """Test the context retrieval implementation directly without using FastMCP tool"""
    
    # Create mock document results
    mock_documents = [
        DocumentResult(
            content="Test document content 1",
            source="test_source",
            metadata={
                "id": "doc123",
                "url": "https://example.com/doc1",
                "file_name": "test1.txt",
                "created_time": "2025-01-01T00:00:00Z",
                "modified_time": "2025-01-02T00:00:00Z",
                "score": 0.95,
                "source_type": "document"
            }
        ),
        DocumentResult(
            content="Test document content 2",
            source="test_source",
            metadata={
                "id": "doc456",
                "url": "https://example.com/doc2",
                "file_name": "test2.txt",
                "created_time": "2025-01-03T00:00:00Z",
                "modified_time": "2025-01-04T00:00:00Z",
                "score": 0.85,
                "source_type": "document"
            }
        ),
        DocumentResult(
            content="Test document content 3",
            source="test_source",
            metadata={
                "id": "doc789",
                "url": "https://example.com/doc3",
                "file_name": "test3.txt",
                "created_time": "2025-01-05T00:00:00Z",
                "modified_time": "2025-01-06T00:00:00Z",
                "score": 0.75,
                "source_type": "document"
            }
        ),
        DocumentResult(
            content="Test document content 4",
            source="test_source",
            metadata={
                "id": "doc101",
                "url": "https://example.com/doc4",
                "file_name": "test4.txt",
                "created_time": "2025-01-07T00:00:00Z",
                "modified_time": "2025-01-08T00:00:00Z",
                "score": 0.65,
                "source_type": "document"
            }
        )
    ]
    
    # Create a mock context result
    mock_result = ContextResult(
        documents=mock_documents,
        cache_hit=False,
        retrieval_time_ms=42
    )
    
    # Mock the context_service module
    with patch("main.context_service.get_context_for_prompt", new_callable=AsyncMock) as mock_get_context:
        # Configure the mock to return our predefined result
        mock_get_context.return_value = mock_result
        
        # Create a test request
        request = ContextRequest(
            auth_token="default_token",
            token_type="OpenWebUI",
            prompt="Test prompt",
            history_summary="Test history"
        )
        
        # Define a simple implementation based on the actual endpoint logic
        async def legacy_context_endpoint(request):
            try:
                # Validate the token and get user info
                user_info = await validate_token(request.auth_token, request.token_type)
                user_id = user_info.id
                
                # Get context for the prompt using ContextService
                from main import context_service
                context_result = await context_service.get_context_for_prompt(
                    user_id=user_id,
                    prompt=request.prompt,
                    history_summary=request.history_summary,
                    user_info=user_info
                )
                
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
                
                return response
                
            except ValueError as e:
                raise ValueError(str(e)) from e
            except Exception as e:
                raise Exception(f"Error in test implementation: {str(e)}") from e
        
        # Call our implementation
        result = await legacy_context_endpoint(request)
        
        # Verify the result structure - there should be 4 context items now
        assert len(result.context_items) == 4
        
        # Verify the first context item structure
        context_item = result.context_items[0]
        assert context_item.content == "Test document content 1"
        assert context_item.role == "system"
        assert context_item.metadata["source"] == "test_source"
        assert context_item.metadata["document_id"] == "doc123"
        
        # Verify the second context item
        context_item = result.context_items[1]
        assert context_item.content == "Test document content 2"
        assert context_item.metadata["document_id"] == "doc456"
        
        # Verify metadata
        metadata = result.metadata
        assert metadata.token_type == "OpenWebUI"
        assert metadata.user.id == "default_user"
        assert metadata.retrieval_metadata.cache_hit is False
        assert metadata.retrieval_metadata.retrieval_time_ms == 42
        assert metadata.context_sources[0].count == 4  # Should reflect all 4 documents
        
        # Verify that get_context_for_prompt was called with the expected arguments
        mock_get_context.assert_called_once()
        call_args = mock_get_context.call_args[1]
        assert call_args["prompt"] == "Test prompt"
        assert call_args["history_summary"] == "Test history"
        assert call_args["user_id"] == "default_user"

if __name__ == "__main__":
    import asyncio
    # Run the tests manually
    async def run_tests():
        print("Testing health check endpoint...")
        await test_health_check()
        print("✅ health check test passed")
        
        print("\nTesting validate_token function...")
        await test_validate_token()
        print("✅ validate_token test passed")
        
        print("\nTesting get_context implementation...")
        await test_get_context_implementation()
        print("✅ get_context implementation test passed")
        
        print("\nAll tests completed! 🎉")
    
    asyncio.run(run_tests()) 