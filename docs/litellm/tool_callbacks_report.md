# LiteLLM Tool Callbacks Configuration Report

This report details the configuration of tool callbacks in LiteLLM, with a specific focus on integrating a `web_search` tool. The analysis is based on the LiteLLM codebase and available documentation.

## 1. Introduction to Callbacks and Tools in LiteLLM

LiteLLM provides robust mechanisms for interacting with Large Language Models (LLMs), including support for tools (often referred to as function calling). It also offers a callback system for logging, monitoring, and custom processing at various stages of an LLM call.

It's important to distinguish between:
*   **Event-driven Callbacks:** These are functions or integrations (e.g., Langfuse, Sentry) triggered by events like successful or failed LLM calls, or before an API call is made. They are primarily for logging, monitoring, or modifying data.
*   **Tool/Function Calling:** This refers to the ability of an LLM to request the invocation of an external tool or function to gather more information or perform an action. LiteLLM facilitates this by passing tool schemas to the LLM and returning the LLM's request to call a tool. The *execution* of these tools can be handled in different ways.

## 2. General Event-Driven Callback Configuration

LiteLLM allows setting various callbacks through `litellm_settings` in the configuration file or directly in code. These are primarily for observability and custom processing hooks.

Key callback settings include:
*   `litellm.input_callback` or `litellm_settings.input_callback`: For processing data before it's sent to the LLM.
*   `litellm.success_callback` or `litellm_settings.success_callback`: Triggered after a successful LLM call.
*   `litellm.failure_callback` or `litellm_settings.failure_callback`: Triggered after a failed LLM call.
*   `litellm.callbacks`: A list of custom logger classes that can implement various hooks like `log_pre_api_call`, `log_post_api_call`, `async_log_success_event`, etc.

**Example (from `docs/my-website/docs/observability/custom_callback.md`):**
```python
import litellm
from litellm.integrations.custom_logger import CustomLogger

class MyCustomHandler(CustomLogger):
    def log_success_event(self, kwargs, response_obj, start_time, end_time): 
        print(f"On Success")

customHandler = MyCustomHandler()
litellm.callbacks = [customHandler]

# Or for simpler function-based callbacks:
def my_success_logger(kwargs, completion_response, start_time, end_time):
    print("LLM call was successful!")

litellm.success_callback = [my_success_logger]
```

In a `config.yaml` for the LiteLLM proxy:
```yaml
litellm_settings:
  success_callback: ["langfuse"] # Built-in integration
  failure_callback: ["sentry"]
  # For custom callback modules:
  # callbacks: ["your_module.your_custom_handler_instance"] 
```
These callbacks are primarily for logging and event handling, not for defining the execution logic of tools requested by an LLM.

## 3. Configuring and Using Tools (Function Calling)

When an LLM needs to use a tool, it's typically configured in two main parts:
1.  **Tool Definition/Schema:** Informing the LLM about available tools (name, description, parameters). This is usually done in a format compatible with the LLM provider (e.g., OpenAI's function calling schema).
2.  **Tool Execution:** Handling the LLM's request to call a tool and returning the result.

### 3.1. Web Search Tool

LiteLLM supports web search capabilities, primarily through specific models that have this functionality built-in or through dedicated endpoints.

#### 3.1.1. Built-in Web Search with OpenAI Models
As per `docs/my-website/docs/completion/web_search.md`, certain OpenAI models (e.g., `openai/gpt-4o-search-preview`) inherently support web search.

**SDK Usage:**
```python
from litellm import completion

response = completion(
    model="openai/gpt-4o-search-preview",
    messages=[{"role": "user", "content": "What was a positive news story from today?"}],
    # Optional: customize search context size
    # web_search_options={"search_context_size": "low"} # "low", "medium" (default), "high"
)
```

**Proxy Usage (`config.yaml`):**
```yaml
model_list:
  - model_name: gpt-4o-search-preview # Alias for clients
    litellm_params:
      model: openai/gpt-4o-search-preview
      api_key: os.environ/OPENAI_API_KEY
```
Clients then call the `gpt-4o-search-preview` model alias.

#### 3.1.2. Web Search via `/responses` Endpoint
The `/responses` endpoint (experimental) also supports enabling web search for compatible models.

**SDK Usage:**
```python
from litellm import responses

response = responses(
    model="openai/gpt-4o",
    input=[{"role": "user", "content": "What was a positive news story from today?"}],
    tools=[{"type": "web_search_preview"}] # Enables web search
)
```
This method uses a specific tool type `web_search_preview`. The cost tracking for such built-in tools is handled by LiteLLM, as seen in `litellm/litellm_core_utils/llm_cost_calc/tool_call_cost_tracking.py`.

### 3.2. Custom Tools and `tool_callbacks`

For custom tools or tools not natively integrated into a model, the configuration approach differs.

**User's Provided Configuration Snippet:**
```yaml
litellm_settings:
  # ... other settings
  tool_callbacks: # This specific key for defining tool execution endpoints
    web_search: <user-mention type="webPage">Web-http://webcat:8765/api/v1/search#</user-mention>

# Tools configuration (OpenAI schema)
tools:
  - type: function
    function:
      name: web_search
      description: "Search the web..."
      parameters:
        # ... schema ...
```

**Analysis:**

1.  **`tools` (OpenAI Schema):** The `tools` section correctly defines the schema for the `web_search` function. This definition is what LiteLLM passes to the LLM, enabling it to understand when and how to request this tool. This part is standard for function calling.

2.  **`litellm_settings.tool_callbacks`:**
    *   The direct use of `litellm_settings.tool_callbacks` to map a tool name (`web_search`) to an HTTP execution endpoint (e.g., `http://webcat:8765/api/v1/search`) is **not a prominently documented standard feature** for LiteLLM to *itself* execute arbitrary HTTP-based tools for all scenarios (SDK or Proxy).
    *   The primary `callbacks` in `litellm_settings` (like `success_callback`, `failure_callback`, or custom logger classes via `litellm.callbacks`) are designed for logging, monitoring, or data transformation around an LLM call, not for LiteLLM to directly execute a tool by calling an external URL defined this way.
    *   If such a `tool_callbacks` mechanism exists for direct HTTP execution by LiteLLM (outside of MCP or client-side handling), its usage and scope are not clearly detailed in the primary documentation paths explored (`config_settings.md`, `callbacks.md`, `custom_callback.md`).
    *   The file `tests/logging_callback_tests/test_unit_tests_init_callbacks.py` and `litellm/litellm_core_utils/litellm_logging.py` focus on the event-driven callback system.

**How Custom Tool Execution is Typically Handled:**

*   **Client-Side Execution (SDK):** When using `litellm.completion()` directly in Python, if the LLM returns a tool call request, the calling application is responsible for:
    1.  Receiving the tool call request from the `completion` response.
    2.  Executing the actual `web_search` function (e.g., by making an HTTP request to `http://webcat:8765/api/v1/search`).
    3.  Sending the tool's output back to the LLM in a subsequent `completion` call.

*   **LiteLLM Proxy with MCP (Model Context Protocol):** For more integrated tool management, especially with the LiteLLM Proxy, the Model Context Protocol (MCP) is the recommended approach for custom or external tools.
    *   As per `docs/my-website/docs/mcp.md`, you can define `mcp_servers` in your `config.yaml`. These are external servers that host your tools.
        ```yaml
        # config.yaml
        mcp_servers:
          my_tool_server: # An arbitrary name for your tool server
            url: "http://webcat:8765" # Base URL of your tool server (if it follows MCP spec)
        ```
    *   If `http://webcat:8765` is an MCP-compliant server, LiteLLM Proxy can interact with it.
    *   Alternatively, `mcp_tools` can be defined in the config, pointing to specific handlers as shown in `litellm/proxy/_experimental/mcp_server/tool_registry.py`. These handlers would contain the logic to call the web search URL.
        ```python
        # litellm/proxy/_experimental/mcp_server/tool_registry.py
        # Example of how mcp_tools might be loaded (conceptual)
        # config.yaml
        # mcp_tools:
        #   - name: "web_search"
        #     description: "Searches the web."
        #     input_schema: { ... }
        #     handler: "my_module.my_web_search_handler" # Python function to call the webcat URL
        ```
    *   The proxy server (`litellm/proxy/proxy_server.py`) initializes and uses `global_mcp_tool_registry` and `global_mcp_server_manager` based on these configurations.

## 4. Correct Way to Configure Web Search

*   **Using OpenAI's Built-in Search:**
    *   For SDK: Call `litellm.completion(model="openai/gpt-4o-search-preview", ...)` or `litellm.responses(..., tools=[{"type": "web_search_preview"}])`.
    *   For Proxy: Define `openai/gpt-4o-search-preview` in `model_list`.

*   **Implementing a Custom `web_search` Tool (callable by any LLM via function calling):**
    1.  **Define Tool Schema:** Your `tools` definition is correct for this.
        ```yaml
        # In your litellm.completion call or proxy config for a model
        tools:
          - type: function
            function:
              name: web_search
              description: "Search the web for real-time information..."
              parameters:
                type: object
                properties:
                  search_term:
                    type: string
                    description: "The search term to look up on the web."
                required:
                  - search_term
        ```
    2.  **Handle Execution:**
        *   **SDK:** Your application code receives the `tool_calls` from `litellm.completion()`. Then, your code explicitly calls `http://webcat:8765/api/v1/search` with the arguments and passes the result back to the LLM.
        *   **Proxy (Advanced - MCP):** If `http://webcat:8765` is an MCP-compliant tool server, register it under `mcp_servers`. If it's a simple HTTP endpoint and you want the proxy to manage it, you'd typically use the `mcp_tools` definition with a Python handler function that makes the HTTP request. The `tool_callbacks` key in `litellm_settings` as shown in the user's example is not the standard documented method for this proxy-side HTTP execution.

## 5. Conclusion

*   The `tools` definition provided by the user is the correct way to define the *schema* of a custom `web_search` tool for LLMs.
*   The `litellm_settings.tool_callbacks` mapping a tool name directly to an HTTP URL for execution by LiteLLM (SDK/Proxy) is **not** the standard documented approach.
*   For OpenAI models with built-in web search, use the specific model names (e.g., `openai/gpt-4o-search-preview`) or the `web_search_preview` tool type with the `/responses` endpoint.
*   For custom tools like a `web_search` function that calls an external API:
    *   If using LiteLLM SDK, the client application handles the execution.
    *   If using LiteLLM Proxy and wanting the proxy to manage/call the tool, the MCP (`mcp_servers` or `mcp_tools` with handlers) is the more appropriate and documented mechanism.
*   General callbacks (`success_callback`, `litellm.callbacks`, etc.) are for logging, monitoring, and event-driven processing, not for defining tool execution endpoints.

The user's configuration for `litellm_settings.callbacks: rag_pipeline.pre_request_hook.rag_handler_instance` is a standard way to use the event-driven callback system, assuming `rag_handler_instance` is an instance of a `CustomLogger` or a compatible callable. This is separate from how the `web_search` tool itself would be executed.
