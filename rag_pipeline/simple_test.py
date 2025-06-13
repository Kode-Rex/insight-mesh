import sys
import os

print('=== Testing Post Response Hook Import ===')
try:
    import post_response_hook as hook_module
    print('✓ Module imported successfully')
    print(f'✓ Has mcp_tool_handler_instance: {hasattr(hook_module, "mcp_tool_handler_instance")}')
    print(f'✓ Has MCPToolHandler: {hasattr(hook_module, "MCPToolHandler")}')
    print(f'✓ Instance type: {type(hook_module.mcp_tool_handler_instance)}')
    
    # Test the instance
    instance = hook_module.mcp_tool_handler_instance
    print(f'✓ Instance created: {instance}')
    print(f'✓ Instance has async_post_call_success_hook: {hasattr(instance, "async_post_call_success_hook")}')
    
except Exception as e:
    print(f'✗ Import failed: {e}')
    import traceback
    traceback.print_exc()

print('\n=== Testing from rag_pipeline.post_response_hook ===')
try:
    from rag_pipeline.post_response_hook import mcp_tool_handler_instance, MCPToolHandler
    print('✓ Direct import successful')
    print(f'✓ Instance type: {type(mcp_tool_handler_instance)}')
    print(f'✓ Is MCPToolHandler: {isinstance(mcp_tool_handler_instance, MCPToolHandler)}')
except Exception as e:
    print(f'✗ Direct import failed: {e}')
    import traceback
    traceback.print_exc() 