# MCP Registry

The MCP Registry is a lightweight FastAPI service that provides read-only API access to MCP (Model Context Protocol) server configurations stored in `.weave/config.json`.

## Purpose

This service acts as a registry/catalog of available MCP servers, allowing other services to:
- Discover available MCP servers
- Filter servers by scope (rag, agent, all)
- Get server configurations including URLs, authentication, and environment variables

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Commands  │    │   MCP Registry   │    │  Configuration  │
│  (Write Only)   │───▶│   (Read-only)    │───▶│      File       │
│                 │    │                  │    │ .weave/config.json │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               ▲
                               │ HTTP API calls  
                    ┌──────────────────┐
                    │  RAG Pipeline    │
                    │ & Other Services │
                    └──────────────────┘
```

## API Endpoints

- `GET /health` - Health check
- `GET /servers` - Get all MCP servers
- `GET /servers/rag` - Get servers with 'rag' or 'all' scope
- `GET /servers/scope/{scope}` - Get servers filtered by specific scope
- `GET /servers/{name}` - Get specific server configuration
- `GET /config` - Get full configuration with metadata

## Usage

### Development
```bash
python mcp_registry/app.py --host 0.0.0.0 --port 8080
```

### Docker
```bash
docker-compose up mcp-registry
```

### Access
- Direct: http://localhost:8888
- Through Caddy: http://localhost:8080/mcp

## Configuration

The service reads MCP server configurations from `.weave/config.json`. Use the Weave CLI to manage servers:

```bash
# Add a server
weave tool server add webcat http://webcat:8765/mcp --scope rag

# List servers
weave tool server list

# Remove a server
weave tool server remove webcat

# Test the registry
weave tool test-registry
```

## Features

- **Automatic Reloading**: Configuration file changes are detected automatically
- **Scope Filtering**: Filter servers by intended use (rag, agent, all)
- **Health Monitoring**: Built-in health checks for Docker integration
- **Fast Performance**: Lightweight FastAPI service optimized for read operations
- **Docker Integration**: Seamlessly integrated with docker-compose stack 