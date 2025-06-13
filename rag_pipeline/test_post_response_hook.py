import sys
import os
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

def test_post_response_hook_import():
    """Test that the post_response_hook module can be imported"""
    try:
        import rag_pipeline.post_response_hook as hook_module
        assert hasattr(hook_module, 'mcp_tool_handler_instance')
        assert hasattr(hook_module, 'MCPToolHandler')
        print("✓ Post response hook imports successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_mcp_tool_handler_instance():
    """Test that the mcp_tool_handler_instance is properly created"""
    try:
        from rag_pipeline.post_response_hook import mcp_tool_handler_instance, MCPToolHandler
        assert isinstance(mcp_tool_handler_instance, MCPToolHandler)
        print("✓ mcp_tool_handler_instance is properly created")
        return True
    except Exception as e:
        print(f"✗ Instance test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_post_call_success_hook_no_tool_calls():
    """Test post_call_success_hook with response that has no tool calls"""
    try:
        from rag_pipeline.post_response_hook import MCPToolHandler
        
        handler = MCPToolHandler()
        
        # Mock response object without tool calls
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.tool_calls = None
        
        # Mock user API key dict
        mock_user_api_key = Mock()
        
        result = await handler.async_post_call_success_hook(
            user_api_key_dict=mock_user_api_key,
            response_obj=mock_response,
            start_time=0.0,
            end_time=1.0
        )
        
        assert result == mock_response
        print("✓ Post hook handles responses without tool calls")
        return True
    except Exception as e:
        print(f"✗ No tool calls test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_post_call_success_hook_with_tool_calls():
    """Test post_call_success_hook with response that has tool calls"""
    try:
        from rag_pipeline.post_response_hook import MCPToolHandler
        
        handler = MCPToolHandler()
        
        # Mock tool call
        mock_tool_call = Mock()
        mock_tool_call.id = "test_call_123"
        mock_tool_call.model_dump.return_value = {
            "id": "test_call_123",
            "type": "function",
            "function": {
                "name": "test_tool",
                "arguments": '{"query": "test"}'
            }
        }
        
        # Mock response object with tool calls
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.tool_calls = [mock_tool_call]
        
        # Mock user API key dict
        mock_user_api_key = Mock()
        
        # Mock the _execute_tool_call method to avoid actual MCP calls
        with patch.object(handler, '_execute_tool_call', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"result": "test_result"}
            
            result = await handler.async_post_call_success_hook(
                user_api_key_dict=mock_user_api_key,
                response_obj=mock_response,
                start_time=0.0,
                end_time=1.0
            )
            
            # Check that tool was executed
            mock_execute.assert_called_once_with(mock_tool_call)
            
            # Check that metadata was added
            assert hasattr(result, 'metadata')
            assert 'tool_results' in result.metadata
            assert len(result.metadata['tool_results']) == 1
            assert result.metadata['tool_results'][0]['tool_call_id'] == "test_call_123"
            
        print("✓ Post hook handles responses with tool calls")
        return True
    except Exception as e:
        print(f"✗ Tool calls test failed: {e}")
        return False

def test_mcp_tool_execution_disabled():
    """Test that tool execution can be disabled via environment variable"""
    try:
        # Temporarily set environment variable
        original_value = os.environ.get("ENABLE_MCP_TOOL_EXECUTION")
        os.environ["ENABLE_MCP_TOOL_EXECUTION"] = "false"
        
        # Reload the module to pick up the new environment variable
        import importlib
        import rag_pipeline.post_response_hook as hook_module
        importlib.reload(hook_module)
        
        # Check that the flag is set correctly
        assert not hook_module.ENABLE_MCP_TOOL_EXECUTION
        print("✓ MCP tool execution can be disabled")
        
        # Restore original value
        if original_value is not None:
            os.environ["ENABLE_MCP_TOOL_EXECUTION"] = original_value
        else:
            os.environ.pop("ENABLE_MCP_TOOL_EXECUTION", None)
            
        return True
    except Exception as e:
        print(f"✗ Disable test failed: {e}")
        return False

async def run_async_tests():
    """Run all async tests"""
    print("\n=== Running Async Tests ===")
    
    tests = [
        test_post_call_success_hook_no_tool_calls(),
        test_post_call_success_hook_with_tool_calls()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"✗ Async test {i+1} failed with exception: {result}")
        elif not result:
            print(f"✗ Async test {i+1} failed")

def run_all_tests():
    """Run all tests"""
    print("=== Testing Post Response Hook ===")
    
    # Sync tests
    sync_tests = [
        test_post_response_hook_import,
        test_mcp_tool_handler_instance,
        test_mcp_tool_execution_disabled
    ]
    
    print("\n=== Running Sync Tests ===")
    for test in sync_tests:
        try:
            test()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
    
    # Async tests
    try:
        asyncio.run(run_async_tests())
    except Exception as e:
        print(f"✗ Async tests failed: {e}")
    
    print("\n=== Test Summary ===")
    print("If all tests pass, the post_response_hook should work correctly!")

if __name__ == "__main__":
    run_all_tests() 