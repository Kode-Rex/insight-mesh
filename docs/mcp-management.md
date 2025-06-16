# MCP Server Management with Weave

This document explains how to manage MCP (Model Context Protocol) servers using the Weave CLI, providing a declarative, version-controlled approach to MCP server configuration.

## Overview

The MCP management system allows you to:
- **Store MCP server configurations** in `.weave/config.json` (version controlled)
- **Sync configurations** to LiteLLM database via API
- **Initialize servers** automatically on container startup
- **Manage servers** through simple CLI commands

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ .weave/         │    │ weave CLI        │    │ LiteLLM         │
│ config.json     │───▶│ tool commands    │───▶│ Database        │
│ (mcp_servers)   │    │ (sync/init)      │    │ (runtime)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

1. **Configuration**: MCP servers defined in `.weave/config.json`
2. **Management**: Weave CLI commands to add/remove/list servers
3. **Synchronization**: Push configs to LiteLLM database via API
4. **Initialization**: Automatic sync on container startup

## Configuration Format

MCP servers are stored in the `mcp_servers` section of `.weave/config.json`:

```json
{
  "mcp_servers": {
    "webcat": {
      "url": "http://webcat:8765/mcp",
      "transport": "sse",
      "spec_version": "2024-11-05",
      "description": "WebCat MCP Server - For Web Search",
      "env": {
        "WEBCAT_API_KEY": "${WEBCAT_API_KEY}",
        "SERPER_API_KEY": "${SERPER_API_KEY}"
      }
    }
  }
}
```

### Configuration Fields

- **`url`**: MCP server endpoint URL
- **`transport`**: Transport protocol (`sse` or `stdio`)
- **`spec_version`**: MCP specification version
- **`description`**: Human-readable description
- **`env`**: Environment variables (supports `${VAR}` substitution)

## CLI Commands

### Server Management

#### Add MCP Server
```bash
# Add a new MCP server
weave tool server add webcat http://webcat:8765/mcp \
  --description "Web search tool" \
  --env WEBCAT_API_KEY=secret \
  --env SERPER_API_KEY=another-secret

# Add with custom transport and spec version
weave tool server add filesystem http://filesystem:8766/mcp \
  --transport sse \
  --spec-version 2024-11-05 \
  --description "Filesystem access"
```

#### List MCP Servers
```bash
# List all configured servers
weave tool server list

# List with detailed information
weave tool server list --verbose
```

#### Remove MCP Server
```bash
# Remove a server (with confirmation)
weave tool server remove webcat

# Remove without confirmation
weave tool server remove webcat --yes
```

### Synchronization

#### Sync to LiteLLM
```bash
# Sync all servers to LiteLLM database
weave tool sync

# Preview what would be synced (dry run)
weave tool sync --dry-run

# Sync with custom LiteLLM URL
weave tool sync --litellm-url http://localhost:4000

# Sync with custom API key
weave tool sync --api-key sk-custom-key-123
```

#### Initialize on Startup
```bash
# Initialize MCP servers (for container startup)
weave tool init

# Wait for LiteLLM service to be ready first
weave tool init --wait-for-service

# Initialize with custom settings
weave tool init \
  --litellm-url http://litellm:4000 \
  --api-key sk-litellm-master-key-123456
```

## Container Integration

### Automatic Initialization

For automatic MCP server initialization on container startup, use the provided init script:

```bash
# Run the init script
./scripts/init-mcp-servers.sh

# With custom environment variables
LITELLM_URL=http://localhost:4000 \
WAIT_FOR_SERVICE=true \
./scripts/init-mcp-servers.sh
```

### Docker Compose Integration

Add the init script to your service's startup command:

```yaml
services:
  your-service:
    image: your-image
    command: >
      sh -c "
        ./scripts/init-mcp-servers.sh &&
        your-main-command
      "
    environment:
      - LITELLM_URL=http://litellm:4000
      - LITELLM_API_KEY=sk-litellm-master-key-123456
      - WAIT_FOR_SERVICE=true
```

### Environment Variables

The init script supports these environment variables:

- **`LITELLM_URL`**: LiteLLM proxy URL (default: `http://litellm:4000`)
- **`LITELLM_API_KEY`**: API key (default: `sk-litellm-master-key-123456`)
- **`WAIT_FOR_SERVICE`**: Wait for LiteLLM to be ready (default: `true`)
- **`MAX_RETRIES`**: Maximum retry attempts (default: `5`)
- **`RETRY_DELAY`**: Delay between retries in seconds (default: `10`)
- **`PROJECT_ROOT`**: Project root directory (optional)

## Workflow Examples

### Adding a New MCP Server

1. **Add to weave config**:
   ```bash
   weave tool server add github http://github-mcp:8767/mcp \
     --description "GitHub integration" \
     --env GITHUB_TOKEN=ghp_your_token
   ```

2. **Sync to LiteLLM**:
   ```bash
   weave tool sync
   ```

3. **Verify in LiteLLM**:
   ```bash
   curl -H "Authorization: Bearer sk-litellm-master-key-123456" \
     http://localhost:4000/mcp/tools/list
   ```

### Updating Server Configuration

1. **Remove old server**:
   ```bash
   weave tool server remove webcat --yes
   ```

2. **Add updated server**:
   ```bash
   weave tool server add webcat http://webcat:8765/mcp \
     --description "Updated web search tool" \
     --env WEBCAT_API_KEY=new-secret
   ```

3. **Sync changes**:
   ```bash
   weave tool sync
   ```

### Development Workflow

1. **Preview changes**:
   ```bash
   weave tool sync --dry-run
   ```

2. **Apply changes**:
   ```bash
   weave tool sync
   ```

3. **Test tools**:
   ```bash
   curl -X POST \
     -H "Authorization: Bearer sk-litellm-master-key-123456" \
     -H "Content-Type: application/json" \
     -d '{"name": "search", "arguments": {"query": "test"}}' \
     http://localhost:4000/mcp/tools/call
   ```

## Troubleshooting

### Common Issues

#### MCP Server Not Found
```bash
# Check if server is in weave config
weave tool server list

# Check if server is in LiteLLM database
curl -H "Authorization: Bearer sk-litellm-master-key-123456" \
  http://localhost:4000/v1/mcp/server
```

#### Sync Failures
```bash
# Check LiteLLM connectivity
curl http://localhost:4000/mcp/enabled

# Check API key
curl -H "Authorization: Bearer sk-litellm-master-key-123456" \
  http://localhost:4000/v1/mcp/server

# Run sync with verbose output
weave tool sync --dry-run
```

#### Service Not Ready
```bash
# Check service status
weave service status litellm

# Wait for service manually
./scripts/init-mcp-servers.sh --help

# Check logs
weave logs litellm
```

### Debug Commands

```bash
# List all MCP tools available in LiteLLM
curl -H "Authorization: Bearer sk-litellm-master-key-123456" \
  http://localhost:4000/mcp/tools/list

# Check MCP server health
curl -X POST \
  -H "Authorization: Bearer sk-litellm-master-key-123456" \
  -H "Content-Type: application/json" \
  -d '{"name": "health_check", "arguments": {}}' \
  http://localhost:4000/mcp/tools/call

# View weave config
cat .weave/config.json | jq .mcp_servers
```

## Migration from Manual Configuration

If you have manually configured MCP servers in LiteLLM:

1. **Export existing servers** (if needed):
   ```bash
   curl -H "Authorization: Bearer sk-litellm-master-key-123456" \
     http://localhost:4000/v1/mcp/server > existing-servers.json
   ```

2. **Add servers to weave config**:
   ```bash
   weave tool server add server-name http://server-url/mcp \
     --description "Migrated server"
   ```

3. **Sync to replace manual configs**:
   ```bash
   weave tool sync
   ```

## Best Practices

1. **Version Control**: Always commit `.weave/config.json` changes
2. **Environment Variables**: Use `${VAR}` syntax for secrets
3. **Descriptive Names**: Use clear, descriptive server names
4. **Testing**: Use `--dry-run` before applying changes
5. **Documentation**: Document custom servers and their purposes
6. **Monitoring**: Check sync status after deployments

## Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Sync MCP Servers
  run: |
    weave tool sync --litellm-url ${{ secrets.LITELLM_URL }}
  env:
    LITELLM_API_KEY: ${{ secrets.LITELLM_API_KEY }}
``` 