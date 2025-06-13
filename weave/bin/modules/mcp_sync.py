#!/usr/bin/env python

import json
import time
import requests
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .mcp_config import get_mcp_servers_from_config

console = Console()

def wait_for_litellm_service(url: str, timeout: int = 60, interval: int = 5) -> bool:
    """Wait for LiteLLM service to be ready"""
    console.print(f"[blue]🔄 Waiting for LiteLLM service at {url}...[/blue]")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                console.print(f"[green]✅ LiteLLM service is ready[/green]")
                return True
        except requests.exceptions.RequestException:
            pass
        
        console.print(f"[yellow]⏳ Service not ready, waiting {interval}s...[/yellow]")
        time.sleep(interval)
    
    console.print(f"[red]❌ Timeout waiting for LiteLLM service after {timeout}s[/red]")
    return False

def get_existing_mcp_servers(litellm_url: str, api_key: str) -> List[Dict[str, Any]]:
    """Get existing MCP servers from LiteLLM database"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{litellm_url}/v1/mcp/server", headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error fetching existing MCP servers: {e}[/red]")
        return []

def create_mcp_server_in_litellm(
    litellm_url: str,
    api_key: str,
    server_name: str,
    server_config: Dict[str, Any]
) -> bool:
    """Create an MCP server in LiteLLM database"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert weave config format to LiteLLM format
        litellm_config = {
            "server_name": server_name,
            "url": server_config["url"],
            "description": server_config.get("description", f"MCP server: {server_name}"),
            "env": server_config.get("env", {}),
            "transport": server_config.get("transport", "sse"),
            "spec_version": server_config.get("spec_version", "2024-11-05")
        }
        
        response = requests.post(
            f"{litellm_url}/v1/mcp/server",
            headers=headers,
            json=litellm_config,
            timeout=10
        )
        response.raise_for_status()
        
        console.print(f"[green]✅ Created MCP server '{server_name}' in LiteLLM[/green]")
        return True
        
    except requests.exceptions.RequestException as e:
        console.print(f"[red]❌ Error creating MCP server '{server_name}': {e}[/red]")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                console.print(f"[red]Error details: {error_detail}[/red]")
            except:
                console.print(f"[red]Response: {e.response.text}[/red]")
        return False

def update_mcp_server_in_litellm(
    litellm_url: str,
    api_key: str,
    server_id: str,
    server_name: str,
    server_config: Dict[str, Any]
) -> bool:
    """Update an existing MCP server in LiteLLM database"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert weave config format to LiteLLM format
        litellm_config = {
            "server_id": server_id,
            "server_name": server_name,
            "url": server_config["url"],
            "description": server_config.get("description", f"MCP server: {server_name}"),
            "env": server_config.get("env", {}),
            "transport": server_config.get("transport", "sse"),
            "spec_version": server_config.get("spec_version", "2024-11-05")
        }
        
        response = requests.put(
            f"{litellm_url}/v1/mcp/server",
            headers=headers,
            json=litellm_config,
            timeout=10
        )
        response.raise_for_status()
        
        console.print(f"[green]✅ Updated MCP server '{server_name}' in LiteLLM[/green]")
        return True
        
    except requests.exceptions.RequestException as e:
        console.print(f"[red]❌ Error updating MCP server '{server_name}': {e}[/red]")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                console.print(f"[red]Error details: {error_detail}[/red]")
            except:
                console.print(f"[red]Response: {e.response.text}[/red]")
        return False

def delete_mcp_server_in_litellm(litellm_url: str, api_key: str, server_id: str, server_name: str) -> bool:
    """Delete an MCP server from LiteLLM database"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.delete(
            f"{litellm_url}/v1/mcp/server/{server_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        console.print(f"[green]✅ Deleted MCP server '{server_name}' from LiteLLM[/green]")
        return True
        
    except requests.exceptions.RequestException as e:
        console.print(f"[red]❌ Error deleting MCP server '{server_name}': {e}[/red]")
        return False

def sync_mcp_servers_to_litellm(
    litellm_url: str,
    api_key: str,
    dry_run: bool = False,
    verbose: bool = False
) -> bool:
    """Sync MCP servers from weave config to LiteLLM database"""
    
    # Get servers from weave config
    weave_servers = get_mcp_servers_from_config()
    
    if not weave_servers:
        console.print("[yellow]No MCP servers configured in weave config[/yellow]")
        return True
    
    if dry_run:
        console.print("[bold blue]🔍 DRY RUN - Showing what would be synced:[/bold blue]")
        console.print()
    
    # Get existing servers from LiteLLM
    existing_servers = get_existing_mcp_servers(litellm_url, api_key)
    existing_by_name = {server.get("server_name", ""): server for server in existing_servers}
    
    if verbose or dry_run:
        console.print(f"[blue]📋 Weave config servers: {len(weave_servers)}[/blue]")
        console.print(f"[blue]📋 LiteLLM database servers: {len(existing_servers)}[/blue]")
        console.print()
    
    success = True
    
    # Create/update servers from weave config
    for server_name, server_config in weave_servers.items():
        if dry_run:
            if server_name in existing_by_name:
                console.print(f"[yellow]🔄 Would update: {server_name}[/yellow]")
            else:
                console.print(f"[green]➕ Would create: {server_name}[/green]")
            
            if verbose:
                console.print(f"  URL: {server_config.get('url')}")
                console.print(f"  Transport: {server_config.get('transport', 'sse')}")
                console.print(f"  Description: {server_config.get('description', 'N/A')}")
                env_vars = server_config.get('env', {})
                if env_vars:
                    console.print(f"  Environment: {len(env_vars)} variables")
                console.print()
        else:
            if server_name in existing_by_name:
                # Update existing server
                existing_server = existing_by_name[server_name]
                server_id = existing_server.get("server_id")
                if server_id:
                    result = update_mcp_server_in_litellm(
                        litellm_url, api_key, server_id, server_name, server_config
                    )
                    success &= result
                else:
                    console.print(f"[yellow]⚠️  Server '{server_name}' exists but has no ID, skipping update[/yellow]")
            else:
                # Create new server
                result = create_mcp_server_in_litellm(
                    litellm_url, api_key, server_name, server_config
                )
                success &= result
    
    # Remove servers that exist in LiteLLM but not in weave config
    for existing_server in existing_servers:
        server_name = existing_server.get("server_name", "")
        server_id = existing_server.get("server_id", "")
        
        if server_name and server_name not in weave_servers:
            if dry_run:
                console.print(f"[red]🗑️  Would delete: {server_name}[/red]")
            else:
                if server_id:
                    result = delete_mcp_server_in_litellm(litellm_url, api_key, server_id, server_name)
                    success &= result
                else:
                    console.print(f"[yellow]⚠️  Server '{server_name}' has no ID, cannot delete[/yellow]")
    
    return success

def init_mcp_servers(
    litellm_url: str,
    api_key: str,
    wait_for_service: bool = False,
    verbose: bool = False
) -> bool:
    """Initialize MCP servers on startup"""
    
    if wait_for_service:
        if not wait_for_litellm_service(litellm_url):
            return False
    
    console.print("[blue]🚀 Initializing MCP servers from weave config...[/blue]")
    
    # Check if LiteLLM is accessible
    try:
        response = requests.get(f"{litellm_url}/mcp/enabled", timeout=10)
        if response.status_code != 200:
            console.print(f"[red]❌ LiteLLM service not accessible at {litellm_url}[/red]")
            return False
        
        mcp_status = response.json()
        if not mcp_status.get("enabled", False):
            console.print("[red]❌ MCP is not enabled in LiteLLM[/red]")
            return False
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]❌ Cannot connect to LiteLLM service: {e}[/red]")
        return False
    
    # Sync servers
    return sync_mcp_servers_to_litellm(litellm_url, api_key, dry_run=False, verbose=verbose) 