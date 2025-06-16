#!/usr/bin/env python

import json
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def get_weave_config_path() -> Path:
    """Get the path to the weave config file"""
    return Path.cwd() / '.weave' / 'config.json'

def load_weave_config() -> Dict[str, Any]:
    """Load the weave configuration file"""
    config_path = get_weave_config_path()
    
    if not config_path.exists():
        console.print(f"[red]Weave config file not found at {config_path}[/red]")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing weave config file: {e}[/red]")
        return {}
    except Exception as e:
        console.print(f"[red]Error reading weave config file: {e}[/red]")
        return {}

def save_weave_config(config: Dict[str, Any]) -> bool:
    """Save the weave configuration file"""
    config_path = get_weave_config_path()
    
    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        console.print(f"[red]Error saving weave config file: {e}[/red]")
        return False

def add_mcp_server_to_config(
    server_name: str,
    url: str,
    transport: str = "sse",
    auth_type: Optional[str] = None,
    spec_version: str = "2024-11-05",
    description: str = "",
    env_vars: Optional[Dict[str, str]] = None,
    scope: str = "all",
    force: bool = False
) -> bool:
    """Add an MCP server to the weave configuration"""
    config = load_weave_config()
    
    # Initialize mcp_servers section if it doesn't exist
    if 'mcp_servers' not in config:
        config['mcp_servers'] = {}
    
    # Check if server already exists
    if server_name in config['mcp_servers'] and not force:
        console.print(f"[yellow]MCP server '{server_name}' already exists. Use --force to overwrite.[/yellow]")
        return False
    
    # Validate scope
    valid_scopes = ["rag", "agent", "all"]
    if scope not in valid_scopes:
        console.print(f"[red]Invalid scope '{scope}'. Must be one of: {', '.join(valid_scopes)}[/red]")
        return False
    
    # Create server configuration
    server_config = {
        "url": url,
        "transport": transport,
        "spec_version": spec_version,
        "description": description,
        "scope": scope
    }
    
    # Add auth_type if provided
    if auth_type:
        server_config["auth_type"] = auth_type
    
    # Add environment variables if provided
    if env_vars:
        server_config["env"] = env_vars
    
    config['mcp_servers'][server_name] = server_config
    
    if save_weave_config(config):
        return True
    else:
        return False

def remove_mcp_server_from_config(server_name: str) -> bool:
    """Remove an MCP server from the weave configuration"""
    config = load_weave_config()
    
    if 'mcp_servers' not in config or server_name not in config['mcp_servers']:
        console.print(f"[red]MCP server '{server_name}' not found in configuration.[/red]")
        return False
    
    del config['mcp_servers'][server_name]
    
    if save_weave_config(config):
        return True
    else:
        return False

def list_mcp_servers_from_config(verbose: bool = False) -> Dict[str, Any]:
    """List MCP servers from the weave configuration"""
    config = load_weave_config()
    servers = config.get("mcp_servers", {})
    
    if not servers:
        console.print("[yellow]No MCP servers configured in weave.[/yellow]")
        console.print(f"[blue]Configuration file: {get_weave_config_path()}[/blue]")
        console.print("[blue]Use 'weave tool server add <name> <url>' to add servers[/blue]")
        return {}
    
    table = Table(title=f"MCP Servers in Weave Config ({len(servers)} configured)")
    table.add_column("Server Name", style="cyan", no_wrap=True)
    table.add_column("URL", style="blue")
    table.add_column("Transport", style="green")
    table.add_column("Scope", style="magenta")
    table.add_column("Description", style="yellow")
    
    if verbose:
        table.add_column("Auth Type", style="red")
        table.add_column("Spec Version", style="magenta")
        table.add_column("Environment Variables", style="dim")
    
    for server_name, server_config in servers.items():
        url = server_config.get("url", "N/A")
        transport = server_config.get("transport", "sse")
        scope = server_config.get("scope", "all")
        description = server_config.get("description", "No description")
        
        row_data = [server_name, url, transport, scope, description]
        
        if verbose:
            auth_type = server_config.get("auth_type", "none")
            spec_version = server_config.get("spec_version", "N/A")
            env_vars = server_config.get("env", {})
            env_display = f"{len(env_vars)} vars" if env_vars else "None"
            row_data.extend([auth_type, spec_version, env_display])
        
        table.add_row(*row_data)
    
    console.print(table)
    
    if verbose:
        console.print(f"\n[blue]Configuration file: {get_weave_config_path()}[/blue]")
        console.print(f"[blue]Total servers: {len(servers)}[/blue]")
        
        # Show environment variables details if any
        servers_with_env = {name: cfg for name, cfg in servers.items() if cfg.get("env")}
        if servers_with_env:
            console.print("\n[bold]Environment Variables:[/bold]")
            for server_name, server_config in servers_with_env.items():
                env_vars = server_config.get("env", {})
                env_list = [f"{k}={v}" for k, v in env_vars.items()]
                console.print(f"  [cyan]{server_name}:[/cyan] {', '.join(env_list)}")
    
    return servers

def get_mcp_servers_from_config() -> Dict[str, Any]:
    """Get MCP servers from weave config (for use by other modules)"""
    config = load_weave_config()
    return config.get("mcp_servers", {}) 