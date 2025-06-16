#!/usr/bin/env python3
"""
MCP Configuration Registry Server

This lightweight server provides read-only API access to MCP server configurations.
It acts as a registry/catalog of available MCP servers, reading from the configuration
file while write/delete/update operations go directly to the file via CLI commands.

Usage:
    python mcp_registry/app.py [--host HOST] [--port PORT] [--config CONFIG]
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp_registry")

class MCPServerConfig(BaseModel):
    """Model for MCP server configuration"""
    url: str
    transport: str = "sse"
    spec_version: str = "2024-11-05"
    description: str = ""
    scope: str = "all"
    env: Dict[str, str] = {}

class MCPConfigResponse(BaseModel):
    """Response model for MCP configuration"""
    servers: Dict[str, MCPServerConfig]
    config_path: str
    last_modified: Optional[float] = None

class MCPRegistry:
    """Registry class for reading MCP configurations"""
    
    def __init__(self, config_path: str = ".weave/config.json"):
        self.config_path = Path(config_path)
        self._cached_config = None
        self._last_modified = None
        
    def _get_file_modified_time(self) -> Optional[float]:
        """Get the last modified time of the config file"""
        try:
            return self.config_path.stat().st_mtime
        except (OSError, FileNotFoundError):
            return None
    
    def _should_reload_config(self) -> bool:
        """Check if config should be reloaded based on file modification time"""
        current_modified = self._get_file_modified_time()
        if current_modified is None:
            return False
        
        if self._last_modified is None or current_modified > self._last_modified:
            self._last_modified = current_modified
            return True
        
        return False
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded config from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}")
            raise HTTPException(status_code=404, detail="Configuration file not found")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise HTTPException(status_code=500, detail="Invalid configuration file format")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise HTTPException(status_code=500, detail="Error loading configuration")
    
    def get_mcp_servers(self, scope_filter: Optional[List[str]] = None) -> Dict[str, MCPServerConfig]:
        """Get MCP server configurations, optionally filtered by scope"""
        # Check if we need to reload config
        if self._cached_config is None or self._should_reload_config():
            self._cached_config = self._load_config()
        
        mcp_servers = self._cached_config.get("mcp_servers", {})
        
        # Convert to MCPServerConfig objects and filter by scope if needed
        result = {}
        for name, config in mcp_servers.items():
            server_config = MCPServerConfig(**config)
            
            # Apply scope filter if provided
            if scope_filter is None or server_config.scope in scope_filter:
                result[name] = server_config
        
        logger.info(f"Retrieved {len(result)} MCP servers" + 
                   (f" (filtered by scope: {scope_filter})" if scope_filter else ""))
        return result
    
    def get_server_by_name(self, name: str) -> Optional[MCPServerConfig]:
        """Get a specific MCP server configuration by name"""
        servers = self.get_mcp_servers()
        return servers.get(name)
    
    def get_servers_by_scope(self, scope: str) -> Dict[str, MCPServerConfig]:
        """Get MCP servers filtered by specific scope"""
        return self.get_mcp_servers(scope_filter=[scope])
    
    def get_rag_servers(self) -> Dict[str, MCPServerConfig]:
        """Get MCP servers with 'rag' or 'all' scope (used by LiteLLM integration)"""
        return self.get_mcp_servers(scope_filter=["rag", "all"])
    
    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint"""
        try:
            config_exists = self.config_path.exists()
            last_modified = self._get_file_modified_time()
            
            return {
                "status": "healthy" if config_exists else "degraded",
                "config_file": str(self.config_path),
                "config_exists": config_exists,
                "last_modified": last_modified,
                "cached_config_loaded": self._cached_config is not None
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Global registry instance
registry = None

def get_registry() -> MCPRegistry:
    """Dependency to get the registry instance"""
    global registry
    if registry is None:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    return registry

# FastAPI app
app = FastAPI(
    title="MCP Configuration Registry",
    description="Read-only API for MCP server configurations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["GET"],  # Only read operations
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize the registry on startup"""
    global registry
    config_path = os.environ.get("MCP_CONFIG_PATH", ".weave/config.json")
    registry = MCPRegistry(config_path)
    logger.info(f"MCP Registry started with config path: {config_path}")

@app.get("/health")
async def health_check(reg: MCPRegistry = Depends(get_registry)):
    """Health check endpoint"""
    return reg.health_check()

@app.get("/servers", response_model=Dict[str, MCPServerConfig])
async def get_all_servers(reg: MCPRegistry = Depends(get_registry)):
    """Get all MCP server configurations"""
    return reg.get_mcp_servers()

@app.get("/servers/rag", response_model=Dict[str, MCPServerConfig])
async def get_rag_servers(reg: MCPRegistry = Depends(get_registry)):
    """Get MCP servers with 'rag' or 'all' scope (used by LiteLLM)"""
    return reg.get_rag_servers()

@app.get("/servers/scope/{scope}", response_model=Dict[str, MCPServerConfig])
async def get_servers_by_scope(scope: str, reg: MCPRegistry = Depends(get_registry)):
    """Get MCP servers filtered by specific scope"""
    return reg.get_servers_by_scope(scope)

@app.get("/servers/{name}", response_model=MCPServerConfig)
async def get_server_by_name(name: str, reg: MCPRegistry = Depends(get_registry)):
    """Get a specific MCP server configuration by name"""
    server = reg.get_server_by_name(name)
    if server is None:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not found")
    return server

@app.get("/config", response_model=MCPConfigResponse)
async def get_full_config(reg: MCPRegistry = Depends(get_registry)):
    """Get the full MCP configuration"""
    servers = reg.get_mcp_servers()
    return MCPConfigResponse(
        servers=servers,
        config_path=str(reg.config_path),
        last_modified=reg._last_modified
    )

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Configuration Registry Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--config", default=".weave/config.json", help="Path to config file")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    # Set config path in environment for the app
    os.environ["MCP_CONFIG_PATH"] = args.config
    
    logger.info(f"Starting MCP Registry Server on {args.host}:{args.port}")
    logger.info(f"Config file: {args.config}")
    
    uvicorn.run(
        "mcp_registry.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main() 